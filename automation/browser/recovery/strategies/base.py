"""Base recovery strategy interface."""

from __future__ import annotations

from abc import ABC, abstractmethod
from typing import TYPE_CHECKING, Optional

from tracking import t

from automation.browser.recovery.types import RecoveryResult, RecoveryStrategy
from automation.browser.browser_pool_accessor import (
    browser_pool_accessor,
    proxy_attribute,
)

if TYPE_CHECKING:  # pragma: no cover - type helper
    from automation.browser.browser_pool_recovery import BrowserPoolRecoveryService


class RecoveryContext:
    """Execution context shared with recovery strategies."""

    browser_pool = browser_pool_accessor("service", read_only=True)
    logger = proxy_attribute("service", "logger", read_only=True)

    def __init__(self, service: "BrowserPoolRecoveryService", failed_courts: Optional[list], error_context: Optional[str]):
        t('automation.browser.recovery.strategies.base.RecoveryContext.__init__')
        self.service = service
        self.failed_courts = failed_courts
        self.error_context = error_context


class RecoveryStrategyExecutor(ABC):
    """Interface for executing a recovery strategy."""

    strategy: RecoveryStrategy

    def __init__(self) -> None:
        t('automation.browser.recovery.strategies.base.RecoveryStrategyExecutor.__init__')

    @abstractmethod
    async def execute(self, context: RecoveryContext) -> RecoveryResult:
        """Run the recovery strategy and return a structured result."""

    def __repr__(self) -> str:  # pragma: no cover - debug helper
        return f"{self.__class__.__name__}(strategy={self.strategy.value})"
