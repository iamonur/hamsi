"""Per-task audit log: persists every agent log line to its own append-only
file under task_logs/, so a task's full history survives independently of
the shared Live Terminal (which only shows whatever is running right now).
"""

from __future__ import annotations

import json
import threading
from dataclasses import dataclass
from pathlib import Path
from typing import List

from orchestrator.models import utcnow_iso

DEFAULT_HISTORY_DIR = Path(__file__).resolve().parent.parent / "task_logs"


@dataclass(frozen=True)
class HistoryEntry:
    timestamp: str
    agent: str
    text: str


class TaskHistoryStore:
    """Owns one JSONL file per task ID. Safe to share across threads."""

    def __init__(self, directory: Path = DEFAULT_HISTORY_DIR):
        self._dir = directory
        self._lock = threading.RLock()

    def _path_for(self, task_id: str) -> Path:
        return self._dir / f"{task_id}.jsonl"

    def append(self, task_id: str, agent: str, text: str) -> HistoryEntry:
        entry = HistoryEntry(timestamp=utcnow_iso(), agent=agent, text=text)
        with self._lock:
            self._dir.mkdir(parents=True, exist_ok=True)
            with self._path_for(task_id).open("a", encoding="utf-8") as f:
                f.write(json.dumps(entry.__dict__) + "\n")
        return entry

    def read(self, task_id: str) -> List[HistoryEntry]:
        path = self._path_for(task_id)
        if not path.exists():
            return []
        with self._lock:
            raw = path.read_text(encoding="utf-8")
        entries = []
        for line in raw.splitlines():
            line = line.strip()
            if not line:
                continue
            entries.append(HistoryEntry(**json.loads(line)))
        return entries

    def clear(self, task_id: str) -> None:
        with self._lock:
            path = self._path_for(task_id)
            if path.exists():
                path.unlink()
