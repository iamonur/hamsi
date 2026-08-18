"""Queue Dashboard panel: task table + Add/Edit/Delete/Move controls, bulk
import, Jira import. See REQUIREMENTS.md 5.1."""

from __future__ import annotations

from PyQt5.QtCore import Qt, pyqtSignal
from PyQt5.QtGui import QColor
from PyQt5.QtWidgets import (
    QAbstractItemView,
    QHBoxLayout,
    QHeaderView,
    QMenu,
    QMessageBox,
    QPushButton,
    QTableWidget,
    QTableWidgetItem,
    QVBoxLayout,
    QWidget,
)

from orchestrator import git_ops
from orchestrator.state_store import StateStore
from ui.bulk_import_dialog import BulkImportDialog
from ui.jira_import_dialog import JiraImportDialog
from ui.task_dialog import TaskDialog
from ui.theme import STATE_COLORS

COLUMNS = ["ID", "Summary", "State", "Attempts", "Repo", "Updated"]
STATE_COL = 2


class QueuePanel(QWidget):
    tasks_changed = pyqtSignal()
    refreshed = pyqtSignal(list)  # emitted with the current task list on every refresh

    def __init__(self, store: StateStore, parent=None):
        super().__init__(parent)
        self._store = store

        self.table = QTableWidget(0, len(COLUMNS))
        self.table.setHorizontalHeaderLabels(COLUMNS)
        self.table.setSelectionBehavior(QAbstractItemView.SelectRows)
        self.table.setSelectionMode(QAbstractItemView.SingleSelection)
        self.table.setEditTriggers(QAbstractItemView.NoEditTriggers)
        self.table.setAlternatingRowColors(True)
        # Row order is priority order (see Move Up/Down below), so the table
        # is intentionally not sortable-by-column - that would decouple the
        # visible order from what those buttons actually move.
        self.table.verticalHeader().setVisible(False)
        header = self.table.horizontalHeader()
        header.setSectionResizeMode(1, QHeaderView.Stretch)
        header.setSectionResizeMode(4, QHeaderView.Stretch)
        self.table.setContextMenuPolicy(Qt.CustomContextMenu)
        self.table.customContextMenuRequested.connect(self._show_context_menu)

        self.add_button = QPushButton("Add")
        self.edit_button = QPushButton("Edit")
        self.clone_button = QPushButton("Clone")
        self.delete_button = QPushButton("Delete")
        self.up_button = QPushButton("Move Up")
        self.down_button = QPushButton("Move Down")
        self.push_button = QPushButton("Push to Remote")
        self.bulk_import_button = QPushButton("Bulk Import…")
        self.jira_import_button = QPushButton("Import from Jira…")

        self.add_button.clicked.connect(self._add_task)
        self.edit_button.clicked.connect(self._edit_task)
        self.clone_button.clicked.connect(self._clone_task)
        self.delete_button.clicked.connect(self._delete_task)
        self.up_button.clicked.connect(lambda: self._move_task(-1))
        self.down_button.clicked.connect(lambda: self._move_task(1))
        self.push_button.clicked.connect(self._push_to_remote)
        self.bulk_import_button.clicked.connect(self._bulk_import)
        self.jira_import_button.clicked.connect(self._jira_import)

        button_row = QHBoxLayout()
        for btn in (
            self.add_button,
            self.edit_button,
            self.clone_button,
            self.delete_button,
            self.up_button,
            self.down_button,
            self.push_button,
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

            state_item = QTableWidgetItem(task.state.value)
            color = QColor(STATE_COLORS[task.state])
            state_item.setBackground(color)
            state_item.setForeground(QColor("#0f1117"))
            state_item.setTextAlignment(Qt.AlignCenter)
            font = state_item.font()
            font.setBold(True)
            state_item.setFont(font)
            if task.last_controller_feedback:
                state_item.setToolTip(task.last_controller_feedback)
            self.table.setItem(row, STATE_COL, state_item)

            self.table.setItem(row, 3, QTableWidgetItem(str(task.attempt_count)))
            self.table.setItem(row, 4, QTableWidgetItem(task.repo_url))
            self.table.setItem(row, 5, QTableWidgetItem(task.updated_at.replace("T", " ")[:19]))
        self.refreshed.emit(tasks)

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

    def _clone_task(self) -> None:
        task_id = self._selected_task_id()
        if task_id is None:
            return
        if self._store.clone_task(task_id) is None:
            return
        self.refresh()
        self.tasks_changed.emit()

    def _delete_task(self) -> None:
        task_id = self._selected_task_id()
        if task_id is None:
            return
        if QMessageBox.question(self, "Delete Task", f"Delete {task_id}?") != QMessageBox.Yes:
            return
        self._store.delete_task(task_id)
        git_ops.delete_workspace(task_id)
        self.refresh()
        self.tasks_changed.emit()

    def _move_task(self, offset: int) -> None:
        task_id = self._selected_task_id()
        if task_id is None:
            return
        self._store.move_task(task_id, offset)
        self.refresh()

    def _push_to_remote(self) -> None:
        task_id = self._selected_task_id()
        if task_id is None:
            return
        task = self._store.get_task(task_id)
        if task is None or not task.workspace_path or not task.branch:
            QMessageBox.warning(
                self, "Push to Remote", "This task has no local branch yet — run it first."
            )
            return
        try:
            git_ops.push_to_remote(task.id, task.branch)
        except git_ops.GitOpsError as exc:
            QMessageBox.warning(self, "Push Failed", str(exc))
            return
        QMessageBox.information(self, "Push to Remote", f"Pushed {task.branch} to origin.")

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

    # -- context menu -----------------------------------------------------

    def _show_context_menu(self, pos) -> None:
        row = self.table.indexAt(pos).row()
        if row >= 0:
            self.table.selectRow(row)
            self._show_task_context_menu(pos)
        else:
            self._show_empty_context_menu(pos)

    def _show_task_context_menu(self, pos) -> None:
        menu = QMenu(self)
        menu.addAction("Edit", self._edit_task)
        menu.addAction("Clone", self._clone_task)
        menu.addAction("Delete", self._delete_task)
        menu.addSeparator()
        menu.addAction("Move Up", lambda: self._move_task(-1))
        menu.addAction("Move Down", lambda: self._move_task(1))
        menu.addSeparator()
        menu.addAction("Push to Remote", self._push_to_remote)
        menu.exec_(self.table.viewport().mapToGlobal(pos))

    def _show_empty_context_menu(self, pos) -> None:
        menu = QMenu(self)
        menu.addAction("Add", self._add_task)
        menu.addAction("Bulk Import…", self._bulk_import)
        menu.addAction("Import from Jira…", self._jira_import)
        menu.exec_(self.table.viewport().mapToGlobal(pos))
