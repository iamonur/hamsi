"""Entry point: Claude Code Orchestrator desktop app."""

from __future__ import annotations

import os
import sys

from PyQt5.QtWidgets import QApplication

from orchestrator import env_store
from orchestrator.state_store import StateStore
from ui.main_window import MainWindow


def main() -> int:
    # Merge .env into the process environment before anything else runs, so
    # both this process and any subprocess it spawns see the same values.
    os.environ.update(env_store.read_env())

    app = QApplication(sys.argv)
    store = StateStore()
    window = MainWindow(store)
    window.show()
    return app.exec_()


if __name__ == "__main__":
    sys.exit(main())
