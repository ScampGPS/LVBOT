from tracking import t
import logging

import pytest

from reservations.queue.reservation_validation import ensure_unique_slot


def test_ensure_unique_slot_allows_unique():
    t('tests.unit.test_reservation_validation.test_ensure_unique_slot_allows_unique')
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
        courts=[1],
        logger=logging.getLogger("test"),
    )


def test_ensure_unique_slot_raises_for_conflict():
    t('tests.unit.test_reservation_validation.test_ensure_unique_slot_raises_for_conflict')
    reservations = [
        {
            "id": "abc",
            "user_id": 1,
            "target_date": "2024-01-01",
            "target_time": "08:00",
            "status": "scheduled",
            "court_preferences": [1],
        }
    ]

    with pytest.raises(ValueError):
        ensure_unique_slot(
            reservations,
            user_id=1,
            target_date="2024-01-01",
            target_time="08:00",
            courts=[1],
            logger=logging.getLogger("test"),
        )


def test_ensure_unique_slot_allows_different_courts():
    t('tests.unit.test_reservation_validation.test_ensure_unique_slot_allows_different_courts')
    reservations = [
        {
            "id": "abc",
            "user_id": 1,
            "target_date": "2024-01-01",
            "target_time": "08:00",
            "status": "scheduled",
            "court_preferences": [2],
        }
    ]

    ensure_unique_slot(
        reservations,
        user_id=1,
        target_date="2024-01-01",
        target_time="08:00",
        courts=[1],
        logger=logging.getLogger("test"),
    )


def test_ensure_unique_slot_conflict_when_existing_any_court():
    t('tests.unit.test_reservation_validation.test_ensure_unique_slot_conflict_when_existing_any_court')
    reservations = [
        {
            "id": "abc",
            "user_id": 1,
            "target_date": "2024-01-01",
            "target_time": "08:00",
            "status": "scheduled",
            "court_preferences": [],
        }
    ]

    with pytest.raises(ValueError):
        ensure_unique_slot(
            reservations,
            user_id=1,
            target_date="2024-01-01",
            target_time="08:00",
            courts=[3],
            logger=logging.getLogger("test"),
        )
