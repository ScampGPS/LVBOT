from tracking import t
from reservations.queue.scheduler.metrics import SchedulerStats


def test_scheduler_stats_records_success_and_failure():
    t('tests.unit.test_scheduler_metrics.test_scheduler_stats_records_success_and_failure')
    stats = SchedulerStats()

    stats.record_success(execution_time=2.0)
    stats.record_failure(execution_time=4.0)

    assert stats.successful_bookings == 1
    assert stats.failed_bookings == 1
    assert stats.total_attempts == 2
    assert stats.avg_execution_time == 3.0
    assert round(stats.success_rate, 2) == 50.0


def test_scheduler_stats_health_and_recovery_counters():
    t('tests.unit.test_scheduler_metrics.test_scheduler_stats_health_and_recovery_counters')
    stats = SchedulerStats()

    stats.record_health_check()
    stats.record_health_check()
    stats.record_recovery_attempt()

    report = stats.format_report()

    assert stats.health_checks_performed == 2
    assert stats.recovery_attempts == 1
    assert "🩺 Health Checks: 2" in report
    assert "🛠️ Recovery Attempts: 1" in report
