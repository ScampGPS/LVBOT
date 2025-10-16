"""Queue and scheduling domain services."""

from __future__ import annotations

from importlib import import_module
from typing import TYPE_CHECKING

if TYPE_CHECKING:  # pragma: no cover - typing helper
    from .reservation_queue import ReservationQueue, ReservationStatus
    from .reservation_scheduler import ReservationScheduler
    from .reservation_tracker import ReservationTracker

__all__ = [
    "ReservationQueue",
    "ReservationStatus",
    "ReservationScheduler",
    "ReservationTracker",
]


def __getattr__(name: str):
    if name in {"ReservationQueue", "ReservationStatus"}:
        module = import_module("lvbot.reservations.queue.reservation_queue")
    elif name in {"ReservationScheduler"}:
        module = import_module("lvbot.reservations.queue.reservation_scheduler")
    elif name in {"ReservationTracker"}:
        module = import_module("lvbot.reservations.queue.reservation_tracker")
    else:
        raise AttributeError(name)
    return getattr(module, name)
