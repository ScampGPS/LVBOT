"""Signal evaluation helpers for browser health checks."""

from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime
from typing import Dict, Iterable

from tracking import t

from automation.browser.health.collectors import CourtSignals, PoolSignals
from automation.browser.health.types import CourtHealthStatus, HealthCheckResult, HealthStatus


@dataclass
class CourtEvaluation:
    status: HealthStatus
    checks_passed: Dict[str, bool]


def evaluate_pool_health(signals: PoolSignals) -> HealthCheckResult:
    """Convert pool signals into a health result."""

    t('automation.browser.health.evaluators.evaluate_pool_health')

    if not signals.ready:
        return HealthCheckResult(
            status=HealthStatus.FAILED,
            message="Browser pool is not ready",
            timestamp=datetime.now(),
        )

    if not signals.browser_connected:
        return HealthCheckResult(
            status=HealthStatus.FAILED,
            message="Browser instance is not connected",
            timestamp=datetime.now(),
        )

    if signals.critical_operation:
        return HealthCheckResult(
            status=HealthStatus.DEGRADED,
            message="Critical operation in progress - pool is busy",
            timestamp=datetime.now(),
            details={"critical_operation": True},
        )

    if signals.partially_ready:
        return HealthCheckResult(
            status=HealthStatus.DEGRADED,
            message=f"Pool partially initialized: {signals.available_courts}/{signals.requested_courts} courts",
            timestamp=datetime.now(),
            details={
                "available_courts": signals.available_courts,
                "requested_courts": signals.requested_courts,
                "partial_ready": True,
            },
        )

    return HealthCheckResult(
        status=HealthStatus.HEALTHY,
        message="Browser pool is healthy",
        timestamp=datetime.now(),
    )


def evaluate_court_signals(court_number: int, signals: CourtSignals, *, response_time_ms: int) -> CourtEvaluation:
    """Derive court health status from collected signals."""

    t('automation.browser.health.evaluators.evaluate_court_signals')

    checks = {
        "page_access": signals.url_accessible,
        "javascript": signals.javascript_works,
        "network": signals.network_ok,
        "dom_query": signals.dom_queryable,
    }

    passed = sum(checks.values())
    if passed == 4:
        status = HealthStatus.HEALTHY
    elif passed >= 3:
        status = HealthStatus.DEGRADED
    elif passed >= 1:
        status = HealthStatus.CRITICAL
    else:
        status = HealthStatus.FAILED

    return CourtEvaluation(status=status, checks_passed=checks)


def build_court_health_status(
    court_number: int,
    evaluation: CourtEvaluation,
    signals: CourtSignals,
    *,
    response_time_ms: int,
) -> CourtHealthStatus:
    """Construct a ``CourtHealthStatus`` from evaluation results."""

    t('automation.browser.health.evaluators.build_court_health_status')

    return CourtHealthStatus(
        court_number=court_number,
        status=evaluation.status,
        last_check=datetime.now(),
        page_url=signals.current_url,
        error_message=signals.error,
        response_time_ms=response_time_ms,
        checks_passed=evaluation.checks_passed,
    )


def summarise_courts(court_statuses: Iterable[CourtHealthStatus]) -> Dict[str, str]:
    """Summarise court statuses for telemetry."""

    t('automation.browser.health.evaluators.summarise_courts')
    return {
        f"court_{status.court_number}": status.status.value for status in court_statuses
    }
