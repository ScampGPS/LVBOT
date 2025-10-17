from pathlib import Path

from reservations.queue.reservation_repository import ReservationRepository


class DummyLogger:
    def __init__(self):
        self.entries = []

    def debug(self, *args, **kwargs):
        self.entries.append(("debug", args, kwargs))

    def info(self, *args, **kwargs):
        self.entries.append(("info", args, kwargs))

    def warning(self, *args, **kwargs):
        self.entries.append(("warning", args, kwargs))

    def error(self, *args, **kwargs):
        self.entries.append(("error", args, kwargs))


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
