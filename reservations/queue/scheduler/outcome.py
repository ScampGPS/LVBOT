"""Helpers for recording queued booking outcomes."""

from __future__ import annotations

from typing import TYPE_CHECKING, Any, Dict

if TYPE_CHECKING:  # pragma: no cover - typing helper
    from reservations.queue.reservation_scheduler import ReservationScheduler


def record_outcome(
    scheduler: "ReservationScheduler",
    reservation_id: str,
    result: Dict[str, Any],
) -> None:
    """Update orchestrator state and queue statistics for a booking result."""

    fallback = scheduler.orchestrator.handle_booking_result(
        reservation_id,
        success=bool(result.get("success")),
        court_booked=result.get("court"),
    )

    if result.get("success"):
        scheduler._update_reservation_success(reservation_id, result)
        return

    if fallback:
        result["retry_scheduled"] = True
        scheduler.schedule_fallback_retry(reservation_id, fallback)
        return

    error_msg = result.get("error", "Unknown error")
    scheduler._update_reservation_failed(reservation_id, error_msg)
