from tracking import t
import datetime as dt
from typing import List

import pytest

from reservations.queue.scheduler import (
    HydratedBatch,
    ReservationBatch,
    hydrate_reservation_batch,
    pull_ready_reservations,
)


class DummyQueue:
    def __init__(self, reservations: List[dict]):
        t('tests.unit.test_queue_pipeline.DummyQueue.__init__')
        self._reservations = reservations

    def get_pending_reservations(self) -> List[dict]:
        t('tests.unit.test_queue_pipeline.DummyQueue.get_pending_reservations')
        return list(self._reservations)


@pytest.fixture
def sample_reservations():
    t('tests.unit.test_queue_pipeline.sample_reservations')
    base = {
        "id": "abc123",
        "user_id": 1,
        "first_name": "Test",
        "last_name": "User",
        "email": "test@example.com",
        "phone": "+1",
        "target_date": "2024-01-05",
        "target_time": "08:00",
        "court_preferences": [1, 2],
        "status": "scheduled",
        "scheduled_execution": "2024-01-03T08:00:00",
    }
    ready = base
    health = {**base, "id": "def456", "scheduled_execution": "2024-01-03T08:09:00"}
    waiting = {**base, "id": "ghi789", "scheduled_execution": "2024-01-03T09:00:00"}
    return [ready, health, waiting]


def test_pull_ready_reservations_groups_slots(sample_reservations):
    t('tests.unit.test_queue_pipeline.test_pull_ready_reservations_groups_slots')
    queue = DummyQueue(sample_reservations)
    now = dt.datetime.fromisoformat("2024-01-03T08:05:00")

    evaluation = pull_ready_reservations(queue, now=now, logger=None)

    ready = evaluation.ready_for_execution
    health = evaluation.requires_health_check

    assert len(ready) == 1
    assert ready[0].reservations[0]["id"] == "abc123"
    assert len(health) == 1
    assert health[0].reservations[0]["id"] == "def456"


def test_hydrate_reservation_batch_builds_requests(sample_reservations):
    t('tests.unit.test_queue_pipeline.test_hydrate_reservation_batch_builds_requests')
    batch = ReservationBatch(
        time_key="2024-01-05_08:00",
        target_date="2024-01-05",
        target_time="08:00",
        reservations=sample_reservations[:1],
    )

    hydrated = hydrate_reservation_batch(batch, logger=None)

    assert isinstance(hydrated, HydratedBatch)
    assert len(hydrated.requests) == 1
    assert not hydrated.failures


def test_hydrate_reservation_batch_collects_failures(sample_reservations):
    t('tests.unit.test_queue_pipeline.test_hydrate_reservation_batch_collects_failures')
    broken = dict(sample_reservations[0])
    broken.pop("target_time")
    batch = ReservationBatch(
        time_key="2024-01-05_missing",
        target_date="2024-01-05",
        target_time="08:00",
        reservations=[broken],
    )

    hydrated = hydrate_reservation_batch(batch, logger=None)

    assert not hydrated.requests
    assert len(hydrated.failures) == 1
