"""Bulk import tasks from a local CSV/text file. See REQUIREMENTS.md 4.2."""

from __future__ import annotations

import csv
from pathlib import Path
from typing import List

from PyQt5.QtWidgets import (
    QDialog,
    QDialogButtonBox,
    QFileDialog,
    QHBoxLayout,
    QLabel,
    QPushButton,
    QTableWidget,
    QTableWidgetItem,
    QVBoxLayout,
)

from orchestrator.models import Task

COLUMNS = ["summary", "description", "repo_url"]


def parse_csv(path: Path) -> List[Task]:
    tasks: List[Task] = []
    with path.open(newline="", encoding="utf-8") as fh:
        reader = csv.DictReader(fh)
        for row in reader:
            summary = (row.get("summary") or row.get("Summary") or "").strip()
            description = (row.get("description") or row.get("Description") or "").strip()
            repo_url = (row.get("repo_url") or row.get("RepoURL") or row.get("Repo URL") or "").strip()
            if not summary:
                continue
            tasks.append(Task.new(summary=summary, description=description, repo_url=repo_url))
    return tasks


class BulkImportDialog(QDialog):
    """Expects a CSV with headers: summary, description, repo_url."""

    def __init__(self, parent=None):
        super().__init__(parent)
        self.setWindowTitle("Bulk Import Tasks")
        self.resize(600, 400)
        self._tasks: List[Task] = []

        self.info_label = QLabel("Choose a CSV file with columns: summary, description, repo_url")
        self.choose_button = QPushButton("Choose File…")
        self.choose_button.clicked.connect(self._choose_file)

        self.table = QTableWidget(0, 3)
        self.table.setHorizontalHeaderLabels(["Summary", "Description", "Repo URL"])

        buttons = QDialogButtonBox(QDialogButtonBox.Ok | QDialogButtonBox.Cancel)
        buttons.accepted.connect(self.accept)
        buttons.rejected.connect(self.reject)

        top_row = QHBoxLayout()
        top_row.addWidget(self.info_label)
        top_row.addWidget(self.choose_button)

        layout = QVBoxLayout()
        layout.addLayout(top_row)
        layout.addWidget(self.table)
        layout.addWidget(buttons)
        self.setLayout(layout)

    def _choose_file(self) -> None:
        path_str, _ = QFileDialog.getOpenFileName(self, "Choose CSV file", "", "CSV Files (*.csv);;All Files (*)")
        if not path_str:
            return
        self._tasks = parse_csv(Path(path_str))
        self.table.setRowCount(len(self._tasks))
        for row, task in enumerate(self._tasks):
            self.table.setItem(row, 0, QTableWidgetItem(task.summary))
            self.table.setItem(row, 1, QTableWidgetItem(task.description))
            self.table.setItem(row, 2, QTableWidgetItem(task.repo_url))

    def imported_tasks(self) -> List[Task]:
        return list(self._tasks)
