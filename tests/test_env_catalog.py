from orchestrator.env_catalog import KNOWN_ENV_VARS, describe, known_var_names


def test_known_env_vars_have_names_and_descriptions():
    assert len(KNOWN_ENV_VARS) > 0
    for var in KNOWN_ENV_VARS:
        assert var.name
        assert var.description


def test_describe_returns_known_description():
    assert "X-Api-Key" in describe("ANTHROPIC_API_KEY")


def test_describe_falls_back_for_custom_var():
    assert describe("SOME_CUSTOM_VAR") == "Custom environment variable."


def test_known_var_names_includes_jira_vars():
    names = known_var_names()
    assert "JIRA_BASE_URL" in names
    assert "JIRA_PAT" in names
