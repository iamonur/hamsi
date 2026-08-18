from pathlib import Path

from orchestrator.task_history import TaskHistoryStore


def make_history(tmp_path: Path) -> TaskHistoryStore:
    return TaskHistoryStore(tmp_path / "task_logs")


def test_append_persists_entry_to_disk(tmp_path):
    history = make_history(tmp_path)
    history.append("TASK-1", "worker", "did a thing")

    reloaded = make_history(tmp_path)
    entries = reloaded.read("TASK-1")

    assert len(entries) == 1
    assert entries[0].agent == "worker"
    assert entries[0].text == "did a thing"
    assert entries[0].timestamp


def test_read_returns_empty_list_for_unknown_task(tmp_path):
    history = make_history(tmp_path)
    assert history.read("missing") == []


def test_entries_for_different_tasks_do_not_mix(tmp_path):
    history = make_history(tmp_path)
    history.append("TASK-1", "worker", "task one line")
    history.append("TASK-2", "worker", "task two line")

    assert [e.text for e in history.read("TASK-1")] == ["task one line"]
    assert [e.text for e in history.read("TASK-2")] == ["task two line"]


def test_append_preserves_order(tmp_path):
    history = make_history(tmp_path)
    history.append("TASK-1", "manager", "first")
    history.append("TASK-1", "worker", "second")
    history.append("TASK-1", "controller", "third")

    assert [e.text for e in history.read("TASK-1")] == ["first", "second", "third"]


def test_clear_removes_entries(tmp_path):
    history = make_history(tmp_path)
    history.append("TASK-1", "manager", "first")

    history.clear("TASK-1")

    assert history.read("TASK-1") == []


def test_clear_unknown_task_is_a_no_op(tmp_path):
    history = make_history(tmp_path)
    history.clear("missing")  # must not raise
