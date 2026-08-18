"""Read/write the .env file and merge it into the subprocess environment."""

from __future__ import annotations

import os
from pathlib import Path
from typing import Dict

from dotenv import dotenv_values

DEFAULT_ENV_PATH = Path(__file__).resolve().parent.parent / ".env"


def read_env(path: Path = DEFAULT_ENV_PATH) -> Dict[str, str]:
    if not path.exists():
        return {}
    values = dotenv_values(path)
    return {k: v for k, v in values.items() if v is not None}


def write_env(values: Dict[str, str], path: Path = DEFAULT_ENV_PATH) -> None:
    lines = [f"{key}={value}" for key, value in sorted(values.items())]
    path.write_text("\n".join(lines) + ("\n" if lines else ""), encoding="utf-8")


def subprocess_env(path: Path = DEFAULT_ENV_PATH) -> Dict[str, str]:
    """Host environment merged with (and overridden by) .env contents."""
    merged = os.environ.copy()
    merged.update(read_env(path))
    return merged
