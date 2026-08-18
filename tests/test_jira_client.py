from unittest.mock import MagicMock, patch

import pytest
import requests

from orchestrator.jira_client import JiraClientError, fetch_issues


def test_fetch_issues_requires_base_url_and_pat():
    with pytest.raises(JiraClientError):
        fetch_issues(base_url="", pat="", jql="project = X")


@patch("orchestrator.jira_client.requests.get")
def test_fetch_issues_maps_fields_to_jira_issue(mock_get):
    mock_response = MagicMock()
    mock_response.json.return_value = {
        "issues": [
            {
                "key": "PROJ-1",
                "fields": {"summary": "Fix login bug", "description": "Steps to reproduce..."},
            },
            {
                "key": "PROJ-2",
                "fields": {"summary": "Add dark mode", "description": None},
            },
        ]
    }
    mock_response.raise_for_status.return_value = None
    mock_get.return_value = mock_response

    issues = fetch_issues(base_url="https://jira.example.com", pat="secret-pat", jql="project = PROJ")

    assert [i.key for i in issues] == ["PROJ-1", "PROJ-2"]
    assert issues[0].summary == "Fix login bug"
    assert issues[1].description == ""

    headers = mock_get.call_args.kwargs["headers"]
    assert headers["Authorization"] == "Bearer secret-pat"


@patch("orchestrator.jira_client.requests.get")
def test_fetch_issues_wraps_request_errors(mock_get):
    mock_get.side_effect = requests.ConnectionError("boom")
    with pytest.raises(JiraClientError):
        fetch_issues(base_url="https://jira.example.com", pat="pat", jql="project = PROJ")
