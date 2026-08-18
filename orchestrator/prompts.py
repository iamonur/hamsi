"""Prompt templates for the Worker and Controller agents, and Controller verdict
parsing. See REQUIREMENTS.md sections 3.2 and 3.3.
"""

from __future__ import annotations

import re
from dataclasses import dataclass
from typing import Optional

from orchestrator.models import Task

WORKER_ONE_SHOT_SUFFIX = (
    "\n\nYou are running unattended in headless mode. Do not ask the user any "
    "questions and do not wait for human interaction — make reasonable decisions "
    "yourself and proceed to completion. When you are done, commit your changes "
    "to the current branch with a clear commit message."
)

CONTROLLER_INSTRUCTIONS = (
    "You are the QA Controller for an autonomous coding pipeline. Inspect the "
    "current git workspace (run `git diff` / `git log` as needed) and evaluate "
    "whether the change fully and correctly satisfies the task below.\n\n"
    "Task summary: {summary}\n"
    "Task description:\n{description}\n\n"
    "You are running unattended — do not ask questions. Reach a verdict yourself.\n"
    "Your FINAL line of output must be exactly one of:\n"
    "VERDICT: PASS\n"
    "VERDICT: FAIL: <one-sentence reason>\n"
)

_VERDICT_RE = re.compile(r"^VERDICT:\s*(PASS|FAIL)(?::\s*(.*))?$", re.IGNORECASE)


def build_worker_prompt(task: Task) -> str:
    prompt = f"Task: {task.summary}\n\n{task.description}"
    if task.last_controller_feedback:
        prompt += (
            "\n\nA previous QA review of your last attempt on this branch found "
            f"it incomplete or incorrect for this reason: {task.last_controller_feedback}\n"
            "Fix the existing branch to address this feedback."
        )
    return prompt + WORKER_ONE_SHOT_SUFFIX


def build_controller_prompt(task: Task) -> str:
    return CONTROLLER_INSTRUCTIONS.format(
        summary=task.summary, description=task.description
    )


@dataclass
class Verdict:
    passed: bool
    reason: Optional[str] = None


def parse_verdict(controller_output: str) -> Verdict:
    """Scans from the end for the last `VERDICT: ...` line. Anything unparseable
    is treated as a FAIL (safe default) per the plan."""
    for line in reversed(controller_output.splitlines()):
        match = _VERDICT_RE.match(line.strip())
        if match:
            status, reason = match.group(1).upper(), match.group(2)
            if status == "PASS":
                return Verdict(passed=True)
            return Verdict(passed=False, reason=(reason or "").strip() or "No reason given.")
    return Verdict(passed=False, reason="Controller produced no parseable verdict.")
