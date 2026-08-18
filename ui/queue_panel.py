"""Queue Dashboard panel: task table + Add/Edit/Delete/Move controls, bulk
import, Jira import. See REQUIREMENTS.md 5.1."""

from __future__ import annotations

from PyQt5.QtCore import pyqtSignal
from PyQt5.QtWidgets import (
    QAbstractItemView,
    QHBoxLayout,
    QMessageBox,
    QPushButton,
    QTableWidget,
    QTableWidgetItem,
    QVBoxLayout,
    QWidget,
)

from orchestrator.state_store import StateStore
from ui.bulk_import_dialog import BulkImportDialog
from ui.jira_import_dialog import JiraImportDialog
from ui.task_dialog import TaskDialog

COLUMNS = ["ID", "Summary", "State"]


class QueuePanel(QWidget):
    tasks_changed = pyqtSignal()

    def __init__(self, store: StateStore, parent=None):
        super().__init__(parent)
        self._store = store

        self.table = QTableWidget(0, len(COLUMNS))
        self.table.setHorizontalHeaderLabels(COLUMNS)
        self.table.setSelectionBehavior(QAbstractItemView.SelectRows)
        self.table.setSelectionMode(QAbstractItemView.SingleSelection)
        self.table.setEditTriggers(QAbstractItemView.NoEditTriggers)

        self.add_button = QPushButton("Add")
        self.edit_button = QPushButton("Edit")
        self.delete_button = QPushButton("Delete")
        self.up_button = QPushButton("Move Up")
        self.down_button = QPushButton("Move Down")
        self.bulk_import_button = QPushButton("Bulk Import…")
        self.jira_import_button = QPushButton("Import from Jira…")

        self.add_button.clicked.connect(self._add_task)
        self.edit_button.clicked.connect(self._edit_task)
        self.delete_button.clicked.connect(self._delete_task)
        self.up_button.clicked.connect(lambda: self._move_task(-1))
        self.down_button.clicked.connect(lambda: self._move_task(1))
        self.bulk_import_button.clicked.connect(self._bulk_import)
        self.jira_import_button.clicked.connect(self._jira_import)

        button_row = QHBoxLayout()
        for btn in (
            self.add_button,
            self.edit_button,
            self.delete_button,
            self.up_button,
            self.down_button,
            self.bulk_import_button,
            self.jira_import_button,
        ):
            button_row.addWidget(btn)

        layout = QVBoxLayout()
        layout.addLayout(button_row)
        layout.addWidget(self.table)
        self.setLayout(layout)

        self.refresh()

    # -- data -----------------------------------------------------------

    def refresh(self) -> None:
        tasks = self._store.list_tasks()
        self.table.setRowCount(len(tasks))
        for row, task in enumerate(tasks):
            self.table.setItem(row, 0, QTableWidgetItem(task.id))
            self.table.setItem(row, 1, QTableWidgetItem(task.summary))
            self.table.setItem(row, 2, QTableWidgetItem(task.state.value))

    def _selected_task_id(self):
        rows = self.table.selectionModel().selectedRows()
        if not rows:
            return None
        return self.table.item(rows[0].row(), 0).text()

    # -- actions --------------------------------------------------------

    def _add_task(self) -> None:
        dialog = TaskDialog(self)
        if dialog.exec_():
            self._store.add_task(dialog.result_task())
            self.refresh()
            self.tasks_changed.emit()

    def _edit_task(self) -> None:
        task_id = self._selected_task_id()
        if task_id is None:
            return
        task = self._store.get_task(task_id)
        if task is None:
            return
        dialog = TaskDialog(self, task=task)
        if dialog.exec_():
            self._store.update_task(dialog.result_task())
            self.refresh()
            self.tasks_changed.emit()

    def _delete_task(self) -> None:
        task_id = self._selected_task_id()
        if task_id is None:
            return
        if QMessageBox.question(self, "Delete Task", f"Delete {task_id}?") != QMessageBox.Yes:
            return
        self._store.delete_task(task_id)
        self.refresh()
        self.tasks_changed.emit()

    def _move_task(self, offset: int) -> None:
        task_id = self._selected_task_id()
        if task_id is None:
            return
        self._store.move_task(task_id, offset)
        self.refresh()

    def _bulk_import(self) -> None:
        dialog = BulkImportDialog(self)
        if dialog.exec_():
            for task in dialog.imported_tasks():
                self._store.add_task(task)
            self.refresh()
            self.tasks_changed.emit()

    def _jira_import(self) -> None:
        dialog = JiraImportDialog(self)
        if dialog.exec_():
            for task in dialog.imported_tasks():
                self._store.add_task(task)
            self.refresh()
            self.tasks_changed.emit()
