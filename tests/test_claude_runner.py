import json

from orchestrator.claude_runner import _format_stream_json_line


def test_assistant_text_block_is_displayed():
    line = json.dumps({"type": "assistant", "message": {"content": [{"type": "text", "text": "Working on it"}]}})
    display, result = _format_stream_json_line(line)
    assert display == "Working on it"
    assert result is None


def test_assistant_tool_use_block_is_summarized():
    line = json.dumps({"type": "assistant", "message": {"content": [{"type": "tool_use", "name": "Bash"}]}})
    display, _ = _format_stream_json_line(line)
    assert display == "→ using Bash"


def test_user_tool_error_is_surfaced():
    line = json.dumps({
        "type": "user",
        "message": {"content": [{"type": "tool_result", "is_error": True, "content": "boom"}]},
    })
    display, result = _format_stream_json_line(line)
    assert "boom" in display
    assert result is None


def test_user_tool_result_without_error_is_suppressed():
    line = json.dumps({
        "type": "user",
        "message": {"content": [{"type": "tool_result", "is_error": False, "content": "ok"}]},
    })
    display, result = _format_stream_json_line(line)
    assert display is None
    assert result is None


def test_result_message_sets_final_result_text():
    line = json.dumps({"type": "result", "result": "VERDICT: PASS"})
    display, result = _format_stream_json_line(line)
    assert display == "[done] VERDICT: PASS"
    assert result == "VERDICT: PASS"


def test_non_json_line_passes_through_verbatim():
    display, result = _format_stream_json_line("Warning: something not JSON")
    assert display == "Warning: something not JSON"
    assert result is None
