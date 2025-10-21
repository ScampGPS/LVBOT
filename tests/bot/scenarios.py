"""High-level scenarios executed via the bot testing harness."""

from __future__ import annotations

from datetime import date
from typing import Iterable, Optional

from .harness import BotTestHarness, run_async


def queue_booking_flow(
    *,
    target_date: Optional[date] = None,
    target_time: str = "09:00",
    court_callback: str = "queue_court_all",
    queue_path: Optional[str] = None,
) -> Iterable[dict]:
    """Drive the queue booking conversation and return recorded outputs."""

    harness = BotTestHarness(queue_path=queue_path)
    try:
        run_async(
            harness.run_queue_booking_flow(
                target_date=target_date,
                target_time=target_time,
                court_callback=court_callback,
            )
        )
        return list(harness.records)
    finally:
        harness.close()
