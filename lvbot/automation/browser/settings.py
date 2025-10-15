"""Browser settings dataclass and helpers."""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Iterable, List, Optional

from lvbot.infrastructure.settings import get_settings
from lvbot.infrastructure.constants import AVAILABLE_COURT_NUMBERS, BrowserTimeouts


@dataclass(frozen=True)
class BrowserSettings:
    """Configuration values controlling the shared browser pool."""

    courts: List[int] = field(default_factory=lambda: list(AVAILABLE_COURT_NUMBERS))
    headless: bool = False
    warmup_delay: float = 1.5
    navigation_timeout_ms: int = BrowserTimeouts.NORMAL_NAVIGATION
    partial_init_allowed: bool = True

    def with_courts(self, courts: Iterable[int]) -> "BrowserSettings":
        """Return a copy with a different list of courts."""

        return BrowserSettings(
            courts=list(courts),
            headless=self.headless,
            warmup_delay=self.warmup_delay,
            navigation_timeout_ms=self.navigation_timeout_ms,
            partial_init_allowed=self.partial_init_allowed,
        )


def load_browser_settings() -> BrowserSettings:
    """Derive :class:`BrowserSettings` from the global application settings."""

    app_settings = get_settings()

    return BrowserSettings(
        headless=app_settings.production_mode,
        courts=list(AVAILABLE_COURT_NUMBERS),
        warmup_delay=1.5,
        navigation_timeout_ms=BrowserTimeouts.NORMAL_NAVIGATION,
        partial_init_allowed=True,
    )
