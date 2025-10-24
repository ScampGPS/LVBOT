from pathlib import Path

from reservations.queue.reservation_repository import ReservationRepository
from tests.helpers import DummyLogger


def test_repository_round_trip(tmp_path):
    logger = DummyLogger()
    repo_path = tmp_path / "queue.json"
    repository = ReservationRepository(str(repo_path), logger=logger)

    data = [
        {"id": "abc", "status": "pending"},
        {"id": "def", "status": "scheduled"},
    ]

    repository.save(data)
    assert repo_path.exists()

    reloaded = ReservationRepository(str(repo_path), logger=DummyLogger()).load()
    assert reloaded == data
