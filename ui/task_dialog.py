"""Add/Edit task form dialog. See REQUIREMENTS.md 5.1."""

from __future__ import annotations

from typing import Optional

from PyQt5.QtWidgets import (
    QDialog,
    QDialogButtonBox,
    QFormLayout,
    QLineEdit,
    QPlainTextEdit,
)

from orchestrator.models import Task


class TaskDialog(QDialog):
    def __init__(self, parent=None, task: Optional[Task] = None):
        super().__init__(parent)
        self._task = task
        self.setWindowTitle("Edit Task" if task else "Add Task")

        self.summary_edit = QLineEdit(task.summary if task else "")
        self.description_edit = QPlainTextEdit(task.description if task else "")
        self.repo_url_edit = QLineEdit(task.repo_url if task else "")

        form = QFormLayout()
        form.addRow("Summary", self.summary_edit)
        form.addRow("Description", self.description_edit)
        form.addRow("Target Repository URL", self.repo_url_edit)

        buttons = QDialogButtonBox(QDialogButtonBox.Ok | QDialogButtonBox.Cancel)
        buttons.accepted.connect(self.accept)
        buttons.rejected.connect(self.reject)
        form.addRow(buttons)

        self.setLayout(form)

    def result_task(self) -> Task:
        summary = self.summary_edit.text().strip()
        description = self.description_edit.toPlainText().strip()
        repo_url = self.repo_url_edit.text().strip()
        if self._task:
            self._task.summary = summary
            self._task.description = description
            self._task.repo_url = repo_url
            return self._task
        return Task.new(summary=summary, description=description, repo_url=repo_url)
