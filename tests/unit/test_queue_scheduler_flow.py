from tracking import t
from datetime import datetime
from types import SimpleNamespace

import pytest

from automation.shared.booking_contracts import BookingResult
from reservations.queue import reservation_scheduler as scheduler_module
from reservations.queue.reservation_scheduler import ReservationScheduler


class DummyQueue:
    def __init__(self, reservations):
        t('tests.unit.test_queue_scheduler_flow.DummyQueue.__init__')
        self.reservations = {r["id"]: r for r in reservations}
        self.status_updates = []
        self.removed = []

    def update_reservation_status(self, reservation_id, new_status, **kwargs):
        t('tests.unit.test_queue_scheduler_flow.DummyQueue.update_reservation_status')
        self.status_updates.append((reservation_id, new_status, kwargs))
        entry = self.reservations.get(reservation_id, {})
        entry.update({"status": new_status, **kwargs})
        return True

    def remove_reservation(self, reservation_id):
        t('tests.unit.test_queue_scheduler_flow.DummyQueue.remove_reservation')
        self.removed.append(reservation_id)
        self.reservations.pop(reservation_id, None)
        return True

    def get_reservation(self, reservation_id):
        t('tests.unit.test_queue_scheduler_flow.DummyQueue.get_reservation')
        return self.reservations.get(reservation_id)

    # Compatibility helpers used elsewhere
    def add_to_waitlist(self, reservation_id, position):  # pragma: no cover - not exercised
        t('tests.unit.test_queue_scheduler_flow.DummyQueue.add_to_waitlist')
        self.reservations.setdefault(reservation_id, {})["waitlist_position"] = position

    def get_waitlist_for_slot(self, target_date, target_time):  # pragma: no cover
        t('tests.unit.test_queue_scheduler_flow.DummyQueue.get_waitlist_for_slot')
        return []


class DummyUserDB:
    def __init__(self, profiles):
        t('tests.unit.test_queue_scheduler_flow.DummyUserDB.__init__')
        self._profiles = profiles

    def get_user(self, user_id):
        t('tests.unit.test_queue_scheduler_flow.DummyUserDB.get_user')
        return self._profiles.get(user_id)

    def is_admin(self, user_id):  # pragma: no cover - not used in these tests
        t('tests.unit.test_queue_scheduler_flow.DummyUserDB.is_admin')
        return False

    def is_vip(self, user_id):  # pragma: no cover - not used in these tests
        t('tests.unit.test_queue_scheduler_flow.DummyUserDB.is_vip')
        return False


class SuccessImmediateHandler:
    async def _execute_booking(self, booking_request):
        t('tests.unit.test_queue_scheduler_flow.SuccessImmediateHandler._execute_booking')
        return BookingResult.success_result(
            user=booking_request.user,
            request_id=booking_request.request_id,
            court_reserved=booking_request.court_preference.primary,
            time_reserved=booking_request.target_time,
            confirmation_code="CONF-789",
            message="Queue booking succeeded",
        )


class FailingImmediateHandler:
    async def _execute_booking(self, booking_request):
        t('tests.unit.test_queue_scheduler_flow.FailingImmediateHandler._execute_booking')
        return BookingResult.failure_result(
            user=booking_request.user,
            request_id=booking_request.request_id,
            message="Queue booking failed",
            errors=["Queue booking failed"],
        )


@pytest.fixture
def reservation_record():
    t('tests.unit.test_queue_scheduler_flow.reservation_record')
    return {
        "id": "resv-123",
        "user_id": 88,
        "first_name": "Sam",
        "last_name": "Player",
        "email": "sam@example.com",
        "phone": "+155555555",
        "target_date": "2025-08-12",
        "target_time": "07:00",
        "court_preferences": [1, 2],
        "status": "scheduled",
    }


@pytest.fixture
def user_db(reservation_record):
    t('tests.unit.test_queue_scheduler_flow.user_db')
    profile = {
        "user_id": reservation_record["user_id"],
        "first_name": reservation_record["first_name"],
        "last_name": reservation_record["last_name"],
        "email": reservation_record["email"],
        "phone": reservation_record["phone"],
        "tier": "regular",
    }
    return DummyUserDB({reservation_record["user_id"]: profile})


@pytest.fixture
def queue(reservation_record):
    t('tests.unit.test_queue_scheduler_flow.queue')
    return DummyQueue([reservation_record.copy()])


@pytest.fixture
def scheduler(monkeypatch, queue, user_db):
    t('tests.unit.test_queue_scheduler_flow.scheduler')
    monkeypatch.setattr(scheduler_module, "BrowserManager", lambda pool: SimpleNamespace(pool=pool))
    sched = ReservationScheduler(
        config=None,
        queue=queue,
        notification_callback=lambda *a, **k: None,
        browser_pool=None,
        user_manager=user_db,
    )
    # Speed up tests by avoiding actual browser initialisation logic
    sched.browser_pool = None
    return sched


@pytest.mark.asyncio
async def test_execute_single_booking_success_flow(scheduler, queue, reservation_record, user_db):
    t('tests.unit.test_queue_scheduler_flow.test_execute_single_booking_success_flow')
    scheduler.immediate_booking_handler = SuccessImmediateHandler()

    attempt = SimpleNamespace(reservation_id=reservation_record["id"], target_court=reservation_record["court_preferences"][0], attempt_number=1)
    assignment = {"attempt": attempt, "browser_id": "browser-1"}

    result_dict = await scheduler._execute_single_booking(
        assignment,
        reservation_record,
        target_date=datetime(2025, 8, 12),
        index=1,
        total=1,
    )

    assert result_dict["success"] is True
    assert result_dict["confirmation_code"] == "CONF-789"
    assert isinstance(result_dict["booking_result"], BookingResult)
    assert result_dict["booking_result"].metadata["queue_attempt"] == 1
    assert queue.status_updates[-1][1] == "success"


@pytest.mark.asyncio
async def test_execute_single_booking_failure_flow(scheduler, queue, reservation_record, user_db):
    t('tests.unit.test_queue_scheduler_flow.test_execute_single_booking_failure_flow')
    scheduler.immediate_booking_handler = FailingImmediateHandler()

    attempt = SimpleNamespace(reservation_id=reservation_record["id"], target_court=reservation_record["court_preferences"][0], attempt_number=2)
    assignment = {"attempt": attempt, "browser_id": "browser-2"}

    result_dict = await scheduler._execute_single_booking(
        assignment,
        reservation_record,
        target_date=datetime(2025, 8, 12),
        index=1,
        total=1,
    )

    assert result_dict["success"] is False
    assert "failed" in (result_dict.get("message") or result_dict.get("error", "")).lower()
    assert queue.status_updates[-1][1] == "failed"
    assert queue.status_updates[-1][2]["errors"] == ["Queue booking failed"]
