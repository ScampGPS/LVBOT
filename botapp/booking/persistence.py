"""Persistence helpers for immediate booking outcomes."""

from __future__ import annotations
from tracking import t

from typing import Dict, Optional

from automation.shared.booking_contracts import BookingRequest, BookingResult
from reservations.queue.reservation_tracker import ReservationTracker


def persist_immediate_success(
    request: BookingRequest,
    result: BookingResult,
    *,
    tracker: Optional[ReservationTracker] = None,
) -> str:
    """Store a successful immediate booking in the reservation tracker."""
    t('botapp.booking.persistence.persist_immediate_success')

    tracker = tracker or ReservationTracker()

    payload: Dict[str, str] = {
        "court": str(result.court_reserved or request.court_preference.primary),
        "date": request.target_date.isoformat(),
        "time": result.time_reserved or request.target_time,
        "confirmation_id": result.confirmation_code,
        "confirmation_url": result.confirmation_url,
        "message": result.message,
        "metadata": result.metadata,
    }

    return tracker.add_immediate_reservation(request.user.user_id, payload)


def persist_immediate_failure(
    request: BookingRequest,
    result: BookingResult,
    *,
    tracker: Optional[ReservationTracker] = None,
) -> str:
    """Record failed immediate bookings for auditing and diagnostics."""
    t('botapp.booking.persistence.persist_immediate_failure')

    tracker = tracker or ReservationTracker()

    payload: Dict[str, str] = {
        "court": str(request.court_preference.primary),
        "date": request.target_date.isoformat(),
        "time": request.target_time,
        "status": "failed",
        "message": result.message,
        "errors": list(result.errors),
        "metadata": result.metadata,
    }

    return tracker.add_immediate_reservation(request.user.user_id, payload)

