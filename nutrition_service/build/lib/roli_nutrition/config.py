"""Settings read from environment variables.

The core never opens files. Entry points (scripts, tests, the MCP server)
load ``roli/.env`` with python-dotenv *before* calling ``Settings.from_env()``,
so by the time this module runs the values are already in the environment.
"""

from __future__ import annotations

import os
from dataclasses import dataclass
from typing import Mapping


class ConfigError(Exception):
    """A required setting is missing or unusable. The message never shows a value."""


@dataclass(frozen=True)
class Settings:
    api_key: str
    cache_ttl_seconds: float = 86400.0
    cache_max_entries: int = 1000

    @classmethod
    def from_env(cls, env: Mapping[str, str] | None = None) -> "Settings":
        """Build settings from ``os.environ`` (or a mapping passed in by tests)."""
        source = os.environ if env is None else env

        api_key = source.get("USDA_FDC_API_KEY", "").strip()
        if not api_key:
            raise ConfigError(
                "USDA_FDC_API_KEY is missing or blank. "
                "Add it to roli/.env or the process environment."
            )

        return cls(
            api_key=api_key,
            cache_ttl_seconds=_positive_number(source, "ROLI_CACHE_TTL_SECONDS", 86400.0, float),
            cache_max_entries=_positive_number(source, "ROLI_CACHE_MAX_ENTRIES", 1000, int),
        )


def _positive_number(source: Mapping[str, str], name: str, default, kind):
    raw = source.get(name)
    if raw is None or raw.strip() == "":
        return default
    try:
        value = kind(raw.strip())
    except ValueError:
        raise ConfigError(f"{name} must be a positive number.") from None
    if value <= 0:
        raise ConfigError(f"{name} must be a positive number.")
    return value
