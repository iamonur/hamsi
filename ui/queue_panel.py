"""Queue Dashboard panel: task table + Add/Edit/Delete/Move controls, bulk
import, Jira import. See REQUIREMENTS.md 5.1."""

from __future__ import annotations

from typing import Optional

from PyQt5.QtCore import Qt, QTimer, pyqtSignal
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
from orchestrator.task_history import TaskHistoryStore
from ui.bulk_import_dialog import BulkImportDialog
from ui.jira_import_dialog import JiraImportDialog
from ui.task_dialog import TaskDialog
from ui.task_history_dialog import TaskHistoryDialog
from ui.theme import STATE_COLORS

COLUMNS = ["ID", "Summary", "State", "Attempts", "Time Spent", "Repo", "Updated"]
STATE_COL = 2
TIME_COL = 4

TICK_INTERVAL_MS = 1000


def format_duration(seconds: float) -> str:
    """Render a duration as e.g. '45s', '12m 03s', '2h 05m'."""
    total_seconds = int(max(0.0, seconds))
    if total_seconds < 60:
        return f"{total_seconds}s"
    minutes, secs = divmod(total_seconds, 60)
    if minutes < 60:
        return f"{minutes}m {secs:02d}s"
    hours, minutes = divmod(minutes, 60)
    return f"{hours}h {minutes:02d}m"


class _QueueTable(QTableWidget):
    """QTableWidget that reports whole-row drag-and-drop reordering.

    QTableWidget's built-in InternalMove drop handling operates on individual
    cells, not whole rows, so we take over dropEvent entirely: figure out
    which row was dragged onto which row, and let the panel re-fetch/redraw
    from the store rather than trying to shuffle QTableWidgetItems by hand.
    """

    row_reordered = pyqtSignal(int, int)  # source_row, target_row

    def dropEvent(self, event) -> None:
        if event.source() is not self:
            super().dropEvent(event)
            return
        event.ignore()
        source_row = self.currentRow()
        if source_row < 0:
            return
        target_index = self.indexAt(event.pos())
        target_row = target_index.row() if target_index.isValid() else self.rowCount() - 1
        if target_row < 0 or target_row == source_row:
            return
        self.row_reordered.emit(source_row, target_row)


class QueuePanel(QWidget):
    tasks_changed = pyqtSignal()
    refreshed = pyqtSignal(list)  # emitted with the current task list on every refresh

    def __init__(self, store: StateStore, history: Optional[TaskHistoryStore] = None, parent=None):
        super().__init__(parent)
        self._store = store
        self._history = history or TaskHistoryStore(store.path.parent / "task_logs")

        self.table = _QueueTable(0, len(COLUMNS))
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
        header.setSectionResizeMode(5, QHeaderView.Stretch)
        self.table.setContextMenuPolicy(Qt.CustomContextMenu)
        self.table.customContextMenuRequested.connect(self._show_context_menu)
        self.table.itemDoubleClicked.connect(self._edit_task)

        # Drag a row onto another row to re-prioritize it, same underlying
        # operation as the Move Up/Down buttons and context menu actions.
        self.table.setDragEnabled(True)
        self.table.setAcceptDrops(True)
        self.table.setDropIndicatorShown(True)
        self.table.setDragDropMode(QAbstractItemView.InternalMove)
        self.table.setDragDropOverwriteMode(False)
        self.table.row_reordered.connect(self._reorder_task)

        self.add_button = QPushButton("Add")
        self.edit_button = QPushButton("Edit")
        self.clone_button = QPushButton("Clone")
        self.delete_button = QPushButton("Delete")
        self.up_button = QPushButton("Move Up")
        self.down_button = QPushButton("Move Down")
        self.push_button = QPushButton("Push to Remote")
        self.history_button = QPushButton("History")
        self.bulk_import_button = QPushButton("Bulk Import…")
        self.jira_import_button = QPushButton("Import from Jira…")

        self.add_button.clicked.connect(self._add_task)
        self.edit_button.clicked.connect(self._edit_task)
        self.clone_button.clicked.connect(self._clone_task)
        self.delete_button.clicked.connect(self._delete_task)
        self.up_button.clicked.connect(lambda: self._move_task(-1))
        self.down_button.clicked.connect(lambda: self._move_task(1))
        self.push_button.clicked.connect(self._push_to_remote)
        self.history_button.clicked.connect(self._view_history)
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
            self.history_button,
            self.bulk_import_button,
            self.jira_import_button,
        ):
            button_row.addWidget(btn)

        layout = QVBoxLayout()
        layout.addLayout(button_row)
        layout.addWidget(self.table)
        self.setLayout(layout)

        self._tasks_cache: list = []

        self._tick_timer = QTimer(self)
        self._tick_timer.setInterval(TICK_INTERVAL_MS)
        self._tick_timer.timeout.connect(self._tick)
        self._tick_timer.start()

        self.refresh()

    # -- data -----------------------------------------------------------

    def refresh(self) -> None:
        tasks = self._store.list_tasks()
        self._tasks_cache = tasks
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

            time_item = QTableWidgetItem(format_duration(task.total_time_spent_seconds()))
            time_item.setTextAlignment(Qt.AlignCenter)
            self.table.setItem(row, TIME_COL, time_item)

            self.table.setItem(row, 5, QTableWidgetItem(task.repo_url))
            self.table.setItem(row, 6, QTableWidgetItem(task.updated_at.replace("T", " ")[:19]))
        self.refreshed.emit(tasks)

    def _tick(self) -> None:
        """Advance the Time Spent column for tasks currently being worked on,
        without rebuilding the whole table (keeps selection/scroll stable)."""
        for row, task in enumerate(self._tasks_cache):
            if not task.active_since:
                continue
            item = self.table.item(row, TIME_COL)
            if item is not None:
                item.setText(format_duration(task.total_time_spent_seconds()))

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

    def _reorder_task(self, source_row: int, target_row: int) -> None:
        item = self.table.item(source_row, 0)
        if item is None:
            return
        self._store.reorder_task(item.text(), target_row)
        self.refresh()
        self.table.selectRow(target_row)
        self.tasks_changed.emit()

    def _view_history(self) -> None:
        task_id = self._selected_task_id()
        if task_id is None:
            return
        task = self._store.get_task(task_id)
        if task is None:
            return
        dialog = TaskHistoryDialog(task, self._history, self)
        dialog.exec_()

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
        menu.addAction("View History", self._view_history)
        menu.exec_(self.table.viewport().mapToGlobal(pos))

    def _show_empty_context_menu(self, pos) -> None:
        menu = QMenu(self)
        menu.addAction("Add", self._add_task)
        menu.addAction("Bulk Import…", self._bulk_import)
        menu.addAction("Import from Jira…", self._jira_import)
        menu.exec_(self.table.viewport().mapToGlobal(pos))
