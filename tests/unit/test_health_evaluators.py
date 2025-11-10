from tracking import t
from datetime import datetime

from automation.browser.health.evaluators import (
    build_court_health_status,
    evaluate_court_signals,
    evaluate_pool_health,
    summarise_courts,
)
from automation.browser.health.collectors import CourtSignals, PoolSignals
from automation.browser.health.types import CourtHealthStatus, HealthStatus


def test_evaluate_pool_health_handles_partial_ready():
    t('tests.unit.test_health_evaluators.test_evaluate_pool_health_handles_partial_ready')
    signals = PoolSignals(
        ready=True,
        browser_connected=True,
        critical_operation=False,
        partially_ready=True,
        available_courts=2,
        requested_courts=3,
    )

    result = evaluate_pool_health(signals)

    assert result.status == HealthStatus.DEGRADED
    assert result.details["partial_ready"] is True


def test_build_court_health_status_reports_success():
    t('tests.unit.test_health_evaluators.test_build_court_health_status_reports_success')
    signals = CourtSignals(
        url_accessible=True,
        javascript_works=True,
        network_ok=True,
        dom_queryable=False,
        current_url="https://clublavilla.as.me",
        error=None,
    )
    evaluation = evaluate_court_signals(1, signals, response_time_ms=120)

    status = build_court_health_status(
        1,
        evaluation,
        signals,
        response_time_ms=120,
    )

    assert status.court_number == 1
    assert status.status in {HealthStatus.HEALTHY, HealthStatus.DEGRADED}
    assert status.page_url == "https://clublavilla.as.me"


def test_summarise_courts_returns_status_map():
    t('tests.unit.test_health_evaluators.test_summarise_courts_returns_status_map')
    now = datetime.now()
    statuses = [
        CourtHealthStatus(court_number=1, status=HealthStatus.HEALTHY, last_check=now),
        CourtHealthStatus(court_number=2, status=HealthStatus.FAILED, last_check=now),
    ]

    summary = summarise_courts(statuses)

    assert summary == {"court_1": "healthy", "court_2": "failed"}
