from tracking import t
import pytest
from datetime import datetime

from automation.browser.health.runner import HealthCheckRunner
from automation.browser.health.types import CourtHealthStatus, HealthCheckResult, HealthStatus
from tests.helpers import DummyLogger


@pytest.mark.asyncio
async def test_runner_returns_degraded_when_some_courts_fail():
    t('tests.unit.test_browser_health_runner.test_runner_returns_degraded_when_some_courts_fail')
    logger = DummyLogger()
    runner = HealthCheckRunner(logger=logger)

    async def pool_check():
        t('tests.unit.test_browser_health_runner.test_runner_returns_degraded_when_some_courts_fail.pool_check')
        return HealthCheckResult(
            status=HealthStatus.HEALTHY,
            message="ok",
            timestamp=datetime.now(),
            details={"pool": "ok"},
        )

    async def healthy_court():
        t('tests.unit.test_browser_health_runner.test_runner_returns_degraded_when_some_courts_fail.healthy_court')
        return CourtHealthStatus(
            court_number=1,
            status=HealthStatus.HEALTHY,
            last_check=datetime.now(),
        )

    async def failing_court():
        t('tests.unit.test_browser_health_runner.test_runner_returns_degraded_when_some_courts_fail.failing_court')
        return CourtHealthStatus(
            court_number=2,
            status=HealthStatus.FAILED,
            last_check=datetime.now(),
            error_message="boom",
        )

    result = await runner.run(pool_check, {1: healthy_court, 2: failing_court})

    assert result.status == HealthStatus.DEGRADED
    assert result.details["healthy_count"] == 1
    assert result.details["failed_count"] == 1
    assert "courts" in result.details


@pytest.mark.asyncio
async def test_runner_handles_court_exceptions():
    t('tests.unit.test_browser_health_runner.test_runner_handles_court_exceptions')
    logger = DummyLogger()
    runner = HealthCheckRunner(logger=logger)

    async def pool_check():
        t('tests.unit.test_browser_health_runner.test_runner_handles_court_exceptions.pool_check')
        return HealthCheckResult(
            status=HealthStatus.HEALTHY,
            message="ok",
            timestamp=datetime.now(),
        )

    async def raising():
        t('tests.unit.test_browser_health_runner.test_runner_handles_court_exceptions.raising')
        raise RuntimeError("failure")

    result = await runner.run(pool_check, {5: raising})

    assert result.status == HealthStatus.FAILED
    assert result.details["failed_count"] == 1
    # Logger captured the error
    assert any(entry[0] == "error" for entry in logger.messages)
