from pathlib import Path

from orchestrator.models import Task
from orchestrator.state_store import AppSettings, StateStore


def make_store(tmp_path: Path) -> StateStore:
    return StateStore(path=tmp_path / "queue_state.json")


def test_add_and_list_tasks_persists_to_disk(tmp_path):
    store = make_store(tmp_path)
    task = Task.new(summary="s", description="d", repo_url="r")
    store.add_task(task)

    reloaded = make_store(tmp_path)
    assert [t.id for t in reloaded.list_tasks()] == [task.id]


def test_update_task_changes_state_and_bumps_updated_at(tmp_path):
    store = make_store(tmp_path)
    task = Task.new(summary="s", description="d", repo_url="r")
    store.add_task(task)

    task.summary = "renamed"
    store.update_task(task)

    assert store.get_task(task.id).summary == "renamed"


def test_delete_task_removes_it(tmp_path):
    store = make_store(tmp_path)
    task = Task.new(summary="s", description="d", repo_url="r")
    store.add_task(task)
    store.delete_task(task.id)
    assert store.get_task(task.id) is None


def test_clone_task_adds_copy_after_original(tmp_path):
    store = make_store(tmp_path)
    original = Task.new(summary="first", description="d", repo_url="r")
    other = Task.new(summary="second", description="d", repo_url="r")
    store.add_task(original)
    store.add_task(other)

    cloned = store.clone_task(original.id)

    assert cloned is not None
    assert cloned.id != original.id
    assert cloned.summary == f"Copy of {original.summary}"
    ids = [t.id for t in store.list_tasks()]
    assert ids == [original.id, cloned.id, other.id]


def test_clone_task_persists_to_disk(tmp_path):
    store = make_store(tmp_path)
    original = Task.new(summary="first", description="d", repo_url="r")
    store.add_task(original)
    cloned = store.clone_task(original.id)

    reloaded = make_store(tmp_path)
    assert [t.id for t in reloaded.list_tasks()] == [original.id, cloned.id]


def test_clone_task_returns_none_for_unknown_id(tmp_path):
    store = make_store(tmp_path)
    assert store.clone_task("missing") is None


def test_move_task_reorders_list(tmp_path):
    store = make_store(tmp_path)
    first = Task.new(summary="first", description="d", repo_url="r")
    second = Task.new(summary="second", description="d", repo_url="r")
    store.add_task(first)
    store.add_task(second)

    store.move_task(second.id, -1)

    assert [t.id for t in store.list_tasks()] == [second.id, first.id]


def test_settings_round_trip(tmp_path):
    store = make_store(tmp_path)
    store.update_settings(AppSettings(retry_interval_minutes=5, max_retries=3, task_timeout_minutes=10))

    reloaded = make_store(tmp_path)
    settings = reloaded.get_settings()
    assert settings.retry_interval_minutes == 5
    assert settings.max_retries == 3
    assert settings.task_timeout_minutes == 10
