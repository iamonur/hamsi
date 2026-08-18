from unittest.mock import patch

from orchestrator import git_ops


def test_push_to_remote_runs_git_push_with_tracking(tmp_path):
    with patch.object(git_ops, "workspace_path_for", return_value=tmp_path), \
         patch.object(git_ops, "_run") as mock_run:
        git_ops.push_to_remote("TASK-1", "feature/do-thing")

    mock_run.assert_called_once_with(
        ["git", "push", "-u", "origin", "feature/do-thing"], cwd=tmp_path
    )


def test_push_to_remote_raises_on_git_failure(tmp_path):
    with patch.object(git_ops, "workspace_path_for", return_value=tmp_path), \
         patch.object(git_ops, "_run", side_effect=git_ops.GitOpsError("boom")):
        try:
            git_ops.push_to_remote("TASK-1", "feature/do-thing")
        except git_ops.GitOpsError as exc:
            assert str(exc) == "boom"
        else:
            raise AssertionError("expected GitOpsError")


def test_delete_workspace_removes_existing_clone(tmp_path):
    workspace = tmp_path / "TASK-1"
    workspace.mkdir()
    (workspace / "file.txt").write_text("data")

    with patch.object(git_ops, "workspace_path_for", return_value=workspace):
        git_ops.delete_workspace("TASK-1")

    assert not workspace.exists()


def test_delete_workspace_is_noop_when_missing(tmp_path):
    workspace = tmp_path / "TASK-missing"

    with patch.object(git_ops, "workspace_path_for", return_value=workspace):
        git_ops.delete_workspace("TASK-missing")  # should not raise

    assert not workspace.exists()
