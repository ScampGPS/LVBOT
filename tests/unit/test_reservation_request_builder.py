from datetime import datetime

import pytest

from automation.shared.booking_contracts import BookingRequest, BookingSource
from reservations.queue.request_builder import ReservationRequestBuilder
from reservations.queue.reservation_queue import QueueRecordSerializer


@pytest.fixture()
def builder() -> ReservationRequestBuilder:
    return ReservationRequestBuilder()


def test_from_summary_produces_reservation_record(builder):
    summary = {
        "reservation_id": "abc123",
        "user_id": 42,
        "first_name": "Ana",
        "last_name": "Perez",
        "email": "ana@example.com",
        "phone": "555-0000",
        "target_date": "2025-01-01",
        "target_time": "08:00",
        "court_preferences": [1, 2],
        "created_at": "2024-12-01T12:00:00",
        "status": "scheduled",
        "tier": "VIP",
    }

    record = builder.from_summary(summary)

    assert record.request_id == "abc123"
    assert record.target_time == "08:00"
    assert record.court_preferences == [1, 2]
    assert record.user.email == "ana@example.com"
    assert record.status == "scheduled"


def test_from_dict_generates_booking_request(builder):
    reservation = {
        "id": "xyz789",
        "user_id": 99,
        "first_name": "Luis",
        "last_name": "Lopez",
        "email": "luis@example.com",
        "phone": "555-1234",
        "target_date": "2025-02-02",
        "target_time": "09:00",
        "court_preferences": [3],
        "priority": 1,
        "status": "pending",
    }

    request = builder.from_dict(reservation, metadata={"custom": "value"})

    assert isinstance(request, BookingRequest)
    assert request.preferred_courts() == [3]
    assert request.target_time == "09:00"
    assert request.metadata["custom"] == "value"
    assert request.metadata["source"] == BookingSource.QUEUED.value
    assert request.metadata["priority"] == 1


def test_record_from_payload_handles_missing_user_fields(builder):
    payload = {
        "id": "minimal-1",
        "user_id": 0,
        "target_date": "2025-03-03",
        "target_time": "07:30",
        "court_preferences": [2],
    }

    record = builder.record_from_payload(payload)

    assert record.request_id == "minimal-1"
    assert record.court_preferences == [2]
    # Defaults applied for missing user info
    assert record.user.first_name == "Queue"
    assert record.user.email.startswith("queue-user--1@")


def test_to_payload_round_trip(builder):
    reservation = builder.from_summary(
        {
            "reservation_id": "round-1",
            "user_id": 7,
            "first_name": "Eva",
            "last_name": "Ruiz",
            "email": "eva@example.com",
            "phone": "555-9876",
            "target_date": "2025-04-04",
            "target_time": "10:30",
            "court_preferences": [1],
        }
    )

    payload = builder.to_payload(reservation)
    rebuilt = builder.record_from_payload(payload)

    assert rebuilt.request_id == reservation.request_id
    assert rebuilt.target_time == reservation.target_time
    assert rebuilt.court_preferences == reservation.court_preferences


def test_queue_record_serializer_normalises_payload(builder):
    serializer = QueueRecordSerializer(builder)
    payload = {
        "id": "ser-1",
        "user_id": 5,
        "target_date": datetime(2025, 5, 5),
        "target_time": "06:00",
        "court_preferences": [1, 2],
        "status": "pending",
    }

    normalised = serializer.normalise_payload(payload)
    assert normalised["target_date"] == "2025-05-05"
    assert normalised["court_preferences"] == [1, 2]

    record = serializer.from_storage(normalised)
    assert record.target_date.isoformat() == "2025-05-05"
