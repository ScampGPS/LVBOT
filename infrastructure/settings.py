"""Centralized application settings scaffolding.

This module introduces a single place to load runtime configuration values,
laying groundwork for the refactor phases that will remove scattered
``os.getenv`` calls. Existing modules continue to read configuration directly;
they can migrate to :func:`get_settings` gradually without behaviour changes.
"""

from __future__ import annotations
from tracking import t

import os
from dataclasses import dataclass
from functools import lru_cache
from typing import Mapping, Optional

try:  # Optional dependency to support .env files during development.
    from dotenv import load_dotenv
except ImportError:  # pragma: no cover - library is optional.
    load_dotenv = None  # type: ignore

from . import constants as utils_constants


def _to_bool(value: str, default: bool = False) -> bool:
    """Normalize environment strings such as "true"/"1" into booleans."""
    t('infrastructure.settings._to_bool')

    if value is None:
        return default
    return value.strip().lower() in {"1", "true", "yes", "on"}


@dataclass(frozen=True)
class AppSettings:
    """Immutable snapshot of high-level configuration values."""

    bot_token: str
    production_mode: bool
    booking_url: str
    timezone: str
    browser_pool_size: int
    browser_refresh_interval: int
    queue_file: str
    users_file: str
    data_directory: str


def load_settings(env: Optional[Mapping[str, str]] = None) -> AppSettings:
    """Load configuration from the environment and fall back to defaults."""
    t('infrastructure.settings.load_settings')

    if env is None:
        if load_dotenv is not None:
            load_dotenv(override=False)
        env = os.environ

    bot_token = env.get(
        "TELEGRAM_BOT_TOKEN",
        "7768823561:AAHxxvzil7lKsdf64ZuDF3Cch2KYoPJx2AY",
    )

    production_mode = _to_bool(env.get("PRODUCTION_MODE", "false"), default=False)

    booking_url = env.get("BOOKING_URL", utils_constants.BOOKING_URL)
    timezone = env.get("BOT_TIMEZONE", "America/Guatemala")

    browser_pool_size = int(env.get("BROWSER_POOL_SIZE", "3"))
    browser_refresh_interval = int(env.get("BROWSER_REFRESH_INTERVAL", "180"))

    queue_file = env.get("QUEUE_FILE", "data/queue.json")
    users_file = env.get("USERS_FILE", "data/users.json")
    data_directory = env.get("DATA_DIRECTORY", "data")

    return AppSettings(
        bot_token=bot_token,
        production_mode=production_mode,
        booking_url=booking_url,
        timezone=timezone,
        browser_pool_size=browser_pool_size,
        browser_refresh_interval=browser_refresh_interval,
        queue_file=queue_file,
        users_file=users_file,
        data_directory=data_directory,
    )


@lru_cache(maxsize=1)
def get_settings() -> AppSettings:
    """Return a cached :class:`AppSettings` instance."""
    t('infrastructure.settings.get_settings')

    return load_settings()
