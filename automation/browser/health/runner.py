"""Shared runner that orchestrates browser health checks."""

from __future__ import annotations
from tracking import t

import asyncio
from datetime import datetime
from functools import partial
from typing import Awaitable, Callable, Dict, Mapping

from automation.browser.health.evaluators import summarise_courts
from automation.browser.health.types import CourtHealthStatus, HealthCheckResult, HealthStatus


class HealthCheckRunner:
    """Execute pool and per-court health checks using provided strategies."""

    def __init__(self, *, logger, summary_builder: Callable = summarise_courts) -> None:
        t('automation.browser.health.runner.HealthCheckRunner.__init__')
        self._logger = logger
        self._summarise = summary_builder

    async def run(
        self,
        pool_check: Callable[[], Awaitable[HealthCheckResult]],
        court_checks: Mapping[int, Callable[[], Awaitable[CourtHealthStatus]]],
    ) -> HealthCheckResult:
        t('automation.browser.health.runner.HealthCheckRunner.run')
        start_time = datetime.now()

        pool_result = await pool_check()
        if pool_result.status == HealthStatus.FAILED:
            return pool_result

        court_numbers = list(court_checks.keys())
        if not court_numbers:
            return HealthCheckResult(
                status=HealthStatus.FAILED,
                message="No courts available in browser pool",
                timestamp=datetime.now(),
            )

        results = await asyncio.gather(
            *(court_checks[number]() for number in court_numbers),
            return_exceptions=True,
        )

        healthy = 0
        degraded = 0
        failed = 0
        court_statuses: Dict[int, CourtHealthStatus] = {}

        for number, result in zip(court_numbers, results):
            if isinstance(result, Exception):
                self._logger.error("Court %s health check failed: %s", number, result)
                status = CourtHealthStatus(
                    court_number=number,
                    status=HealthStatus.FAILED,
                    last_check=datetime.now(),
                    error_message=str(result),
                )
            else:
                status = result

            court_statuses[number] = status
            if status.status == HealthStatus.HEALTHY:
                healthy += 1
            elif status.status in {HealthStatus.DEGRADED, HealthStatus.CRITICAL}:
                degraded += 1
            else:
                failed += 1

        summary = self._summarise(court_statuses.values())
        elapsed_ms = int((datetime.now() - start_time).total_seconds() * 1000)

        if healthy == len(court_numbers):
            status_enum = HealthStatus.HEALTHY
            message = f"All {healthy} courts are healthy"
        elif healthy > 0:
            status_enum = HealthStatus.DEGRADED
            message = f"{healthy} healthy, {degraded} degraded, {failed} failed"
        elif degraded > 0:
            status_enum = HealthStatus.CRITICAL
            message = f"No healthy courts, {degraded} degraded, {failed} failed"
        else:
            status_enum = HealthStatus.FAILED
            message = f"All {failed} courts have failed"

        details = {
            "pool": pool_result.details or {},
            "courts": summary,
            "healthy_count": healthy,
            "degraded_count": degraded,
            "failed_count": failed,
            "total_courts": len(court_numbers),
            "check_duration_ms": elapsed_ms,
        }

        return HealthCheckResult(
            status=status_enum,
            message=message,
            timestamp=datetime.now(),
            details=details,
        )

    def build_court_checks(
        self,
        available_courts,
        runner: Callable[[int], Awaitable[CourtHealthStatus]],
    ) -> Dict[int, Callable[[], Awaitable[CourtHealthStatus]]]:
        """Helper to bind court numbers to their async runners."""
        t('automation.browser.health.runner.HealthCheckRunner.build_court_checks')

        return {court: partial(runner, court) for court in available_courts}
