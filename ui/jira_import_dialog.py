"""Import tasks from Jira via JQL, applying one target repo URL to the batch
(editable per-row before confirming). See REQUIREMENTS.md 4.2."""

from __future__ import annotations

from typing import List

from PyQt5.QtWidgets import (
    QDialog,
    QDialogButtonBox,
    QFormLayout,
    QLineEdit,
    QMessageBox,
    QPushButton,
    QTableWidget,
    QTableWidgetItem,
    QVBoxLayout,
)

from orchestrator import env_store
from orchestrator.jira_client import JiraClientError, fetch_issues
from orchestrator.models import Task


class JiraImportDialog(QDialog):
    def __init__(self, parent=None):
        super().__init__(parent)
        self.setWindowTitle("Import from Jira")
        self.resize(650, 420)
        self._tasks: List[Task] = []

        env = env_store.read_env()
        self.base_url_edit = QLineEdit(env.get("JIRA_BASE_URL", ""))
        self.pat_edit = QLineEdit(env.get("JIRA_PAT", ""))
        self.pat_edit.setEchoMode(QLineEdit.Password)
        self.jql_edit = QLineEdit("")
        self.jql_edit.setPlaceholderText('e.g. project = "PROJ" AND status = "To Do"')
        self.repo_url_edit = QLineEdit("")
        self.repo_url_edit.setPlaceholderText("Applied to every fetched issue below")

        self.fetch_button = QPushButton("Fetch Issues")
        self.fetch_button.clicked.connect(self._fetch)

        self.table = QTableWidget(0, 3)
        self.table.setHorizontalHeaderLabels(["Jira Key", "Summary", "Repo URL"])

        form = QFormLayout()
        form.addRow("Jira Base URL", self.base_url_edit)
        form.addRow("Personal Access Token", self.pat_edit)
        form.addRow("JQL", self.jql_edit)
        form.addRow("Target Repository URL", self.repo_url_edit)
        form.addRow(self.fetch_button)

        buttons = QDialogButtonBox(QDialogButtonBox.Ok | QDialogButtonBox.Cancel)
        buttons.accepted.connect(self.accept)
        buttons.rejected.connect(self.reject)

        layout = QVBoxLayout()
        layout.addLayout(form)
        layout.addWidget(self.table)
        layout.addWidget(buttons)
        self.setLayout(layout)

    def _fetch(self) -> None:
        try:
            issues = fetch_issues(
                base_url=self.base_url_edit.text().strip(),
                pat=self.pat_edit.text().strip(),
                jql=self.jql_edit.text().strip(),
            )
        except JiraClientError as exc:
            QMessageBox.warning(self, "Jira Import Failed", str(exc))
            return

        repo_url = self.repo_url_edit.text().strip()
        self._tasks = [
            Task.new(summary=issue.summary, description=issue.description, repo_url=repo_url, task_id=issue.key)
            for issue in issues
        ]
        self.table.setRowCount(len(self._tasks))
        for row, task in enumerate(self._tasks):
            self.table.setItem(row, 0, QTableWidgetItem(task.id))
            self.table.setItem(row, 1, QTableWidgetItem(task.summary))
            self.table.setItem(row, 2, QTableWidgetItem(task.repo_url))

    def imported_tasks(self) -> List[Task]:
        for row in range(self.table.rowCount()):
            item = self.table.item(row, 2)
            if item is not None and row < len(self._tasks):
                self._tasks[row].repo_url = item.text().strip()
        return list(self._tasks)
