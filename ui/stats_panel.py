"""Task state dashboard: a stacked bar chart + colored legend chips showing
how many tasks are in each TaskState. Drawn with QPainter so no charting
dependency is required. See REQUIREMENTS.md 4.3 for the state machine."""

from __future__ import annotations

from typing import Dict, List

from PyQt5.QtCore import QRectF, Qt
from PyQt5.QtGui import QColor, QPainter, QPainterPath
from PyQt5.QtWidgets import QHBoxLayout, QLabel, QSizePolicy, QVBoxLayout, QWidget

from orchestrator.models import Task, TaskState
from ui.theme import STATE_COLORS

BAR_HEIGHT = 22
BAR_RADIUS = 6


class _StackedBar(QWidget):
    """A single horizontal bar, proportionally segmented by task state."""

    def __init__(self, parent=None):
        super().__init__(parent)
        self._counts: Dict[TaskState, int] = {}
        self.setMinimumHeight(BAR_HEIGHT)
        self.setSizePolicy(QSizePolicy.Expanding, QSizePolicy.Fixed)

    def set_counts(self, counts: Dict[TaskState, int]) -> None:
        self._counts = counts
        self.update()

    def paintEvent(self, event) -> None:  # noqa: N802 - Qt override
        painter = QPainter(self)
        painter.setRenderHint(QPainter.Antialiasing)

        rect = QRectF(0, 0, self.width(), self.height())
        total = sum(self._counts.values())

        painter.setPen(Qt.NoPen)
        painter.setBrush(QColor("#2a2f42"))
        painter.drawRoundedRect(rect, BAR_RADIUS, BAR_RADIUS)

        if total == 0:
            painter.end()
            return

        painter.setClipPath(_rounded_path(rect, BAR_RADIUS))
        x = 0.0
        for state in TaskState:
            count = self._counts.get(state, 0)
            if count <= 0:
                continue
            segment_width = rect.width() * (count / total)
            segment_rect = QRectF(x, 0, segment_width, self.height())
            painter.setBrush(QColor(STATE_COLORS[state]))
            painter.drawRect(segment_rect)
            x += segment_width
        painter.end()


def _rounded_path(rect: QRectF, radius: float) -> QPainterPath:
    path = QPainterPath()
    path.addRoundedRect(rect, radius, radius)
    return path


class _LegendChip(QWidget):
    def __init__(self, state: TaskState, parent=None):
        super().__init__(parent)
        self._state = state

        self.dot = QLabel()
        self.dot.setFixedSize(10, 10)
        self.dot.setStyleSheet(
            f"background-color: {STATE_COLORS[state]}; border-radius: 5px;"
        )

        self.label = QLabel(f"{state.value}: 0")
        self.label.setStyleSheet("font-weight: 600;")

        layout = QHBoxLayout()
        layout.setContentsMargins(0, 0, 0, 0)
        layout.setSpacing(6)
        layout.addWidget(self.dot)
        layout.addWidget(self.label)
        self.setLayout(layout)

    def set_count(self, count: int) -> None:
        self.label.setText(f"{self._state.value}: {count}")


class StatsPanel(QWidget):
    """Live dashboard summarizing the task queue by state."""

    def __init__(self, parent=None):
        super().__init__(parent)

        self.title = QLabel("Task Overview")
        self.title.setStyleSheet("font-size: 15px; font-weight: 700;")

        self.total_label = QLabel("0 tasks")
        self.total_label.setStyleSheet("color: #9aa1b5;")

        header_row = QHBoxLayout()
        header_row.addWidget(self.title)
        header_row.addStretch(1)
        header_row.addWidget(self.total_label)

        self.bar = _StackedBar(self)

        self._chips: Dict[TaskState, _LegendChip] = {}
        legend_row = QHBoxLayout()
        legend_row.setSpacing(16)
        for state in TaskState:
            chip = _LegendChip(state, self)
            self._chips[state] = chip
            legend_row.addWidget(chip)
        legend_row.addStretch(1)

        layout = QVBoxLayout()
        layout.addLayout(header_row)
        layout.addWidget(self.bar)
        layout.addLayout(legend_row)
        layout.setContentsMargins(12, 10, 12, 10)
        self.setLayout(layout)

    def update_counts(self, tasks: List[Task]) -> None:
        counts: Dict[TaskState, int] = {state: 0 for state in TaskState}
        for task in tasks:
            counts[task.state] = counts.get(task.state, 0) + 1

        self.bar.set_counts(counts)
        for state, chip in self._chips.items():
            chip.set_count(counts.get(state, 0))

        total = len(tasks)
        self.total_label.setText(f"{total} task{'s' if total != 1 else ''} total")
