"""Runs the `claude` CLI headlessly and streams output line-by-line via a callback.

Uses `--output-format stream-json --verbose`: plain `-p` text mode only prints
the final response once the whole turn finishes, which made the Live Terminal
panel look dead for the entire (often multi-minute) duration of a Worker/
Controller run even though work was genuinely happening. stream-json emits one
JSON object per message/tool-use as it occurs, which we turn into
human-readable lines.
"""

from __future__ import annotations

import json
import subprocess
import time
from dataclasses import dataclass
from pathlib import Path
from typing import Callable, Dict, Optional, Tuple

LineCallback = Callable[[str], None]


class ClaudeTimeoutError(RuntimeError):
    pass


@dataclass
class ClaudeRunResult:
    exit_code: int
    output: str


def _format_stream_json_line(raw_line: str) -> Tuple[Optional[str], Optional[str]]:
    """Turns one `stream-json` line into (display_text, final_result_text).

    Either element may be None: display_text is None for events not worth
    surfacing (e.g. session init), final_result_text is only set on the
    terminal `result` message. Lines that aren't valid JSON (stray warnings
    printed to stderr, etc.) are passed through as display text verbatim.
    """
    try:
        obj = json.loads(raw_line)
    except (json.JSONDecodeError, ValueError):
        return raw_line, None

    msg_type = obj.get("type")

    if msg_type == "assistant":
        parts = []
        for block in obj.get("message", {}).get("content", []):
            block_type = block.get("type")
            if block_type == "text":
                text = block.get("text", "").strip()
                if text:
                    parts.append(text)
            elif block_type == "tool_use":
                parts.append(f"→ using {block.get('name', 'tool')}")
        return ("\n".join(parts) or None), None

    if msg_type == "user":
        for block in obj.get("message", {}).get("content", []):
            if block.get("type") == "tool_result" and block.get("is_error"):
                return f"⚠ tool error: {block.get('content')}", None
        return None, None

    if msg_type == "result":
        result_text = obj.get("result", "") or ""
        return f"[done] {result_text[:200]}", result_text

    if msg_type == "system" and obj.get("subtype") == "api_retry":
        return f"(retrying API call: {obj.get('error')})", None

    return None, None


def run_claude(
    prompt: str,
    cwd: Path,
    env: Dict[str, str],
    on_line: LineCallback,
    timeout_seconds: float,
    claude_bin: str = "claude",
) -> ClaudeRunResult:
    """Runs `claude -p <prompt> --dangerously-skip-permissions --output-format
    stream-json --verbose` in `cwd`, streaming human-readable progress lines
    to `on_line` as they arrive. Raises ClaudeTimeoutError if the process
    exceeds `timeout_seconds`.
    """
    proc = subprocess.Popen(
        [
            claude_bin,
            "-p",
            prompt,
            "--dangerously-skip-permissions",
            "--output-format",
            "stream-json",
            "--verbose",
        ],
        cwd=str(cwd),
        env=env,
        stdin=subprocess.DEVNULL,
        stdout=subprocess.PIPE,
        stderr=subprocess.STDOUT,
        text=True,
        bufsize=1,
    )

    final_result_text: Optional[str] = None
    raw_lines: list[str] = []
    deadline = time.monotonic() + timeout_seconds
    try:
        assert proc.stdout is not None
        for line in proc.stdout:
            raw_lines.append(line)
            display, result_text = _format_stream_json_line(line.rstrip("\n"))
            if display:
                on_line(display)
            if result_text is not None:
                final_result_text = result_text
            if time.monotonic() > deadline:
                proc.kill()
                proc.wait()
                raise ClaudeTimeoutError(
                    f"claude did not finish within {timeout_seconds:.0f}s"
                )
        exit_code = proc.wait(timeout=max(0.0, deadline - time.monotonic()) or 1)
    except subprocess.TimeoutExpired:
        proc.kill()
        proc.wait()
        raise ClaudeTimeoutError(f"claude did not finish within {timeout_seconds:.0f}s")
    finally:
        if proc.poll() is None:
            proc.kill()

    output = final_result_text if final_result_text is not None else "".join(raw_lines)
    return ClaudeRunResult(exit_code=exit_code, output=output)
