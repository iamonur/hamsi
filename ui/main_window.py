"""Main window: Queue Dashboard + Live Terminal + Start/Stop + Settings.
See REQUIREMENTS.md section 5."""

from __future__ import annotations

from PyQt5.QtCore import Qt
from PyQt5.QtWidgets import (
    QAction,
    QApplication,
    QLabel,
    QMainWindow,
    QSplitter,
    QToolBar,
    QVBoxLayout,
    QWidget,
)

from orchestrator.manager_thread import ManagerThread
from orchestrator.state_store import StateStore
from ui import theme
from ui.queue_panel import QueuePanel
from ui.settings_dialog import SettingsDialog
from ui.stats_panel import StatsPanel
from ui.terminal_panel import TerminalPanel


class MainWindow(QMainWindow):
    def __init__(self, store: StateStore, claude_bin: str = "claude"):
        super().__init__()
        self._store = store
        self._claude_bin = claude_bin
        self._manager: ManagerThread | None = None
        self._dark_mode = True

        self.setWindowTitle("⚡ Claude Code Orchestrator")
        self.resize(1280, 780)

        self.stats_panel = StatsPanel(self)
        self.queue_panel = QueuePanel(store, self)
        self.terminal_panel = TerminalPanel(self)
        self.queue_panel.refreshed.connect(self.stats_panel.update_counts)
        # QueuePanel already ran its own refresh() during __init__, before the
        # signal above existed, so the stats panel missed that first emit.
        self.stats_panel.update_counts(store.list_tasks())

        splitter = QSplitter(Qt.Horizontal)
        splitter.addWidget(self.queue_panel)
        splitter.addWidget(self.terminal_panel)
        splitter.setSizes([560, 720])

        central = QWidget(self)
        layout = QVBoxLayout(central)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.setSpacing(8)
        layout.addWidget(self.stats_panel)
        layout.addWidget(splitter)
        self.setCentralWidget(central)

        self._build_toolbar()
        self._build_status_bar()

    def _build_toolbar(self) -> None:
        toolbar = QToolBar("Main")
        toolbar.setMovable(False)
        self.addToolBar(toolbar)

        self.start_stop_action = QAction("▶  Start Manager", self)
        self.start_stop_action.triggered.connect(self._toggle_manager)
        toolbar.addAction(self.start_stop_action)

        toolbar.addSeparator()

        settings_action = QAction("⚙  Settings…", self)
        settings_action.triggered.connect(self._open_settings)
        toolbar.addAction(settings_action)

        theme_action = QAction("🌓  Toggle Theme", self)
        theme_action.triggered.connect(self._toggle_theme)
        toolbar.addAction(theme_action)

    def _build_status_bar(self) -> None:
        self.manager_status_label = QLabel("Manager: Idle")
        self.statusBar().addPermanentWidget(self.manager_status_label)
        self.statusBar().showMessage("Ready")

    def _toggle_theme(self) -> None:
        self._dark_mode = not self._dark_mode
        app = QApplication.instance()
        if app is not None:
            theme.apply_theme(app, self._dark_mode)

    def _toggle_manager(self) -> None:
        if self._manager is not None and self._manager.isRunning():
            self._manager.request_stop()
            self.start_stop_action.setText("▶  Start Manager")
            self.manager_status_label.setText("Manager: Stopping…")
            return

        self._manager = ManagerThread(self._store, claude_bin=self._claude_bin)
        self._manager.log_line.connect(self.terminal_panel.append_line)
        self._manager.task_changed.connect(lambda _task_id: self.queue_panel.refresh())
        self._manager.finished.connect(self._on_manager_finished)
        self._manager.start()
        self.start_stop_action.setText("■  Stop Manager")
        self.manager_status_label.setText("Manager: Running")

    def _on_manager_finished(self) -> None:
        self.start_stop_action.setText("▶  Start Manager")
        self.manager_status_label.setText("Manager: Idle")

    def _open_settings(self) -> None:
        dialog = SettingsDialog(self._store, self)
        dialog.exec_()

    def closeEvent(self, event) -> None:  # noqa: N802 - Qt override
        if self._manager is not None and self._manager.isRunning():
            self._manager.request_stop()
            self._manager.wait(5000)
        super().closeEvent(event)
