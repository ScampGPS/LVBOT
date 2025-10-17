"""Full browser pool restart strategy."""

from __future__ import annotations

import asyncio
from datetime import datetime

from tracking import t

from automation.browser.recovery.strategies.base import RecoveryContext, RecoveryStrategyExecutor
from automation.browser.recovery.types import RecoveryAttempt, RecoveryResult, RecoveryStrategy


class FullRestartRecovery(RecoveryStrategyExecutor):
    strategy = RecoveryStrategy.FULL_RESTART

    async def execute(self, context: RecoveryContext) -> RecoveryResult:
        t('automation.browser.recovery.strategies.full_restart.FullRestartRecovery.execute')
        service = context.service
        browser_pool = service.browser_pool
        logger = service.logger

        start_time = datetime.now()
        attempt = RecoveryAttempt(
            strategy=self.strategy,
            timestamp=start_time,
            courts_affected=list(browser_pool.courts),
            success=False,
        )

        try:
            logger.warning("🔄 Performing full browser pool restart")

            original_courts = browser_pool.courts.copy()

            await browser_pool.stop()

            browser_pool.pages.clear()
            browser_pool.contexts.clear()
            browser_pool.browser = None
            browser_pool.playwright = None

            await asyncio.sleep(2)

            browser_pool.courts = original_courts
            await browser_pool.start()

            courts_recovered = browser_pool.get_available_courts()
            courts_failed = [court for court in original_courts if court not in courts_recovered]

            attempt.success = bool(courts_recovered)
            attempt.duration_seconds = (datetime.now() - start_time).total_seconds()

            message = (
                f"Full restart completed: {len(courts_recovered)}/{len(original_courts)} courts ready"
            )
            return RecoveryResult(
                success=bool(courts_recovered),
                strategy_used=self.strategy,
                courts_recovered=courts_recovered,
                courts_failed=courts_failed,
                message=message,
                attempts=[attempt],
            )

        except Exception as exc:  # pragma: no cover - defensive guard
            attempt.error_message = str(exc)
            attempt.duration_seconds = (datetime.now() - start_time).total_seconds()
            return RecoveryResult(
                success=False,
                strategy_used=self.strategy,
                courts_recovered=[],
                courts_failed=list(browser_pool.courts),
                message="Exception during full pool restart",
                error_details=str(exc),
                attempts=[attempt],
            )
