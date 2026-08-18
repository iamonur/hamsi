"""Visual theme: color palette, per-state colors, and Qt stylesheets.

Two themes are offered (dark is the default, flashy one; light is a
disciplined alternative) plus a shared color map for task states so the
queue table, the state chart, and status indicators all agree on meaning.
"""

from __future__ import annotations

from PyQt5.QtWidgets import QApplication

from orchestrator.models import TaskState

# Task state -> accent color. Used by the queue table badges and the state chart.
STATE_COLORS: dict[TaskState, str] = {
    TaskState.BACKLOG: "#8b93a7",
    TaskState.IN_PROGRESS: "#3ea6ff",
    TaskState.IN_REVIEW: "#c084fc",
    TaskState.WILL_RETRY: "#f5a524",
    TaskState.DONE: "#2ecc71",
    TaskState.FAILED: "#ef4444",
}

ACCENT = "#7c5cff"
ACCENT_2 = "#00d9c0"

DARK = {
    "bg": "#0f1117",
    "surface": "#171a24",
    "surface_alt": "#1d2130",
    "border": "#2a2f42",
    "text": "#e6e8f0",
    "muted": "#9aa1b5",
    "accent": ACCENT,
    "accent_2": ACCENT_2,
}

LIGHT = {
    "bg": "#f4f5f9",
    "surface": "#ffffff",
    "surface_alt": "#eceefb",
    "border": "#d7dae5",
    "text": "#1b1e2b",
    "muted": "#5b6072",
    "accent": "#5b3df0",
    "accent_2": "#0891a3",
}


def _build_qss(p: dict) -> str:
    return f"""
    QMainWindow, QDialog, QWidget {{
        background-color: {p['bg']};
        color: {p['text']};
        font-size: 13px;
    }}

    QToolBar {{
        background-color: {p['surface']};
        border-bottom: 1px solid {p['border']};
        padding: 6px;
        spacing: 6px;
    }}

    QStatusBar {{
        background-color: {p['surface']};
        border-top: 1px solid {p['border']};
        color: {p['muted']};
    }}

    QPushButton {{
        background-color: {p['surface_alt']};
        color: {p['text']};
        border: 1px solid {p['border']};
        border-radius: 6px;
        padding: 6px 12px;
    }}
    QPushButton:hover {{
        border-color: {p['accent']};
        color: {p['accent']};
    }}
    QPushButton:pressed {{
        background-color: {p['accent']};
        color: #ffffff;
    }}
    QPushButton:disabled {{
        color: {p['muted']};
        border-color: {p['border']};
    }}

    QToolButton {{
        background-color: transparent;
        border: none;
        color: {p['text']};
        padding: 6px 10px;
        border-radius: 6px;
    }}
    QToolButton:hover {{
        background-color: {p['surface_alt']};
        color: {p['accent']};
    }}

    QLineEdit, QPlainTextEdit, QSpinBox {{
        background-color: {p['surface']};
        border: 1px solid {p['border']};
        border-radius: 4px;
        padding: 4px 6px;
        color: {p['text']};
        selection-background-color: {p['accent']};
    }}
    QLineEdit:focus, QPlainTextEdit:focus, QSpinBox:focus {{
        border-color: {p['accent']};
    }}

    QTableWidget {{
        background-color: {p['surface']};
        alternate-background-color: {p['surface_alt']};
        gridline-color: {p['border']};
        border: 1px solid {p['border']};
        border-radius: 6px;
        selection-background-color: {p['accent']};
        selection-color: #ffffff;
    }}
    QHeaderView::section {{
        background-color: {p['surface_alt']};
        color: {p['muted']};
        padding: 6px;
        border: none;
        border-bottom: 2px solid {p['border']};
        font-weight: 600;
    }}

    QTabWidget::pane {{
        border: 1px solid {p['border']};
        border-radius: 6px;
        top: -1px;
    }}
    QTabBar::tab {{
        background-color: {p['surface']};
        color: {p['muted']};
        padding: 8px 14px;
        border: 1px solid {p['border']};
        border-bottom: none;
        border-top-left-radius: 6px;
        border-top-right-radius: 6px;
    }}
    QTabBar::tab:selected {{
        color: {p['accent']};
        background-color: {p['surface_alt']};
    }}

    QSplitter::handle {{
        background-color: {p['border']};
    }}
    QSplitter::handle:horizontal {{
        width: 2px;
    }}

    QScrollBar:vertical {{
        background: {p['surface']};
        width: 12px;
        margin: 0;
    }}
    QScrollBar::handle:vertical {{
        background: {p['border']};
        border-radius: 5px;
        min-height: 24px;
    }}
    QScrollBar::handle:vertical:hover {{
        background: {p['accent']};
    }}
    QScrollBar::add-line:vertical, QScrollBar::sub-line:vertical {{
        height: 0;
    }}

    QMessageBox QLabel {{
        color: {p['text']};
    }}

    QToolTip {{
        background-color: {p['surface_alt']};
        color: {p['text']};
        border: 1px solid {p['accent']};
        padding: 4px;
    }}
    """


DARK_QSS = _build_qss(DARK)
LIGHT_QSS = _build_qss(LIGHT)


def palette(dark: bool) -> dict:
    return DARK if dark else LIGHT


def apply_theme(app: QApplication, dark: bool) -> None:
    app.setStyleSheet(DARK_QSS if dark else LIGHT_QSS)
