"""Partial pool recovery strategy."""

from __future__ import annotations

import asyncio
from datetime import datetime

from tracking import t

from automation.browser.recovery.strategies.base import RecoveryContext, RecoveryStrategyExecutor
from automation.browser.recovery.types import RecoveryAttempt, RecoveryResult, RecoveryStrategy


class PartialPoolRecovery(RecoveryStrategyExecutor):
    strategy = RecoveryStrategy.PARTIAL_POOL

    async def execute(self, context: RecoveryContext) -> RecoveryResult:
        t('automation.browser.recovery.strategies.partial_pool.PartialPoolRecovery.execute')
        service = context.service
        browser_pool = service.browser_pool
        logger = service.logger

        court_numbers = context.failed_courts or browser_pool.courts

        start_time = datetime.now()
        attempt = RecoveryAttempt(
            strategy=self.strategy,
            timestamp=start_time,
            courts_affected=list(court_numbers),
            success=False,
        )

        courts_recovered = []
        courts_failed = []

        try:
            logger.info("🔧 Recovering partial pool: courts %s", court_numbers)

            for court_number in court_numbers:
                page = browser_pool.pages.pop(court_number, None)
                if page:
                    try:
                        await page.close()
                    except Exception:  # pragma: no cover - best effort
                        pass

                ctx = browser_pool.contexts.pop(court_number, None)
                if ctx:
                    try:
                        await ctx.close()
                    except Exception:  # pragma: no cover - best effort
                        pass

            tasks = []
            for index, court_number in enumerate(court_numbers):
                delay = index * 1.5
                tasks.append(
                    browser_pool._create_and_navigate_court_page_with_stagger(court_number, delay)
                )

            results = await asyncio.gather(*tasks, return_exceptions=True)

            for court_number, result in zip(court_numbers, results):
                if isinstance(result, Exception):
                    logger.error("Failed to recover court %s: %s", court_number, result)
                    courts_failed.append(court_number)
                else:
                    logger.info("Successfully recovered court %s", court_number)
                    courts_recovered.append(court_number)

            if courts_recovered:
                browser_pool.is_partially_ready = len(courts_recovered) < len(browser_pool.courts)

            attempt.success = bool(courts_recovered)
            attempt.duration_seconds = (datetime.now() - start_time).total_seconds()

            message = f"Recovered {len(courts_recovered)}/{len(court_numbers)} courts"
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
                courts_failed=list(court_numbers),
                message="Exception during partial pool recovery",
                error_details=str(exc),
                attempts=[attempt],
            )
