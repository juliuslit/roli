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
    # spec v2.3 (2026-11-05): saved answers on disk, the hourly allowance and refresh by release. All proposals from SPEC_3_mvp.md 12.5 are settings.
    store_dir: str | None = None                 # ROLI_USDA_STORE_DIR; None = no disk store (the in-memory cache alone, as before)
    stale_months: int = 7                        # ROLI_USDA_STALE_MONTHS: Foundation/Survey answers older than this are refreshed even if detection fails
    reserve_requests: int = 200                  # ROLI_USDA_RESERVE_REQUESTS: callers pause when the remaining hourly allowance is at or under this
    halt_seconds: float = 3600.0                 # ROLI_USDA_HALT_SECONDS: after a 429, no request is sent for this long (0 disables)

    @property
    def stale_days(self) -> int:
        return int(round(self.stale_months * 30.44))

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

        store_dir = (source.get("ROLI_USDA_STORE_DIR") or "").strip() or None
        return cls(
            api_key=api_key,
            cache_ttl_seconds=_positive_number(source, "ROLI_CACHE_TTL_SECONDS", 86400.0, float),
            cache_max_entries=_positive_number(source, "ROLI_CACHE_MAX_ENTRIES", 1000, int),
            store_dir=store_dir,
            stale_months=_positive_number(source, "ROLI_USDA_STALE_MONTHS", 7, int),
            reserve_requests=_non_negative_number(source, "ROLI_USDA_RESERVE_REQUESTS", 200, int),
            halt_seconds=_non_negative_number(source, "ROLI_USDA_HALT_SECONDS", 3600.0, float),
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


def _non_negative_number(source: Mapping[str, str], name: str, default, kind):
    raw = source.get(name)
    if raw is None or raw.strip() == "":
        return default
    try:
        value = kind(raw.strip())
    except ValueError:
        raise ConfigError(f"{name} must be a number of 0 or more.") from None
    if value < 0:
        raise ConfigError(f"{name} must be a number of 0 or more.")
    return value
