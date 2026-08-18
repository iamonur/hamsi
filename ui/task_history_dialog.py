"""Read-only dialog showing the persisted audit log for a single task: every
line any agent (Manager/Worker/Controller/System) emitted while working on
it, in order, independent of whatever else the shared Live Terminal shows.
"""

from __future__ import annotations

from PyQt5.QtWidgets import QDialog, QDialogButtonBox, QPushButton, QVBoxLayout

from orchestrator.models import Task
from orchestrator.task_history import TaskHistoryStore
from ui.terminal_panel import TerminalPanel


class TaskHistoryDialog(QDialog):
    def __init__(self, task: Task, history: TaskHistoryStore, parent=None):
        super().__init__(parent)
        self._task = task
        self._history = history
        self.setWindowTitle(f"History — {task.id}: {task.summary}")
        self.resize(900, 600)

        self.terminal = TerminalPanel(self)

        buttons = QDialogButtonBox(QDialogButtonBox.Close)
        buttons.rejected.connect(self.reject)
        buttons.accepted.connect(self.accept)
        refresh_button = QPushButton("Refresh")
        refresh_button.clicked.connect(self._load)
        buttons.addButton(refresh_button, QDialogButtonBox.ActionRole)

        layout = QVBoxLayout()
        layout.addWidget(self.terminal)
        layout.addWidget(buttons)
        self.setLayout(layout)

        self._load()

    def _load(self) -> None:
        self.terminal.clear()
        entries = self._history.read(self._task.id)
        if not entries:
            self.terminal.append_line("system", "No history recorded for this task yet.")
            return
        for entry in entries:
            self.terminal.append_line(entry.agent, entry.text, timestamp=entry.timestamp)
