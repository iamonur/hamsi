"""Parameters & Environment modal: Environment Variables tab + App Settings tab.
See REQUIREMENTS.md 5.3."""

from __future__ import annotations

from PyQt5.QtCore import Qt
from PyQt5.QtWidgets import (
    QDialog,
    QDialogButtonBox,
    QFormLayout,
    QHBoxLayout,
    QHeaderView,
    QMessageBox,
    QPushButton,
    QSpinBox,
    QTableWidget,
    QTableWidgetItem,
    QTabWidget,
    QVBoxLayout,
    QWidget,
)

from orchestrator import env_store
from orchestrator.env_catalog import KNOWN_ENV_VARS, describe
from orchestrator.state_store import AppSettings, StateStore

NAME_COL, VALUE_COL = 0, 1


class _EnvVarsTab(QWidget):
    def __init__(self, parent=None):
        super().__init__(parent)
        self.table = QTableWidget(0, 2)
        self.table.setHorizontalHeaderLabels(["Variable", "Value"])
        self.table.horizontalHeader().setSectionResizeMode(VALUE_COL, QHeaderView.Stretch)

        self.add_button = QPushButton("Add Custom Variable")
        self.delete_button = QPushButton("Delete Selected")
        self.add_button.clicked.connect(self._add_row)
        self.delete_button.clicked.connect(self._delete_row)

        button_row = QHBoxLayout()
        button_row.addWidget(self.add_button)
        button_row.addWidget(self.delete_button)

        layout = QVBoxLayout()
        layout.addLayout(button_row)
        layout.addWidget(self.table)
        self.setLayout(layout)

        self._load()

    def _load(self) -> None:
        current = env_store.read_env()
        known_names = [v.name for v in KNOWN_ENV_VARS]
        custom_names = [n for n in current if n not in known_names]
        names = known_names + custom_names
        self.table.setRowCount(len(names))
        for row, name in enumerate(names):
            name_item = QTableWidgetItem(name)
            name_item.setToolTip(describe(name))
            name_item.setFlags(name_item.flags() & ~Qt.ItemIsEditable)
            self.table.setItem(row, NAME_COL, name_item)
            self.table.setItem(row, VALUE_COL, QTableWidgetItem(current.get(name, "")))

    def _add_row(self) -> None:
        row = self.table.rowCount()
        self.table.insertRow(row)
        self.table.setItem(row, NAME_COL, QTableWidgetItem(""))
        self.table.setItem(row, VALUE_COL, QTableWidgetItem(""))

    def _delete_row(self) -> None:
        rows = sorted({idx.row() for idx in self.table.selectedIndexes()}, reverse=True)
        for row in rows:
            self.table.removeRow(row)

    def values(self) -> dict:
        values = {}
        for row in range(self.table.rowCount()):
            name_item = self.table.item(row, NAME_COL)
            value_item = self.table.item(row, VALUE_COL)
            name = (name_item.text().strip() if name_item else "")
            if not name:
                continue
            values[name] = value_item.text() if value_item else ""
        return values


class _AppSettingsTab(QWidget):
    def __init__(self, settings: AppSettings, parent=None):
        super().__init__(parent)

        self.retry_interval_spin = QSpinBox()
        self.retry_interval_spin.setRange(1, 240)
        self.retry_interval_spin.setValue(settings.retry_interval_minutes)

        self.max_retries_spin = QSpinBox()
        self.max_retries_spin.setRange(1, 1000)
        self.max_retries_spin.setValue(settings.max_retries)

        self.task_timeout_spin = QSpinBox()
        self.task_timeout_spin.setRange(1, 600)
        self.task_timeout_spin.setValue(settings.task_timeout_minutes)

        form = QFormLayout()
        form.addRow("Retry interval (minutes)", self.retry_interval_spin)
        form.addRow("Max retries", self.max_retries_spin)
        form.addRow("Task timeout (minutes)", self.task_timeout_spin)
        self.setLayout(form)

    def values(self) -> AppSettings:
        return AppSettings(
            retry_interval_minutes=self.retry_interval_spin.value(),
            max_retries=self.max_retries_spin.value(),
            task_timeout_minutes=self.task_timeout_spin.value(),
        )


class SettingsDialog(QDialog):
    def __init__(self, store: StateStore, parent=None):
        super().__init__(parent)
        self._store = store
        self.setWindowTitle("Parameters & Environment")
        self.resize(600, 450)

        self.env_tab = _EnvVarsTab(self)
        self.app_settings_tab = _AppSettingsTab(store.get_settings(), self)

        tabs = QTabWidget()
        tabs.addTab(self.env_tab, "Environment Variables")
        tabs.addTab(self.app_settings_tab, "App Settings")

        buttons = QDialogButtonBox(QDialogButtonBox.Save | QDialogButtonBox.Cancel)
        buttons.accepted.connect(self._save)
        buttons.rejected.connect(self.reject)

        layout = QVBoxLayout()
        layout.addWidget(tabs)
        layout.addWidget(buttons)
        self.setLayout(layout)

    def _save(self) -> None:
        try:
            env_store.write_env(self.env_tab.values())
            self._store.update_settings(self.app_settings_tab.values())
        except OSError as exc:
            QMessageBox.critical(self, "Save Failed", str(exc))
            return
        self.accept()
