"""Drives ManagerThread's step logic directly (never calling .start()/.run() as
a real OS thread) with claude_runner and git_ops stubbed out, so no real
`claude` CLI, network, or git operations happen.
"""

from datetime import datetime, timedelta, timezone
from pathlib import Path
from unittest.mock import patch

from orchestrator import manager_thread as mt
from orchestrator.claude_runner import ClaudeRunResult
from orchestrator.models import Task, TaskState
from orchestrator.state_store import AppSettings, StateStore


def make_manager(tmp_path: Path, **settings_overrides) -> tuple[mt.ManagerThread, StateStore]:
    store = StateStore(path=tmp_path / "queue_state.json")
    store.update_settings(AppSettings(
        retry_interval_minutes=settings_overrides.get("retry_interval_minutes", 15),
        max_retries=settings_overrides.get("max_retries", 3),
        task_timeout_minutes=settings_overrides.get("task_timeout_minutes", 1),
    ))
    manager = mt.ManagerThread(store)
    return manager, store


def test_worker_success_and_controller_pass_marks_done(tmp_path):
    manager, store = make_manager(tmp_path)
    task = Task.new(summary="Add feature", description="Do the thing", repo_url="https://example.com/r.git")
    store.add_task(task)

    with patch.object(mt, "run_claude") as run_claude, \
         patch.object(mt.git_ops, "branch_name", return_value="feature/test"), \
         patch.object(mt.git_ops, "ensure_workspace", return_value=tmp_path), \
         patch.object(mt.git_ops, "workspace_path_for", return_value=tmp_path):
        run_claude.side_effect = [
            ClaudeRunResult(exit_code=0, output="worker done"),
            ClaudeRunResult(exit_code=0, output="looks good\nVERDICT: PASS"),
        ]
        manager._process_task(task)

    assert store.get_task(task.id).state == TaskState.DONE


def test_controller_fail_then_pass_loops_back_without_new_task_pick(tmp_path):
    manager, store = make_manager(tmp_path)
    task = Task.new(summary="Add feature", description="Do the thing", repo_url="https://example.com/r.git")
    store.add_task(task)

    with patch.object(mt, "run_claude") as run_claude, \
         patch.object(mt.git_ops, "branch_name", return_value="feature/test"), \
         patch.object(mt.git_ops, "ensure_workspace", return_value=tmp_path), \
         patch.object(mt.git_ops, "workspace_path_for", return_value=tmp_path):
        run_claude.side_effect = [
            ClaudeRunResult(exit_code=0, output="worker attempt 1"),
            ClaudeRunResult(exit_code=0, output="VERDICT: FAIL: missing tests"),
            ClaudeRunResult(exit_code=0, output="worker attempt 2"),
            ClaudeRunResult(exit_code=0, output="VERDICT: PASS"),
        ]
        manager._process_task(task)

    final = store.get_task(task.id)
    assert final.state == TaskState.DONE
    assert final.attempt_count == 1
    assert run_claude.call_count == 4


def test_worker_failure_schedules_will_retry_with_cooldown(tmp_path):
    manager, store = make_manager(tmp_path, retry_interval_minutes=15, max_retries=3)
    task = Task.new(summary="Add feature", description="Do the thing", repo_url="https://example.com/r.git")
    store.add_task(task)

    with patch.object(mt, "run_claude") as run_claude, \
         patch.object(mt.git_ops, "branch_name", return_value="feature/test"), \
         patch.object(mt.git_ops, "ensure_workspace", return_value=tmp_path), \
         patch.object(mt.git_ops, "workspace_path_for", return_value=tmp_path):
        run_claude.side_effect = [ClaudeRunResult(exit_code=1, output="crashed")]
        manager._process_task(task)

    final = store.get_task(task.id)
    assert final.state == TaskState.WILL_RETRY
    assert final.attempt_count == 1
    assert final.next_retry_at is not None


def test_exceeding_max_retries_marks_failed(tmp_path):
    manager, store = make_manager(tmp_path, max_retries=1)
    task = Task.new(summary="Add feature", description="Do the thing", repo_url="https://example.com/r.git")
    task.attempt_count = 1  # already used its one retry
    store.add_task(task)

    with patch.object(mt, "run_claude") as run_claude, \
         patch.object(mt.git_ops, "branch_name", return_value="feature/test"), \
         patch.object(mt.git_ops, "ensure_workspace", return_value=tmp_path), \
         patch.object(mt.git_ops, "workspace_path_for", return_value=tmp_path):
        run_claude.side_effect = [ClaudeRunResult(exit_code=1, output="crashed again")]
        manager._process_task(task)

    assert store.get_task(task.id).state == TaskState.FAILED


def test_pick_next_task_skips_will_retry_before_cooldown_elapsed(tmp_path):
    manager, store = make_manager(tmp_path)
    task = Task.new(summary="s", description="d", repo_url="r")
    task.state = TaskState.WILL_RETRY
    task.next_retry_at = (datetime.now(timezone.utc) + timedelta(minutes=10)).isoformat()
    store.add_task(task)

    assert manager._pick_next_task() is None


def test_pick_next_task_returns_backlog_task(tmp_path):
    manager, store = make_manager(tmp_path)
    task = Task.new(summary="s", description="d", repo_url="r")
    store.add_task(task)

    picked = manager._pick_next_task()
    assert picked is not None
    assert picked.id == task.id


def test_process_task_records_history_for_the_task(tmp_path):
    manager, store = make_manager(tmp_path)
    task = Task.new(summary="Add feature", description="Do the thing", repo_url="https://example.com/r.git")
    store.add_task(task)

    with patch.object(mt, "run_claude") as run_claude, \
         patch.object(mt.git_ops, "branch_name", return_value="feature/test"), \
         patch.object(mt.git_ops, "ensure_workspace", return_value=tmp_path), \
         patch.object(mt.git_ops, "workspace_path_for", return_value=tmp_path):
        run_claude.side_effect = [
            ClaudeRunResult(exit_code=0, output="worker done"),
            ClaudeRunResult(exit_code=0, output="looks good\nVERDICT: PASS"),
        ]
        manager._process_task(task)

    entries = manager._history.read(task.id)
    assert entries, "expected history entries for the processed task"
    assert all(e.agent == "manager" for e in entries)
    assert any("Picked up" in e.text for e in entries)
    assert any("validated. Marking Done" in e.text for e in entries)


def test_history_is_isolated_per_task(tmp_path):
    manager, store = make_manager(tmp_path)
    first = Task.new(summary="First", description="d", repo_url="https://example.com/r.git")
    second = Task.new(summary="Second", description="d", repo_url="https://example.com/r.git")
    store.add_task(first)
    store.add_task(second)

    with patch.object(mt, "run_claude") as run_claude, \
         patch.object(mt.git_ops, "branch_name", return_value="feature/test"), \
         patch.object(mt.git_ops, "ensure_workspace", return_value=tmp_path), \
         patch.object(mt.git_ops, "workspace_path_for", return_value=tmp_path):
        run_claude.side_effect = [
            ClaudeRunResult(exit_code=0, output="worker done"),
            ClaudeRunResult(exit_code=0, output="VERDICT: PASS"),
        ]
        manager._process_task(first)

    assert manager._history.read(first.id)
    assert manager._history.read(second.id) == []
