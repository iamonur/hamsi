"""The Manager Agent: QThread running the main queue loop. Performs the Worker
and Controller steps synchronously within itself (single background thread),
emitting Qt signals so the GUI thread can update without blocking. See
REQUIREMENTS.md sections 3 and 4.
"""

from __future__ import annotations

from datetime import datetime, timedelta, timezone
from typing import Optional

from PyQt5.QtCore import QThread, pyqtSignal

from orchestrator import env_store, git_ops
from orchestrator.claude_runner import ClaudeTimeoutError, run_claude
from orchestrator.models import AgentKind, Task, TaskState
from orchestrator.prompts import build_controller_prompt, build_worker_prompt, parse_verdict
from orchestrator.state_store import StateStore

POLL_INTERVAL_SECONDS = 5
STOP_CHECK_INTERVAL_SECONDS = 1


def _parse_iso(value: Optional[str]) -> Optional[datetime]:
    if not value:
        return None
    return datetime.fromisoformat(value)


class ManagerThread(QThread):
    log_line = pyqtSignal(str, str)  # agent kind value, text
    task_changed = pyqtSignal(str)  # task id

    def __init__(self, store: StateStore, claude_bin: str = "claude", parent=None):
        super().__init__(parent)
        self._store = store
        self._claude_bin = claude_bin
        self._stop_requested = False

    def request_stop(self) -> None:
        self._stop_requested = True

    # -- logging helpers -----------------------------------------------

    def _log(self, agent: AgentKind, text: str) -> None:
        self.log_line.emit(agent.value, text)

    def _set_state(self, task: Task, state: TaskState, **fields) -> Task:
        task.state = state
        for key, value in fields.items():
            setattr(task, key, value)
        self._store.update_task(task)
        self.task_changed.emit(task.id)
        return task

    # -- main loop -------------------------------------------------------

    def run(self) -> None:  # noqa: C901 - orchestration loop, kept together deliberately
        self._log(AgentKind.MANAGER, "Manager started.")
        while not self._stop_requested:
            task = self._pick_next_task()
            if task is None:
                self._sleep_interruptible(POLL_INTERVAL_SECONDS)
                continue
            self._process_task(task)
        self._log(AgentKind.MANAGER, "Manager stopped.")

    def _sleep_interruptible(self, seconds: float) -> None:
        elapsed = 0.0
        while elapsed < seconds and not self._stop_requested:
            self.msleep(int(STOP_CHECK_INTERVAL_SECONDS * 1000))
            elapsed += STOP_CHECK_INTERVAL_SECONDS

    def _pick_next_task(self) -> Optional[Task]:
        now = datetime.now(timezone.utc)
        for task in self._store.list_tasks():
            if task.state == TaskState.BACKLOG:
                return task
            if task.state == TaskState.IN_PROGRESS:
                return task  # resume after an app restart
            if task.state == TaskState.WILL_RETRY:
                retry_at = _parse_iso(task.next_retry_at)
                if retry_at is None or retry_at <= now:
                    return task
        return None

    def _process_task(self, task: Task) -> None:
        settings = self._store.get_settings()
        self._log(AgentKind.MANAGER, f"Picked up {task.id}: {task.summary}")
        self._set_state(task, TaskState.IN_PROGRESS)

        while True:
            if self._stop_requested:
                return

            worker_ok = self._run_worker_step(task, settings.task_timeout_minutes)
            if not worker_ok:
                self._handle_failure(task, settings)
                return

            self._set_state(task, TaskState.IN_REVIEW)
            verdict_passed, reason = self._run_controller_step(
                task, settings.task_timeout_minutes
            )
            if verdict_passed is None:
                self._handle_failure(task, settings)
                return

            if verdict_passed:
                self._log(AgentKind.MANAGER, f"{task.id} validated. Marking Done.")
                self._set_state(task, TaskState.DONE, last_controller_feedback=None)
                return

            # Controller rejected: loop back to Worker immediately, no cooldown.
            self._log(AgentKind.MANAGER, f"{task.id} rejected by Controller: {reason}")
            task.attempt_count += 1
            if task.attempt_count > settings.max_retries:
                self._log(AgentKind.MANAGER, f"{task.id} exceeded max retries. Marking Failed.")
                self._set_state(task, TaskState.FAILED, last_controller_feedback=reason)
                return
            self._set_state(
                task, TaskState.IN_PROGRESS, last_controller_feedback=reason
            )

    def _run_worker_step(self, task: Task, timeout_minutes: int) -> bool:
        try:
            branch = git_ops.branch_name(task.summary)
            self._log(AgentKind.MANAGER, f"Preparing workspace for {task.id} on branch {branch}...")
            workspace = git_ops.ensure_workspace(task.id, task.repo_url, branch)
            task.branch = branch
            task.workspace_path = str(workspace)
            self._store.update_task(task)

            self._log(AgentKind.MANAGER, f"Starting Worker for {task.id}...")
            prompt = build_worker_prompt(task)
            result = run_claude(
                prompt=prompt,
                cwd=workspace,
                env=env_store.subprocess_env(),
                on_line=lambda line: self._log(AgentKind.WORKER, line),
                timeout_seconds=timeout_minutes * 60,
                claude_bin=self._claude_bin,
            )
            if result.exit_code != 0:
                self._log(
                    AgentKind.SYSTEM,
                    f"Worker exited with code {result.exit_code} for {task.id}.",
                )
                return False
            return True
        except (ClaudeTimeoutError, git_ops.GitOpsError, OSError) as exc:
            self._log(AgentKind.SYSTEM, f"Worker step failed for {task.id}: {exc}")
            return False

    def _run_controller_step(self, task: Task, timeout_minutes: int):
        try:
            prompt = build_controller_prompt(task)
            result = run_claude(
                prompt=prompt,
                cwd=git_ops.workspace_path_for(task.id),
                env=env_store.subprocess_env(),
                on_line=lambda line: self._log(AgentKind.CONTROLLER, line),
                timeout_seconds=timeout_minutes * 60,
                claude_bin=self._claude_bin,
            )
            verdict = parse_verdict(result.output)
            return verdict.passed, verdict.reason
        except (ClaudeTimeoutError, OSError) as exc:
            self._log(AgentKind.SYSTEM, f"Controller step failed for {task.id}: {exc}")
            return None, None

    def _handle_failure(self, task: Task, settings) -> None:
        task.attempt_count += 1
        if task.attempt_count > settings.max_retries:
            self._log(AgentKind.MANAGER, f"{task.id} exceeded max retries. Marking Failed.")
            self._set_state(task, TaskState.FAILED)
            return
        next_retry = datetime.now(timezone.utc) + timedelta(
            minutes=settings.retry_interval_minutes
        )
        self._log(
            AgentKind.MANAGER,
            f"{task.id} will retry in {settings.retry_interval_minutes} minute(s) "
            f"(attempt {task.attempt_count}/{settings.max_retries}).",
        )
        self._set_state(
            task, TaskState.WILL_RETRY, next_retry_at=next_retry.isoformat()
        )
