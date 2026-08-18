"""Read-only, color-coded live terminal output panel. See REQUIREMENTS.md 5.2."""

from __future__ import annotations

import html
from datetime import datetime
from typing import Optional

from PyQt5.QtWidgets import QTextEdit

AGENT_COLORS = {
    "manager": "#4da6ff",     # blue
    "worker": "#4dd472",      # green
    "controller": "#d979e0",  # magenta
    "system": "#ff5c5c",      # red
}


class TerminalPanel(QTextEdit):
    def __init__(self, parent=None):
        super().__init__(parent)
        self.setReadOnly(True)
        self.setLineWrapMode(QTextEdit.NoWrap)
        self.setStyleSheet(
            "QTextEdit { background-color: #0f1117; color: #e6e8f0; "
            "border: 1px solid #2a2f42; border-radius: 6px; "
            "font-family: Menlo, Consolas, monospace; font-size: 12px; }"
        )

    def append_line(self, agent: str, text: str, timestamp: Optional[str] = None) -> None:
        """Appends one log line. `timestamp`, if given, is an ISO-8601 string
        (e.g. from a persisted audit log entry) rendered instead of "now" -
        used when replaying a task's history rather than showing it live.
        """
        color = AGENT_COLORS.get(agent, "#e0e0e0")
        when = datetime.fromisoformat(timestamp) if timestamp else datetime.now()
        clock = when.strftime("%H:%M:%S")
        escaped = html.escape(text)
        self.append(
            f'<span style="color:#5b6072">{clock}</span> '
            f'<span style="color:{color}; font-weight:600;">[{agent}]</span> {escaped}'
        )
