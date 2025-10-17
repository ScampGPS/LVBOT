"""Emergency fallback recovery strategy."""

from __future__ import annotations

from datetime import datetime

from tracking import t

from automation.browser.recovery.strategies.base import RecoveryContext, RecoveryStrategyExecutor
from automation.browser.recovery.types import RecoveryAttempt, RecoveryResult, RecoveryStrategy


class EmergencyFallbackRecovery(RecoveryStrategyExecutor):
    strategy = RecoveryStrategy.EMERGENCY_FALLBACK

    async def execute(self, context: RecoveryContext) -> RecoveryResult:
        t('automation.browser.recovery.strategies.emergency_fallback.EmergencyFallbackRecovery.execute')
        service = context.service
        logger = service.logger
        browser_pool = service.browser_pool

        start_time = datetime.now()
        attempt = RecoveryAttempt(
            strategy=self.strategy,
            timestamp=start_time,
            courts_affected=[99],
            success=False,
        )

        try:
            logger.critical("🚨 Activating emergency fallback browser")

            from playwright.async_api import async_playwright

            if service.emergency_browser:
                try:
                    await service.emergency_browser.close()
                except Exception:  # pragma: no cover - best effort
                    pass

            emergency_playwright = await async_playwright().start()
            service.emergency_browser = await emergency_playwright.chromium.launch(
                headless=False,
                args=['--no-sandbox', '--disable-dev-shm-usage'],
            )

            context_obj = await service.emergency_browser.new_context(
                viewport={'width': 1920, 'height': 1080},
                locale='es-GT',
                timezone_id='America/Guatemala',
            )
            page = await context_obj.new_page()
            await page.goto("https://clublavilla.as.me", wait_until='domcontentloaded', timeout=30000)

            browser_pool.pages[99] = page
            browser_pool.contexts[99] = context_obj

            attempt.success = True
            attempt.duration_seconds = (datetime.now() - start_time).total_seconds()

            logger.info("✅ Emergency fallback browser activated")
            return RecoveryResult(
                success=True,
                strategy_used=self.strategy,
                courts_recovered=[99],
                courts_failed=[],
                message="Emergency browser activated - limited functionality available",
                attempts=[attempt],
            )

        except Exception as exc:  # pragma: no cover - defensive guard
            attempt.error_message = str(exc)
            attempt.duration_seconds = (datetime.now() - start_time).total_seconds()
            return RecoveryResult(
                success=False,
                strategy_used=self.strategy,
                courts_recovered=[],
                courts_failed=[99],
                message="Failed to activate emergency fallback",
                error_details=str(exc),
                attempts=[attempt],
            )
