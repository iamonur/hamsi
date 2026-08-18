"""Main window: Queue Dashboard + Live Terminal + Start/Stop + Settings.
See REQUIREMENTS.md section 5."""

from __future__ import annotations

from PyQt5.QtCore import Qt
from PyQt5.QtWidgets import QAction, QMainWindow, QSplitter, QToolBar

from orchestrator.manager_thread import ManagerThread
from orchestrator.state_store import StateStore
from ui.queue_panel import QueuePanel
from ui.settings_dialog import SettingsDialog
from ui.terminal_panel import TerminalPanel


class MainWindow(QMainWindow):
    def __init__(self, store: StateStore, claude_bin: str = "claude"):
        super().__init__()
        self._store = store
        self._claude_bin = claude_bin
        self._manager: ManagerThread | None = None

        self.setWindowTitle("Claude Code Orchestrator")
        self.resize(1200, 720)

        self.queue_panel = QueuePanel(store, self)
        self.terminal_panel = TerminalPanel(self)

        splitter = QSplitter(Qt.Horizontal)
        splitter.addWidget(self.queue_panel)
        splitter.addWidget(self.terminal_panel)
        splitter.setSizes([500, 700])
        self.setCentralWidget(splitter)

        self._build_toolbar()

    def _build_toolbar(self) -> None:
        toolbar = QToolBar("Main")
        self.addToolBar(toolbar)

        self.start_stop_action = QAction("Start Manager", self)
        self.start_stop_action.triggered.connect(self._toggle_manager)
        toolbar.addAction(self.start_stop_action)

        settings_action = QAction("Settings…", self)
        settings_action.triggered.connect(self._open_settings)
        toolbar.addAction(settings_action)

    def _toggle_manager(self) -> None:
        if self._manager is not None and self._manager.isRunning():
            self._manager.request_stop()
            self.start_stop_action.setText("Start Manager")
            return

        self._manager = ManagerThread(self._store, claude_bin=self._claude_bin)
        self._manager.log_line.connect(self.terminal_panel.append_line)
        self._manager.task_changed.connect(lambda _task_id: self.queue_panel.refresh())
        self._manager.finished.connect(lambda: self.start_stop_action.setText("Start Manager"))
        self._manager.start()
        self.start_stop_action.setText("Stop Manager")

    def _open_settings(self) -> None:
        dialog = SettingsDialog(self._store, self)
        dialog.exec_()

    def closeEvent(self, event) -> None:  # noqa: N802 - Qt override
        if self._manager is not None and self._manager.isRunning():
            self._manager.request_stop()
            self._manager.wait(5000)
        super().closeEvent(event)
