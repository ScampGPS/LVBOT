"""Persistence helpers for queue-driven booking outcomes."""

from __future__ import annotations

from typing import Dict, Optional

from automation.shared.booking_contracts import BookingResult
from reservations.queue.reservation_queue import ReservationQueue, ReservationStatus


def persist_queue_outcome(
    reservation_id: str,
    result: BookingResult,
    *,
    queue: Optional[ReservationQueue] = None,
) -> bool:
    """Update queue records according to a booking result."""

    queue = queue or ReservationQueue()

    status = (
        ReservationStatus.SUCCESS.value
        if result.success
        else ReservationStatus.FAILED.value
    )

    updates: Dict[str, object] = {
        "result_message": result.message,
        "confirmation_code": result.confirmation_code,
        "confirmation_url": result.confirmation_url,
        "court_reserved": result.court_reserved,
        "time_reserved": result.time_reserved,
        "errors": list(result.errors),
        "metadata": result.metadata,
    }

    return queue.update_reservation_status(reservation_id, status, **updates)


def persist_queue_cancellation(
    reservation_id: str,
    *,
    queue: Optional[ReservationQueue] = None,
    metadata: Optional[Dict[str, object]] = None,
) -> bool:
    """Mark a queued reservation as cancelled with optional metadata."""

    queue = queue or ReservationQueue()
    updates = metadata or {}
    return queue.update_reservation_status(
        reservation_id,
        ReservationStatus.CANCELLED.value,
        **updates,
    )

