"""Minimal git helpers: clone, branch creation/checkout. Uses the host's git
credential manager — no custom auth handling, per REQUIREMENTS.md section 6.
"""

from __future__ import annotations

import os
import re
import subprocess
from pathlib import Path

WORKSPACES_ROOT = Path(__file__).resolve().parent.parent / "workspaces"
GIT_TIMEOUT_SECONDS = 120


class GitOpsError(RuntimeError):
    pass


def slugify(text: str, max_len: int = 50) -> str:
    slug = re.sub(r"[^a-zA-Z0-9]+", "-", text.strip().lower()).strip("-")
    return slug[:max_len] or "task"


def branch_name(summary: str) -> str:
    return f"feature/{slugify(summary)}"


def _run(args: list[str], cwd: Path | None = None) -> subprocess.CompletedProcess:
    # GIT_TERMINAL_PROMPT=0 makes git fail fast instead of hanging on an
    # interactive credential prompt it has no terminal to show or read from
    # when running inside this GUI app's subprocess.
    env = {**os.environ, "GIT_TERMINAL_PROMPT": "0"}
    try:
        result = subprocess.run(
            args,
            cwd=str(cwd) if cwd else None,
            capture_output=True,
            text=True,
            stdin=subprocess.DEVNULL,
            env=env,
            timeout=GIT_TIMEOUT_SECONDS,
        )
    except subprocess.TimeoutExpired as exc:
        raise GitOpsError(
            f"`{' '.join(args)}` timed out after {GIT_TIMEOUT_SECONDS}s"
        ) from exc
    if result.returncode != 0:
        raise GitOpsError(
            f"`{' '.join(args)}` failed (exit {result.returncode}): {result.stderr.strip()}"
        )
    return result


def workspace_path_for(task_id: str) -> Path:
    return WORKSPACES_ROOT / task_id


def ensure_workspace(task_id: str, repo_url: str, branch: str) -> Path:
    """Clones the repo if the workspace doesn't exist yet, then ensures `branch`
    exists (creating it off the default branch) and is checked out."""
    path = workspace_path_for(task_id)
    if not path.exists():
        WORKSPACES_ROOT.mkdir(parents=True, exist_ok=True)
        _run(["git", "clone", repo_url, str(path)])

    existing_branches = _run(["git", "branch", "--list", branch], cwd=path).stdout
    if branch in existing_branches:
        _run(["git", "checkout", branch], cwd=path)
    else:
        _run(["git", "checkout", "-b", branch], cwd=path)

    return path
