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


def test_task_clone_copies_content_with_fresh_id_and_state():
    task = Task.new(summary="Fix bug", description="Details", repo_url="https://example.com/repo.git")
    task.state = TaskState.IN_PROGRESS
    task.attempt_count = 3
    task.branch = "worker/fix-bug"
    task.workspace_path = "/tmp/workspace"
    task.last_controller_feedback = "needs more tests"

    clone = task.clone()

    assert clone.id != task.id
    assert clone.summary == f"Copy of {task.summary}"
    assert clone.description == task.description
    assert clone.repo_url == task.repo_url
    assert clone.state == TaskState.BACKLOG
    assert clone.attempt_count == 0
    assert clone.next_retry_at is None
    assert clone.branch is None
    assert clone.workspace_path is None
    assert clone.last_controller_feedback is None
