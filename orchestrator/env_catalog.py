"""Known Claude Code (and this app's own) environment variables, with tooltip text.

Sourced from https://code.claude.com/docs/en/env-vars (fetched 2026-08-18); listing
the ones most relevant to an unattended headless-orchestration use case rather than
the full set (there are 40+ documented vars covering Bedrock/Vertex/Foundry auth,
custom model aliases, etc. that don't apply here).
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import List


@dataclass(frozen=True)
class EnvVarInfo:
    name: str
    description: str
    default_value: str = ""


KNOWN_ENV_VARS: List[EnvVarInfo] = [
    EnvVarInfo("ANTHROPIC_API_KEY", "API key sent as the X-Api-Key header for claude CLI calls. Leave blank to use the host's existing `claude login` session."),
    EnvVarInfo("ANTHROPIC_MODEL", "Overrides the model claude CLI uses for Worker/Controller runs."),
    EnvVarInfo("ANTHROPIC_BASE_URL", "Overrides the API endpoint (proxy/gateway routing)."),
    EnvVarInfo("API_TIMEOUT_MS", "Timeout for individual API requests, in milliseconds.", "600000"),
    EnvVarInfo("BASH_DEFAULT_TIMEOUT_MS", "Default timeout for bash commands claude runs inside a task.", "120000"),
    EnvVarInfo("BASH_MAX_TIMEOUT_MS", "Maximum timeout claude may request for a single bash command.", "600000"),
    EnvVarInfo("BASH_MAX_OUTPUT_LENGTH", "Max characters of bash output claude reads back.", "30000"),
    EnvVarInfo("CLAUDE_CODE_AUTO_COMPACT_WINDOW", "Context window token threshold before Claude Code auto-compacts (100000-1000000)."),
    EnvVarInfo("MAX_THINKING_TOKENS", "Extended-thinking token budget; 0 disables it."),
    EnvVarInfo("DISABLE_TELEMETRY", "Any non-empty value disables telemetry reporting."),
    EnvVarInfo("DISABLE_AUTOUPDATER", "Any non-empty value disables the CLI auto-updater — recommended for unattended runs."),
    EnvVarInfo("JIRA_BASE_URL", "Base URL of the Jira instance used by this app's Jira import feature."),
    EnvVarInfo("JIRA_PAT", "Personal Access Token used as a Bearer credential for Jira REST calls."),
]


def known_var_names() -> List[str]:
    return [v.name for v in KNOWN_ENV_VARS]


def describe(name: str) -> str:
    for v in KNOWN_ENV_VARS:
        if v.name == name:
            return v.description
    return "Custom environment variable."
