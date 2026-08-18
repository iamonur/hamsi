"""Core data model: Task, TaskState, AgentKind."""

from __future__ import annotations

import uuid
from dataclasses import dataclass, field, asdict
from datetime import datetime, timezone
from enum import Enum
from typing import Optional


def utcnow_iso() -> str:
    return datetime.now(timezone.utc).isoformat()


class TaskState(str, Enum):
    BACKLOG = "Backlog"
    IN_PROGRESS = "In Progress"
    IN_REVIEW = "In Review"
    WILL_RETRY = "Will Retry"
    DONE = "Done"
    FAILED = "Failed"


class AgentKind(str, Enum):
    MANAGER = "manager"
    WORKER = "worker"
    CONTROLLER = "controller"
    SYSTEM = "system"


@dataclass
class Task:
    id: str
    summary: str
    description: str
    repo_url: str
    state: TaskState = TaskState.BACKLOG
    attempt_count: int = 0
    next_retry_at: Optional[str] = None
    branch: Optional[str] = None
    workspace_path: Optional[str] = None
    last_controller_feedback: Optional[str] = None
    qa_criteria: str = ""
    use_default_qa_criteria: bool = True
    created_at: str = field(default_factory=utcnow_iso)
    updated_at: str = field(default_factory=utcnow_iso)
    time_spent_seconds: float = 0.0
    active_since: Optional[str] = None

    def total_time_spent_seconds(self) -> float:
        """Accumulated implementation time, including the in-flight session
        if the task is currently being worked on."""
        total = self.time_spent_seconds
        if self.active_since:
            started = datetime.fromisoformat(self.active_since)
            total += (datetime.now(timezone.utc) - started).total_seconds()
        return total

    @staticmethod
    def new(
        summary: str,
        description: str,
        repo_url: str,
        task_id: Optional[str] = None,
        qa_criteria: str = "",
        use_default_qa_criteria: bool = True,
    ) -> "Task":
        return Task(
            id=task_id or f"TASK-{uuid.uuid4().hex[:8]}",
            summary=summary,
            description=description,
            repo_url=repo_url,
            qa_criteria=qa_criteria,
            use_default_qa_criteria=use_default_qa_criteria,
        )

    def clone(self) -> "Task":
        """Return a new task copied from this one, reset to a fresh Backlog state."""
        return Task.new(
            summary=f"Copy of {self.summary}",
            description=self.description,
            repo_url=self.repo_url,
            qa_criteria=self.qa_criteria,
            use_default_qa_criteria=self.use_default_qa_criteria,
        )

    def to_dict(self) -> dict:
        d = asdict(self)
        d["state"] = self.state.value
        return d

    @staticmethod
    def from_dict(d: dict) -> "Task":
        d = dict(d)
        d["state"] = TaskState(d.get("state", TaskState.BACKLOG.value))
        return Task(**d)
