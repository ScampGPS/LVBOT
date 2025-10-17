"""Individual court recovery strategy."""

from __future__ import annotations

from datetime import datetime

from tracking import t

from automation.browser.recovery.strategies.base import RecoveryContext, RecoveryStrategyExecutor
from automation.browser.recovery.types import RecoveryAttempt, RecoveryResult, RecoveryStrategy


class IndividualCourtRecovery(RecoveryStrategyExecutor):
    strategy = RecoveryStrategy.INDIVIDUAL_COURT

    async def execute(self, context: RecoveryContext) -> RecoveryResult:
        t('automation.browser.recovery.strategies.individual_court.IndividualCourtRecovery.execute')
        service = context.service
        browser_pool = service.browser_pool
        logger = service.logger

        failed_courts = context.failed_courts or browser_pool.courts
        court_number = failed_courts[0]

        start_time = datetime.now()
        attempt = RecoveryAttempt(
            strategy=self.strategy,
            timestamp=start_time,
            courts_affected=[court_number],
            success=False,
        )

        try:
            logger.info("🔧 Recovering individual court: %s", court_number)

            if court_number in browser_pool.pages:
                try:
                    await browser_pool.pages[court_number].close()
                except Exception as exc:  # pragma: no cover - best effort
                    logger.debug("Error closing page for court %s: %s", court_number, exc)
                browser_pool.pages.pop(court_number, None)

            if court_number in browser_pool.contexts:
                try:
                    await browser_pool.contexts[court_number].close()
                except Exception as exc:  # pragma: no cover - best effort
                    logger.debug("Error closing context for court %s: %s", court_number, exc)
                browser_pool.contexts.pop(court_number, None)

            success = await browser_pool._create_and_navigate_court_page_with_retry(court_number)

            attempt.success = success
            attempt.duration_seconds = (datetime.now() - start_time).total_seconds()

            if success:
                message = f"Successfully recovered court {court_number}"
                return RecoveryResult(
                    success=True,
                    strategy_used=self.strategy,
                    courts_recovered=[court_number],
                    courts_failed=[],
                    message=message,
                    attempts=[attempt],
                )

            message = f"Failed to recover court {court_number}"
            return RecoveryResult(
                success=False,
                strategy_used=self.strategy,
                courts_recovered=[],
                courts_failed=[court_number],
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
                courts_failed=[court_number],
                message=f"Exception during court {court_number} recovery",
                error_details=str(exc),
                attempts=[attempt],
            )
