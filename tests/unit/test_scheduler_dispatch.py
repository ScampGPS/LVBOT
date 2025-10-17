import asyncio
from types import SimpleNamespace

import pytest

from reservations.queue.scheduler.dispatch import DispatchJob, dispatch_to_executors
from reservations.queue.scheduler.outcome import record_outcome


@pytest.mark.asyncio
async def test_dispatch_to_executors_returns_results():
    jobs = [
        DispatchJob(
            reservation_id="res-1",
            assignment={"attempt": SimpleNamespace(reservation_id="res-1")},
            reservation={"id": "res-1"},
            index=1,
            total=1,
        )
    ]

    async def execute_single(assignment, reservation, index, total, *, prebuilt_request=None):
        await asyncio.sleep(0)
        return {"success": True, "court": 1}

    results, timeouts = await dispatch_to_executors(
        jobs,
        execute_single=execute_single,
        timeout_seconds=0.1,
    )

    assert timeouts == {}
    assert results["res-1"]["success"] is True


@pytest.mark.asyncio
async def test_dispatch_to_executors_reports_timeouts():
    jobs = [
        DispatchJob(
            reservation_id="res-timeout",
            assignment={"attempt": SimpleNamespace(reservation_id="res-timeout")},
            reservation={"id": "res-timeout"},
            index=1,
            total=1,
        )
    ]

    async def slow_execute(assignment, reservation, index, total, *, prebuilt_request=None):
        await asyncio.sleep(0.2)
        return {"success": True}

    results, timeouts = await dispatch_to_executors(
        jobs,
        execute_single=slow_execute,
        timeout_seconds=0.05,
    )

    assert "res-timeout" in timeouts
    assert "res-timeout" not in results


class DummyScheduler:
    def __init__(self):
        self.success_calls = []
        self.failed_calls = []
        self.orchestrator = SimpleNamespace(handle_booking_result=self.handle_booking_result)

    def handle_booking_result(self, reservation_id, **kwargs):
        self.recorded = (reservation_id, kwargs)

    def _update_reservation_success(self, reservation_id, result):
        self.success_calls.append((reservation_id, result))

    def _update_reservation_failed(self, reservation_id, error):
        self.failed_calls.append((reservation_id, error))


def test_record_outcome_success_invokes_handlers():
    scheduler = DummyScheduler()
    result = {"success": True, "court": 3}

    record_outcome(scheduler, "res-success", result)

    assert scheduler.success_calls == [("res-success", result)]
    assert scheduler.failed_calls == []


def test_record_outcome_failure_invokes_handlers():
    scheduler = DummyScheduler()
    result = {"success": False, "error": "boom"}

    record_outcome(scheduler, "res-fail", result)

    assert scheduler.failed_calls == [("res-fail", "boom")]
    assert scheduler.success_calls == []
