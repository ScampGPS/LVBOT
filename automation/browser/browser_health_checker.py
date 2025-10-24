"""
Browser Health Checker Module
============================

PURPOSE: Monitor and validate browser pool health before critical operations
PATTERN: Proactive health monitoring to prevent booking failures
SCOPE: AsyncBrowserPool health validation

This module provides comprehensive health checks for the browser pool to
ensure bookings have the best chance of success by detecting issues early.
"""

from tracking import t

import logging
from typing import Dict, Optional
from datetime import datetime
from automation.browser.health.collectors import (
    collect_court_signals,
    collect_pool_signals,
)
from automation.browser.health.evaluators import (
    build_court_health_status,
    evaluate_court_signals,
    evaluate_pool_health,
    summarise_courts,
)
from automation.browser.health.runner import HealthCheckRunner
from automation.browser.health.types import (
    CourtHealthStatus,
    HealthCheckResult,
    HealthStatus,
)

logger = logging.getLogger(__name__)


class BrowserHealthChecker:
    """
    Health checker for browser pool and individual court browsers

    Performs various health checks to ensure browsers are ready for bookings:
    - Page connectivity and responsiveness
    - JavaScript execution capability
    - Network connectivity to booking site
    - DOM query functionality
    - Resource availability
    """

    def __init__(self, browser_pool):
        """
        Initialize health checker with browser pool reference

        Args:
            browser_pool: AsyncBrowserPool instance to monitor
        """
        t("automation.browser.browser_health_checker.BrowserHealthChecker.__init__")
        self.browser_pool = browser_pool
        self.last_full_check: Optional[datetime] = None
        self.court_health_cache: Dict[int, CourtHealthStatus] = {}
        self._runner = HealthCheckRunner(logger=logger)

    async def perform_pre_booking_health_check(self) -> HealthCheckResult:
        """
        Main health check before attempting bookings

        Performs comprehensive health validation of the browser pool
        to ensure maximum chance of booking success.

        Returns:
            HealthCheckResult with overall pool health status
        """
        t(
            "automation.browser.browser_health_checker.BrowserHealthChecker.perform_pre_booking_health_check"
        )
        logger.info("🏥 Starting pre-booking health check...")

        try:
            available_courts = self.browser_pool.get_available_courts()
            court_checks = self._runner.build_court_checks(
                available_courts, self.check_court_health
            )
            result = await self._runner.run(self.check_pool_health, court_checks)
            if result.status != HealthStatus.FAILED:
                self.last_full_check = datetime.now()
            return result

        except Exception as e:
            logger.error(f"Pre-booking health check failed: {e}")
            return HealthCheckResult(
                status=HealthStatus.FAILED,
                message=f"Health check error: {str(e)}",
                timestamp=datetime.now(),
            )

    async def check_pool_health(self) -> HealthCheckResult:
        """
        Check overall browser pool status

        Validates:
        - Pool initialization state
        - Browser instance availability
        - Critical operation status

        Returns:
            HealthCheckResult for the overall pool
        """
        t(
            "automation.browser.browser_health_checker.BrowserHealthChecker.check_pool_health"
        )
        try:
            signals = await collect_pool_signals(self.browser_pool)
            return evaluate_pool_health(signals)
        except Exception as e:
            logger.error(f"Pool health check error: {e}")
            return HealthCheckResult(
                status=HealthStatus.FAILED,
                message=f"Pool health check failed: {str(e)}",
                timestamp=datetime.now(),
            )

    async def check_court_health(self, court_number: int) -> CourtHealthStatus:
        """
        Check health of a specific court browser

        Performs multiple checks:
        - Page connectivity
        - JavaScript execution
        - Network access to booking site
        - DOM query capability

        Args:
            court_number: Court number to check (1, 2, or 3)

        Returns:
            CourtHealthStatus with detailed health information
        """
        t(
            "automation.browser.browser_health_checker.BrowserHealthChecker.check_court_health"
        )
        try:
            start_time = datetime.now()
            async with self.browser_pool.lock:
                page = self.browser_pool.pages.get(court_number)
                if not page:
                    return CourtHealthStatus(
                        court_number=court_number,
                        status=HealthStatus.FAILED,
                        last_check=datetime.now(),
                        error_message="Page not found in pool",
                    )

            signals = await collect_court_signals(
                page, logger=logger, court_number=court_number
            )
            response_time_ms = int((datetime.now() - start_time).total_seconds() * 1000)
            evaluation = evaluate_court_signals(
                court_number, signals, response_time_ms=response_time_ms
            )
            result = build_court_health_status(
                court_number,
                evaluation,
                signals,
                response_time_ms=response_time_ms,
            )

            self.court_health_cache[court_number] = result
            logger.info(
                "Court %s health: %s (%s/4 checks passed in %sms)",
                court_number,
                result.status.value,
                sum(evaluation.checks_passed.values()),
                response_time_ms,
            )

            return result

        except Exception as e:
            logger.error(f"Court {court_number} health check error: {e}")
            return CourtHealthStatus(
                court_number=court_number,
                status=HealthStatus.FAILED,
                last_check=datetime.now(),
                error_message=str(e),
            )

    def get_court_health_summary(self) -> Dict[int, str]:
        """
        Get summary of all court health statuses

        Returns:
            Dict mapping court number to health status string
        """
        t(
            "automation.browser.browser_health_checker.BrowserHealthChecker.get_court_health_summary"
        )
        return summarise_courts(self.court_health_cache.values())

    def requires_pool_restart(self) -> bool:
        """
        Check if browser pool requires restart based on health

        Returns:
            True if pool should be restarted
        """
        t(
            "automation.browser.browser_health_checker.BrowserHealthChecker.requires_pool_restart"
        )
        # Check if all courts have failed
        if not self.court_health_cache:
            return False

        failed_count = sum(
            1
            for health in self.court_health_cache.values()
            if health.status == HealthStatus.FAILED
        )

        return (
            failed_count == len(self.court_health_cache)
            and len(self.court_health_cache) > 0
        )
