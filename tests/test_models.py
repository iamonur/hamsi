from orchestrator.models import Task, TaskState


def test_task_new_generates_id_prefixed_task():
    task = Task.new(summary="Fix bug", description="Details", repo_url="https://example.com/repo.git")
    assert task.id.startswith("TASK-")
    assert task.state == TaskState.BACKLOG
    assert task.attempt_count == 0


def test_task_new_respects_explicit_id():
    task = Task.new(summary="s", description="d", repo_url="r", task_id="PROJ-1")
    assert task.id == "PROJ-1"


def test_task_round_trips_through_dict():
    task = Task.new(summary="Fix bug", description="Details", repo_url="https://example.com/repo.git")
    task.state = TaskState.IN_PROGRESS
    restored = Task.from_dict(task.to_dict())
    assert restored == task
