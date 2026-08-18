"""Add/Edit task form dialog. See REQUIREMENTS.md 5.1."""

from __future__ import annotations

from typing import Optional

from PyQt5.QtWidgets import (
    QCheckBox,
    QDialog,
    QDialogButtonBox,
    QFormLayout,
    QLabel,
    QLineEdit,
    QPlainTextEdit,
    QTabWidget,
    QVBoxLayout,
    QWidget,
)

from orchestrator.models import Task
from orchestrator.prompts import DEFAULT_QA_CRITERIA


class TaskDialog(QDialog):
    def __init__(self, parent=None, task: Optional[Task] = None):
        super().__init__(parent)
        self._task = task
        self.setWindowTitle("Edit Task" if task else "Add Task")
        self.resize(520, 480)

        self.summary_edit = QLineEdit(task.summary if task else "")
        self.description_edit = QPlainTextEdit(task.description if task else "")
        self.repo_url_edit = QLineEdit(task.repo_url if task else "")

        details_form = QFormLayout()
        details_form.addRow("Summary", self.summary_edit)
        details_form.addRow("Description", self.description_edit)
        details_form.addRow("Target Repository URL", self.repo_url_edit)
        details_tab = QWidget()
        details_tab.setLayout(details_form)

        self.use_default_qa_checkbox = QCheckBox("Include default QA criteria")
        self.use_default_qa_checkbox.setChecked(
            task.use_default_qa_criteria if task else True
        )
        default_qa_label = QLabel(DEFAULT_QA_CRITERIA)
        default_qa_label.setWordWrap(True)
        self.qa_criteria_edit = QPlainTextEdit(task.qa_criteria if task else "")
        self.qa_criteria_edit.setPlaceholderText(
            "Optional extra criteria the Controller agent should check for this task…"
        )

        qa_layout = QVBoxLayout()
        qa_layout.addWidget(self.use_default_qa_checkbox)
        qa_layout.addWidget(QLabel("Default criteria:"))
        qa_layout.addWidget(default_qa_label)
        qa_layout.addWidget(QLabel("Custom criteria:"))
        qa_layout.addWidget(self.qa_criteria_edit)
        qa_tab = QWidget()
        qa_tab.setLayout(qa_layout)

        tabs = QTabWidget()
        tabs.addTab(details_tab, "Details")
        tabs.addTab(qa_tab, "QA Criteria")

        buttons = QDialogButtonBox(QDialogButtonBox.Ok | QDialogButtonBox.Cancel)
        buttons.accepted.connect(self.accept)
        buttons.rejected.connect(self.reject)

        layout = QVBoxLayout()
        layout.addWidget(tabs)
        layout.addWidget(buttons)
        self.setLayout(layout)

    def result_task(self) -> Task:
        summary = self.summary_edit.text().strip()
        description = self.description_edit.toPlainText().strip()
        repo_url = self.repo_url_edit.text().strip()
        qa_criteria = self.qa_criteria_edit.toPlainText().strip()
        use_default_qa_criteria = self.use_default_qa_checkbox.isChecked()
        if self._task:
            self._task.summary = summary
            self._task.description = description
            self._task.repo_url = repo_url
            self._task.qa_criteria = qa_criteria
            self._task.use_default_qa_criteria = use_default_qa_criteria
            return self._task
        return Task.new(
            summary=summary,
            description=description,
            repo_url=repo_url,
            qa_criteria=qa_criteria,
            use_default_qa_criteria=use_default_qa_criteria,
        )
