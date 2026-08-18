from orchestrator.models import Task
from orchestrator.prompts import build_controller_prompt, build_worker_prompt, parse_verdict


def make_task(**overrides) -> Task:
    task = Task.new(summary="Add login page", description="Build a login form.", repo_url="https://example.com/r.git")
    for key, value in overrides.items():
        setattr(task, key, value)
    return task


def test_worker_prompt_includes_summary_and_no_wait_instruction():
    prompt = build_worker_prompt(make_task())
    assert "Add login page" in prompt
    assert "unattended" in prompt.lower()


def test_worker_prompt_includes_controller_feedback_when_present():
    prompt = build_worker_prompt(make_task(last_controller_feedback="Missing tests."))
    assert "Missing tests." in prompt


def test_controller_prompt_asks_for_strict_verdict_marker():
    prompt = build_controller_prompt(make_task())
    assert "VERDICT: PASS" in prompt
    assert "VERDICT: FAIL" in prompt


def test_parse_verdict_pass():
    verdict = parse_verdict("Looking good.\nVERDICT: PASS")
    assert verdict.passed is True


def test_parse_verdict_fail_with_reason():
    verdict = parse_verdict("Some notes.\nVERDICT: FAIL: missing error handling")
    assert verdict.passed is False
    assert verdict.reason == "missing error handling"


def test_parse_verdict_defaults_to_fail_when_unparseable():
    verdict = parse_verdict("The agent forgot to print a verdict line.")
    assert verdict.passed is False
    assert verdict.reason


def test_parse_verdict_uses_last_verdict_line():
    output = "VERDICT: FAIL: draft thought\nMore analysis...\nVERDICT: PASS"
    verdict = parse_verdict(output)
    assert verdict.passed is True
