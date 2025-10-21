"""Structured configuration loaders for the Telegram bot runtime."""

from __future__ import annotations
from tracking import t

from dataclasses import dataclass
from typing import Optional

from infrastructure.settings import AppSettings, get_settings


@dataclass(frozen=True)
class TelegramConfig:
    """Telegram-specific settings for the bot runtime."""

    token: str
    production_mode: bool


@dataclass(frozen=True)
class SchedulerConfig:
    """Scheduling parameters controlling queue evaluation."""

    timezone: str
    check_interval_seconds: int
    booking_window_hours: int
    max_retry_attempts: int
    browser_refresh_interval_seconds: int


@dataclass(frozen=True)
class BrowserConfig:
    """Browser pool settings shared across automation components."""

    booking_url: str
    pool_size: int
    low_resource_mode: bool


@dataclass(frozen=True)
class PathsConfig:
    """File-system locations for persisted state."""

    data_directory: str
    queue_file: str
    users_file: str


@dataclass(frozen=True)
class BotAppConfig:
    """Aggregated configuration snapshot for the Telegram bot."""

    telegram: TelegramConfig
    scheduler: SchedulerConfig
    browser: BrowserConfig
    paths: PathsConfig

    # --- Compatibility helpers for legacy callers ---
    @property
    def timezone(self) -> str:
        return self.scheduler.timezone

    @property
    def browser_refresh_interval(self) -> int:
        return self.scheduler.browser_refresh_interval_seconds

    @property
    def booking_window_hours(self) -> int:
        return self.scheduler.booking_window_hours

    @property
    def max_retry_attempts(self) -> int:
        return self.scheduler.max_retry_attempts

    @property
    def check_interval(self) -> int:
        return self.scheduler.check_interval_seconds

    @property
    def booking_url(self) -> str:
        return self.browser.booking_url

    @property
    def browser_pool_size(self) -> int:
        return self.browser.pool_size

    @property
    def low_resource_mode(self) -> bool:
        return self.browser.low_resource_mode


def _build_config_from_settings(settings: AppSettings) -> BotAppConfig:
    """Translate :class:`AppSettings` values into runtime config objects."""
    t('botapp.config._build_config_from_settings')

    telegram = TelegramConfig(
        token=settings.bot_token,
        production_mode=settings.production_mode,
    )

    scheduler = SchedulerConfig(
        timezone=settings.timezone,
        check_interval_seconds=settings.reservation_check_interval,
        booking_window_hours=settings.reservation_booking_window_hours,
        max_retry_attempts=settings.reservation_max_retry_attempts,
        browser_refresh_interval_seconds=settings.browser_refresh_interval,
    )

    browser = BrowserConfig(
        booking_url=settings.booking_url,
        pool_size=settings.browser_pool_size,
        low_resource_mode=settings.low_resource_mode,
    )

    paths = PathsConfig(
        data_directory=settings.data_directory,
        queue_file=settings.queue_file,
        users_file=settings.users_file,
    )

    return BotAppConfig(
        telegram=telegram,
        scheduler=scheduler,
        browser=browser,
        paths=paths,
    )


def load_bot_config(settings: Optional[AppSettings] = None) -> BotAppConfig:
    """Load the Telegram bot configuration from shared application settings."""
    t('botapp.config.load_bot_config')

    if settings is None:
        settings = get_settings()
    return _build_config_from_settings(settings)


__all__ = [
    'BotAppConfig',
    'BrowserConfig',
    'PathsConfig',
    'SchedulerConfig',
    'TelegramConfig',
    'load_bot_config',
]
