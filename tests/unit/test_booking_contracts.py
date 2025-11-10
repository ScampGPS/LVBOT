from tracking import t
from datetime import date, datetime

from automation.shared.booking_contracts import BookingSource, BookingUser, compose_booking_metadata


def test_as_executor_payload_defaults():
    t('tests.unit.test_booking_contracts.test_as_executor_payload_defaults')
    user = BookingUser(
        user_id=123,
        first_name="Jane",
        last_name="Doe",
        email="jane@example.com",
        phone="555-0100",
    )

    payload = user.as_executor_payload()

    assert payload == {
        "first_name": "Jane",
        "last_name": "Doe",
        "email": "jane@example.com",
        "phone": "555-0100",
        "user_id": 123,
    }


def test_as_executor_payload_options():
    t('tests.unit.test_booking_contracts.test_as_executor_payload_options')
    user = BookingUser(
        user_id=456,
        first_name="John",
        last_name="Smith",
        email="john@example.com",
        phone="555-0200",
        tier=None,
    )

    payload = user.as_executor_payload(user_id_as_str=True, include_tier_when_none=True)

    assert payload == {
        "first_name": "John",
        "last_name": "Smith",
        "email": "john@example.com",
        "phone": "555-0200",
        "user_id": "456",
        "tier": None,
    }

    payload_with_tier = user.as_executor_payload(user_id_as_str=True)

    assert "tier" not in payload_with_tier



def test_compose_booking_metadata_basic():
    t('tests.unit.test_booking_contracts.test_compose_booking_metadata_basic')
    metadata = compose_booking_metadata(
        BookingSource.IMMEDIATE,
        date(2025, 5, 1),
        '08:30',
    )

    assert metadata == {
        'source': BookingSource.IMMEDIATE.value,
        'target_date': '2025-05-01',
        'target_time': '08:30',
    }


def test_compose_booking_metadata_with_extras_and_datetime():
    t('tests.unit.test_booking_contracts.test_compose_booking_metadata_with_extras_and_datetime')
    metadata = compose_booking_metadata(
        BookingSource.QUEUED,
        datetime(2025, 5, 2, 10, 0),
        '09:15',
        extras={'reservation_id': 'abc', 'priority': 1},
    )

    assert metadata['source'] == BookingSource.QUEUED.value
    assert metadata['target_date'] == '2025-05-02'
    assert metadata['target_time'] == '09:15'
    assert metadata['reservation_id'] == 'abc'
    assert metadata['priority'] == 1
