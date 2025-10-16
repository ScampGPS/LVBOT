import json
from datetime import date, datetime

import pytest

from reservations.models import ReservationRequest, UserProfile
from reservations.queue.reservation_queue import ReservationQueue, ReservationStatus


def make_request(user_id: int = 1, status: str = ReservationStatus.PENDING.value) -> ReservationRequest:
    user = UserProfile(
        user_id=user_id,
        first_name="Test",
        last_name="User",
        email="test@example.com",
        phone="1234567890",
    )
    return ReservationRequest(
        request_id=None,
        user=user,
        target_date=date(2025, 1, 1),
        target_time="08:00",
        court_preferences=[1, 2],
        created_at=datetime(2024, 12, 1, 12, 0, 0),
        status=status,
    )


def test_add_reservation_request_round_trip(tmp_path):
    queue_file = tmp_path / "queue.json"
    queue = ReservationQueue(file_path=str(queue_file))

    request = make_request(user_id=123)
    reservation_id = queue.add_reservation_request(request)

    assert reservation_id
    stored = queue.list_reservations()
    assert len(stored) == 1
    stored_request = stored[0]
    assert stored_request.user.user_id == 123
    assert stored_request.target_time == "08:00"


def test_queue_persistence(tmp_path):
    queue_file = tmp_path / "queue.json"
    queue = ReservationQueue(file_path=str(queue_file))
    queue.add_reservation_request(make_request(user_id=1))

    # Reload from disk and ensure data persisted
    queue_reloaded = ReservationQueue(file_path=str(queue_file))
    stored = queue_reloaded.list_reservations()
    assert len(stored) == 1
    assert stored[0].user.first_name == "Test"


def test_duplicate_reservation_detection(tmp_path):
    queue_file = tmp_path / "queue.json"
    queue = ReservationQueue(file_path=str(queue_file))
    queue.add_reservation(
        {
            "user_id": 99,
            "target_date": "2025-01-01",
            "target_time": "08:00",
        }
    )

    with pytest.raises(ValueError):
        queue.add_reservation(
            {
                "user_id": 99,
                "target_date": "2025-01-01",
                "target_time": "08:00",
            }
        )
