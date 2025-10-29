"""Centralized application settings scaffolding.

This module introduces a single place to load runtime configuration values,
laying groundwork for the refactor phases that will remove scattered
``os.getenv`` calls. Existing modules continue to read configuration directly;
they can migrate to :func:`get_settings` gradually without behaviour changes.
"""

from __future__ import annotations
from tracking import t

import json
import os
from dataclasses import dataclass
from functools import lru_cache
from pathlib import Path
from typing import Mapping, Optional

try:  # Optional dependency to support .env files during development.
    from dotenv import load_dotenv
except ImportError:  # pragma: no cover - library is optional.
    load_dotenv = None  # type: ignore

from . import constants as utils_constants

TEST_MODE_FILE = Path(__file__).resolve().parents[1] / 'data' / 'test_mode.json'


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
    low_resource_mode: bool
    reservation_check_interval: int
    reservation_max_retry_attempts: int
    reservation_booking_window_hours: int
    queue_file: str
    users_file: str
    data_directory: str
    save_availability_screenshots: bool


@dataclass(frozen=True)
class TestModeConfig:
    """Configuration toggles that control test-mode behaviour."""

    enabled: bool
    allow_within_48h: bool
    trigger_delay_minutes: float
    retain_failed_reservations: bool


# Prevent pytest from attempting to collect the dataclass as a test case.
TestModeConfig.__test__ = False


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
    low_resource_mode = _to_bool(env.get("BROWSER_LOW_RESOURCE_MODE", "false"))

    reservation_check_interval = int(env.get("RESERVATION_CHECK_INTERVAL", "30"))
    reservation_max_retry_attempts = int(env.get("RESERVATION_MAX_RETRY_ATTEMPTS", "3"))
    reservation_booking_window_hours = int(env.get("RESERVATION_BOOKING_WINDOW_HOURS", "48"))

    queue_file = env.get("QUEUE_FILE", "data/queue.json")
    users_file = env.get("USERS_FILE", "data/users.json")
    data_directory = env.get("DATA_DIRECTORY", "data")
    save_availability_screenshots = _to_bool(
        env.get("SAVE_AVAILABILITY_SCREENSHOTS", "false")
    )

    return AppSettings(
        bot_token=bot_token,
        production_mode=production_mode,
        booking_url=booking_url,
        timezone=timezone,
        browser_pool_size=browser_pool_size,
        browser_refresh_interval=browser_refresh_interval,
        low_resource_mode=low_resource_mode,
        reservation_check_interval=reservation_check_interval,
        reservation_max_retry_attempts=reservation_max_retry_attempts,
        reservation_booking_window_hours=reservation_booking_window_hours,
        queue_file=queue_file,
        users_file=users_file,
        data_directory=data_directory,
        save_availability_screenshots=save_availability_screenshots,
    )


@lru_cache(maxsize=1)
def get_settings() -> AppSettings:
    """Return a cached :class:`AppSettings` instance."""
    t('infrastructure.settings.get_settings')

    return load_settings()


def load_test_mode(env: Optional[Mapping[str, str]] = None) -> TestModeConfig:
    """Load test-mode configuration with sensible defaults."""

    t('infrastructure.settings.load_test_mode')

    if env is None:
        if load_dotenv is not None:
            load_dotenv(override=False)
        env = os.environ

    enabled = _to_bool(env.get('TEST_MODE_ENABLED', 'false'))
    allow_within_48h = _to_bool(env.get('TEST_MODE_ALLOW_WITHIN_48H', 'false'))

    try:
        trigger_delay_minutes = float(env.get('TEST_MODE_TRIGGER_DELAY_MINUTES', '1'))
    except (TypeError, ValueError):
        trigger_delay_minutes = 0.25

    retain_failed = _to_bool(
        env.get('TEST_MODE_RETAIN_FAILED', 'true' if enabled else 'false'),
        default=enabled,
    )

    config_data = {
        'enabled': enabled,
        'allow_within_48h': allow_within_48h,
        'trigger_delay_minutes': trigger_delay_minutes,
        'retain_failed_reservations': retain_failed,
    }

    if TEST_MODE_FILE.exists():
        try:
            file_values = json.loads(TEST_MODE_FILE.read_text(encoding='utf-8'))
            if isinstance(file_values, dict):
                config_data.update({
                    'enabled': bool(file_values.get('enabled', config_data['enabled'])),
                    'allow_within_48h': bool(file_values.get('allow_within_48h', config_data['allow_within_48h'])),
                    'trigger_delay_minutes': float(file_values.get('trigger_delay_minutes', config_data['trigger_delay_minutes'])),
                    'retain_failed_reservations': bool(file_values.get('retain_failed_reservations', config_data['retain_failed_reservations'])),
                })
        except (ValueError, OSError):
            pass

    return TestModeConfig(
        enabled=config_data['enabled'],
        allow_within_48h=config_data['allow_within_48h'],
        trigger_delay_minutes=config_data['trigger_delay_minutes'],
        retain_failed_reservations=config_data['retain_failed_reservations'],
    )


_TEST_MODE_CONFIG: Optional[TestModeConfig] = None


def get_test_mode(refresh: bool = False) -> TestModeConfig:
    """Return the cached :class:`TestModeConfig` snapshot."""

    t('infrastructure.settings.get_test_mode')

    global _TEST_MODE_CONFIG
    if _TEST_MODE_CONFIG is None or refresh:
        _TEST_MODE_CONFIG = load_test_mode()
    return _TEST_MODE_CONFIG


def set_test_mode(config: TestModeConfig) -> TestModeConfig:
    """Explicitly override the in-process test mode configuration."""

    t('infrastructure.settings.set_test_mode')

    global _TEST_MODE_CONFIG
    _TEST_MODE_CONFIG = config
    _write_test_mode_file(config)
    return _TEST_MODE_CONFIG


def update_test_mode(**kwargs: object) -> TestModeConfig:
    """Update selected fields on the cached test mode configuration."""

    t('infrastructure.settings.update_test_mode')

    current = get_test_mode()
    new_config = TestModeConfig(
        enabled=kwargs.get('enabled', current.enabled),
        allow_within_48h=kwargs.get('allow_within_48h', current.allow_within_48h),
        trigger_delay_minutes=kwargs.get('trigger_delay_minutes', current.trigger_delay_minutes),
        retain_failed_reservations=kwargs.get('retain_failed_reservations', current.retain_failed_reservations),
    )
    return set_test_mode(new_config)


def _write_test_mode_file(config: TestModeConfig) -> None:
    try:
        TEST_MODE_FILE.parent.mkdir(parents=True, exist_ok=True)
        TEST_MODE_FILE.write_text(
            json.dumps(
                {
                    'enabled': config.enabled,
                    'allow_within_48h': config.allow_within_48h,
                    'trigger_delay_minutes': config.trigger_delay_minutes,
                    'retain_failed_reservations': config.retain_failed_reservations,
                },
                indent=2,
            ),
            encoding='utf-8',
        )
    except OSError:
        pass
