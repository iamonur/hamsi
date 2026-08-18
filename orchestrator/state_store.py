"""Thread-safe load/save of queue_state.json (tasks + app settings)."""

from __future__ import annotations

import json
import threading
from dataclasses import dataclass, asdict
from pathlib import Path
from typing import List, Optional

from orchestrator.models import Task, utcnow_iso

DEFAULT_STATE_PATH = Path(__file__).resolve().parent.parent / "queue_state.json"


@dataclass
class AppSettings:
    retry_interval_minutes: int = 15
    max_retries: int = 50
    task_timeout_minutes: int = 60


class StateStore:
    """Owns queue_state.json. All mutation methods persist immediately."""

    def __init__(self, path: Path = DEFAULT_STATE_PATH):
        self._path = path
        self._lock = threading.RLock()
        self._tasks: List[Task] = []
        self._settings = AppSettings()
        self.load()

    # -- persistence -----------------------------------------------------

    @property
    def path(self) -> Path:
        return self._path

    def load(self) -> None:
        with self._lock:
            if not self._path.exists():
                self._tasks = []
                self._settings = AppSettings()
                return
            raw = json.loads(self._path.read_text(encoding="utf-8"))
            self._tasks = [Task.from_dict(t) for t in raw.get("tasks", [])]
            settings_raw = raw.get("settings", {})
            self._settings = AppSettings(
                retry_interval_minutes=settings_raw.get("retry_interval_minutes", 15),
                max_retries=settings_raw.get("max_retries", 50),
                task_timeout_minutes=settings_raw.get("task_timeout_minutes", 60),
            )

    def save(self) -> None:
        with self._lock:
            payload = {
                "tasks": [t.to_dict() for t in self._tasks],
                "settings": asdict(self._settings),
            }
            tmp = self._path.with_suffix(".json.tmp")
            tmp.write_text(json.dumps(payload, indent=2), encoding="utf-8")
            tmp.replace(self._path)

    # -- tasks -------------------------------------------------------------

    def list_tasks(self) -> List[Task]:
        with self._lock:
            return list(self._tasks)

    def get_task(self, task_id: str) -> Optional[Task]:
        with self._lock:
            for t in self._tasks:
                if t.id == task_id:
                    return t
            return None

    def add_task(self, task: Task) -> None:
        with self._lock:
            self._tasks.append(task)
            self.save()

    def update_task(self, task: Task) -> None:
        with self._lock:
            for i, t in enumerate(self._tasks):
                if t.id == task.id:
                    task.updated_at = utcnow_iso()
                    self._tasks[i] = task
                    break
            self.save()

    def delete_task(self, task_id: str) -> None:
        with self._lock:
            self._tasks = [t for t in self._tasks if t.id != task_id]
            self.save()

    def clone_task(self, task_id: str) -> Optional[Task]:
        """Add a fresh copy of an existing task right after it in priority order."""
        with self._lock:
            idx = next((i for i, t in enumerate(self._tasks) if t.id == task_id), None)
            if idx is None:
                return None
            cloned = self._tasks[idx].clone()
            self._tasks.insert(idx + 1, cloned)
            self.save()
            return cloned

    def move_task(self, task_id: str, offset: int) -> None:
        """Move a task up (-1) or down (+1) in priority order."""
        with self._lock:
            idx = next((i for i, t in enumerate(self._tasks) if t.id == task_id), None)
            if idx is None:
                return
            self._reorder_locked(idx, idx + offset)

    def reorder_task(self, task_id: str, new_index: int) -> None:
        """Move a task to an arbitrary position in priority order (e.g. drag-and-drop)."""
        with self._lock:
            idx = next((i for i, t in enumerate(self._tasks) if t.id == task_id), None)
            if idx is None:
                return
            self._reorder_locked(idx, new_index)

    def _reorder_locked(self, idx: int, new_idx: int) -> None:
        """Move the task at idx to new_idx. Caller must hold self._lock."""
        new_idx = max(0, min(len(self._tasks) - 1, new_idx))
        if new_idx == idx:
            return
        self._tasks.insert(new_idx, self._tasks.pop(idx))
        self.save()

    # -- settings ------------------------------------------------------

    def get_settings(self) -> AppSettings:
        with self._lock:
            return AppSettings(**asdict(self._settings))

    def update_settings(self, settings: AppSettings) -> None:
        with self._lock:
            self._settings = settings
            self.save()
