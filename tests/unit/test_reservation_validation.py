import logging

import pytest

from reservations.queue.reservation_validation import ensure_unique_slot


def test_ensure_unique_slot_allows_unique():
    reservations = [
        {
            "id": "abc",
            "user_id": 1,
            "target_date": "2024-01-01",
            "target_time": "08:00",
            "status": "pending",
        }
    ]

    # Should not raise for different slot
    ensure_unique_slot(
        reservations,
        user_id=1,
        target_date="2024-01-01",
        target_time="09:00",
        logger=logging.getLogger("test"),
    )


def test_ensure_unique_slot_raises_for_conflict():
    reservations = [
        {
            "id": "abc",
            "user_id": 1,
            "target_date": "2024-01-01",
            "target_time": "08:00",
            "status": "scheduled",
        }
    ]

    with pytest.raises(ValueError):
        ensure_unique_slot(
            reservations,
            user_id=1,
            target_date="2024-01-01",
            target_time="08:00",
            logger=logging.getLogger("test"),
        )
