"""Fetches issues from Jira via REST API using a Personal Access Token, and maps
them onto the Task fields this app needs. See REQUIREMENTS.md section 4.2.
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import List

import requests


class JiraClientError(RuntimeError):
    pass


@dataclass
class JiraIssue:
    key: str
    summary: str
    description: str


def fetch_issues(base_url: str, pat: str, jql: str, max_results: int = 50) -> List[JiraIssue]:
    """Fetches issues matching `jql` from a Jira Server/Data Center instance
    using Bearer PAT auth against the v2 REST API."""
    if not base_url or not pat:
        raise JiraClientError("Jira base URL and PAT are required.")

    url = f"{base_url.rstrip('/')}/rest/api/2/search"
    headers = {"Authorization": f"Bearer {pat}", "Accept": "application/json"}
    params = {
        "jql": jql,
        "maxResults": max_results,
        "fields": "summary,description",
    }

    try:
        response = requests.get(url, headers=headers, params=params, timeout=30)
        response.raise_for_status()
    except requests.RequestException as exc:
        raise JiraClientError(f"Jira request failed: {exc}") from exc

    payload = response.json()
    issues = []
    for raw in payload.get("issues", []):
        fields = raw.get("fields", {})
        issues.append(
            JiraIssue(
                key=raw.get("key", ""),
                summary=fields.get("summary") or "",
                description=fields.get("description") or "",
            )
        )
    return issues
