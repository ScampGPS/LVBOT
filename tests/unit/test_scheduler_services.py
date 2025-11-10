from tracking import t
from types import SimpleNamespace

import pytest

from automation.shared.booking_contracts import BookingResult
from reservations.queue.scheduler.pipeline import ReservationBatch
from reservations.queue.scheduler.services import (
    HydratedReservations,
    OutcomeRecorder,
    ReservationHydrator,
    SchedulerPipeline,
)


@pytest.mark.asyncio
async def test_scheduler_pipeline_runs_health_and_execution(monkeypatch):
    t('tests.unit.test_scheduler_services.test_scheduler_pipeline_runs_health_and_execution')
    calls = []

    async def health_check(reservations):
        t('tests.unit.test_scheduler_services.test_scheduler_pipeline_runs_health_and_execution.health_check')
        calls.append(("health", len(reservations)))
        return True

    async def executor(reservations, **kwargs):
        t('tests.unit.test_scheduler_services.test_scheduler_pipeline_runs_health_and_execution.executor')
        calls.append(("execute", len(reservations), kwargs.get("prepared_requests")))

    hydrator = SimpleNamespace(
        hydrate=lambda batch: HydratedReservations(batch.reservations, {"1": SimpleNamespace(request_id="1")})
    )

    pipeline = SchedulerPipeline(
        logger=SimpleNamespace(),
        hydrator=hydrator,
        health_check=health_check,
        executor=executor,
    )

    batch = ReservationBatch(time_key="2025-01-01_07:00", target_date="2025-01-01", target_time="07:00", reservations=[{"id": "1"}])
    empty_batch = ReservationBatch(time_key="empty", target_date="2025-01-02", target_time="08:00", reservations=[])
    evaluation = SimpleNamespace(requires_health_check=[empty_batch, batch], ready_for_execution=[empty_batch, batch])

    await pipeline.process(evaluation)

    assert calls[0][0] == "health"
    assert calls[-1][0] == "execute"
    assert isinstance(calls[-1][2], dict)


def test_reservation_hydrator_filters_failures(monkeypatch):
    t('tests.unit.test_scheduler_services.test_reservation_hydrator_filters_failures')
    recorded = {
        "persist": [],
        "failed": [],
    }

    booking_request = SimpleNamespace(request_id="2")

    class DummyFailure(Exception):
        pass

    def fake_hydrate(batch, **kwargs):
        t('tests.unit.test_scheduler_services.test_reservation_hydrator_filters_failures.fake_hydrate')
        failure = SimpleNamespace(reservation=batch.reservations[0], error=DummyFailure("boom"))
        missing_id_failure = SimpleNamespace(reservation={"name": "anon"}, error=DummyFailure("no id"))
        return SimpleNamespace(requests=[booking_request], failures=[failure, missing_id_failure])

    monkeypatch.setattr(
        "reservations.queue.scheduler.services.hydrate_reservation_batch",
        fake_hydrate,
    )

    def persist_outcome(reservation_id, result, queue):
        t('tests.unit.test_scheduler_services.test_reservation_hydrator_filters_failures.persist_outcome')
        recorded["persist"].append((reservation_id, result))

    def on_failure(reservation_id, error):
        t('tests.unit.test_scheduler_services.test_reservation_hydrator_filters_failures.on_failure')
        recorded["failed"].append((reservation_id, error))

    hydrator = ReservationHydrator(
        logger=SimpleNamespace(info=lambda *a, **k: None, debug=lambda *a, **k: None),
        executor_config=None,
        queue=SimpleNamespace(),
        persist_queue_outcome=persist_outcome,
        failure_builder=lambda reservation, message, errors=None: BookingResult.failure_result(
            user=SimpleNamespace(),
            request_id=reservation.get("id"),
            message=message,
            errors=errors or [message],
        ),
        on_failure=on_failure,
    )

    batch = ReservationBatch(
        time_key="key",
        target_date="2025-01-01",
        target_time="07:00",
        reservations=[{"id": "1"}, {"id": "2"}],
    )

    hydrated = hydrator.hydrate(batch)

    assert hydrated.reservations == [{"id": "2"}]
    assert hydrated.prepared_requests == {"2": booking_request}
    assert recorded["persist"]
    assert recorded["failed"]


def test_reservation_hydrator_no_failures(monkeypatch):
    t('tests.unit.test_scheduler_services.test_reservation_hydrator_no_failures')
    booking_request = SimpleNamespace(request_id="5")

    monkeypatch.setattr(
        "reservations.queue.scheduler.services.hydrate_reservation_batch",
        lambda batch, **kwargs: SimpleNamespace(requests=[booking_request], failures=[]),
    )

    hydrator = ReservationHydrator(
        logger=SimpleNamespace(info=lambda *a, **k: None, debug=lambda *a, **k: None),
        executor_config=None,
        queue=SimpleNamespace(),
        persist_queue_outcome=lambda *a, **k: None,
        failure_builder=lambda *a, **k: BookingResult.failure_result(user=SimpleNamespace(), request_id="1", message="fail"),
        on_failure=lambda *a, **k: None,
    )

    batch = ReservationBatch(
        time_key="key",
        target_date="2025-01-01",
        target_time="07:00",
        reservations=[{"id": "5"}],
    )

    hydrated = hydrator.hydrate(batch)
    assert hydrated.reservations == batch.reservations
    assert hydrated.prepared_requests == {"5": booking_request}


@pytest.mark.asyncio
async def test_outcome_recorder_handles_timeouts_and_notifications(monkeypatch):
    t('tests.unit.test_scheduler_services.test_outcome_recorder_handles_timeouts_and_notifications')
    recorded_outcomes = []
    notifications = []

    async def send_notification(user_id, message):
        t('tests.unit.test_scheduler_services.test_outcome_recorder_handles_timeouts_and_notifications.send_notification')
        notifications.append((user_id, message))

    async def set_critical_operation(_flag):
        t('tests.unit.test_scheduler_services.test_outcome_recorder_handles_timeouts_and_notifications.set_critical_operation')
        return None

    scheduler = SimpleNamespace(
        logger=SimpleNamespace(
            info=lambda *a, **k: None,
            error=lambda *a, **k: None,
        ),
        queue=SimpleNamespace(),
        browser_pool=SimpleNamespace(set_critical_operation=set_critical_operation),
        bot=SimpleNamespace(send_notification=send_notification),
        user_db=SimpleNamespace(get_user=lambda _uid: {"id": _uid}),
        _get_reservation_by_id=lambda reservation_id: {
            "id": reservation_id,
            "user_id": 42,
            "target_date": "2025-01-01",
            "target_time": "07:00",
        },
        _get_reservation_field=lambda reservation, field, default=None: reservation.get(field, default),
        orchestrator=SimpleNamespace(handle_booking_result=lambda *a, **k: recorded_outcomes.append((a, k))),
        _update_reservation_success=lambda *a, **k: None,
        _update_reservation_failed=lambda *a, **k: None,
        stats=SimpleNamespace(record_success=lambda *a, **k: None, record_failure=lambda *a, **k: None),
    )

    recorder = OutcomeRecorder(
        scheduler=scheduler,
        persist_queue_outcome=lambda *a, **k: None,
        failure_builder=lambda reservation, message, errors=None: BookingResult.failure_result(
            user=SimpleNamespace(),
            request_id=reservation.get("id"),
            message=message,
            errors=errors or [message],
        ),
        result_mapper=lambda result: {
            "success": result.success,
            "error": result.message,
            "booking_result": result,
        },
    )

    reservation_lookup = {"1": {"id": "1"}}
    results = {"1": {"success": True, "court": 1}}
    await recorder.handle_dispatch_results(reservation_lookup, results, {"2": "timeout"})
    assert recorded_outcomes

    await recorder.notify(results)
    assert notifications


@pytest.mark.asyncio
async def test_outcome_recorder_notify_handles_missing_dependencies():
    t('tests.unit.test_scheduler_services.test_outcome_recorder_notify_handles_missing_dependencies')
    scheduler = SimpleNamespace(
        bot=None,
        user_db=None,
        logger=SimpleNamespace(info=lambda *a, **k: None, error=lambda *a, **k: None),
        queue=SimpleNamespace(),
    )
    recorder = OutcomeRecorder(
        scheduler=scheduler,
        persist_queue_outcome=lambda *a, **k: None,
        failure_builder=lambda *a, **k: BookingResult.failure_result(user=SimpleNamespace(), request_id="1", message="fail"),
        result_mapper=lambda result: {},
    )

    await recorder.notify({"1": {"success": True}})


def test_outcome_recorder_failure_message_format():
    t('tests.unit.test_scheduler_services.test_outcome_recorder_failure_message_format')
    scheduler = SimpleNamespace(
        logger=SimpleNamespace(info=lambda *a, **k: None, error=lambda *a, **k: None),
        _get_reservation_field=lambda reservation, field, default=None: reservation.get(field, default),
        queue=SimpleNamespace(),
    )
    recorder = OutcomeRecorder(
        scheduler=scheduler,
        persist_queue_outcome=lambda *a, **k: None,
        failure_builder=lambda *a, **k: BookingResult.failure_result(user=SimpleNamespace(), request_id="1", message="fail"),
        result_mapper=lambda result: {},
    )

    message = recorder._format_message(
        {"target_date": "2025-01-01", "target_time": "07:00"},
        {"success": False, "error": "boom"},
    )
    assert "boom" in message


def test_outcome_recorder_format_success_booking_result():
    t('tests.unit.test_scheduler_services.test_outcome_recorder_format_success_booking_result')
    scheduler = SimpleNamespace(
        logger=SimpleNamespace(info=lambda *a, **k: None, error=lambda *a, **k: None),
        _get_reservation_field=lambda reservation, field, default=None: reservation.get(field, default),
        queue=SimpleNamespace(),
    )
    recorder = OutcomeRecorder(
        scheduler=scheduler,
        persist_queue_outcome=lambda *a, **k: None,
        failure_builder=lambda *a, **k: BookingResult.failure_result(user=SimpleNamespace(), request_id="1", message="fail"),
        result_mapper=lambda result: {},
    )

    booking_result = BookingResult.success_result(
        user=SimpleNamespace(),
        request_id="1",
        court_reserved=1,
        time_reserved="07:00",
        confirmation_code="CONF",
    )
    message = recorder._format_message(
        {"target_date": "2025-01-01", "target_time": "07:00"},
        {"booking_result": booking_result},
    )
    assert "✅" in message


@pytest.mark.asyncio
async def test_outcome_recorder_notify_skips_missing_entities():
    t('tests.unit.test_scheduler_services.test_outcome_recorder_notify_skips_missing_entities')
    notifications = []

    async def send_notification(user_id, message):
        t('tests.unit.test_scheduler_services.test_outcome_recorder_notify_skips_missing_entities.send_notification')
        notifications.append((user_id, message))

    scheduler = SimpleNamespace(
        logger=SimpleNamespace(info=lambda *a, **k: None, error=lambda *a, **k: None),
        queue=SimpleNamespace(),
        bot=SimpleNamespace(send_notification=send_notification),
        user_db=SimpleNamespace(get_user=lambda _uid: None),
        _get_reservation_field=lambda reservation, field, default=None: reservation.get(field, default),
    )

    recorder = OutcomeRecorder(
        scheduler=scheduler,
        persist_queue_outcome=lambda *a, **k: None,
        failure_builder=lambda *a, **k: BookingResult.failure_result(user=SimpleNamespace(), request_id="1", message="fail"),
        result_mapper=lambda result: {},
    )

    scheduler._get_reservation_by_id = lambda _reservation_id: None
    await recorder.notify({"1": {"success": True}})
    scheduler._get_reservation_by_id = lambda _reservation_id: {"user_id": 1, "target_date": "2025-01-01", "target_time": "07:00"}
    await recorder.notify({"2": {"success": True}})
    assert not notifications
