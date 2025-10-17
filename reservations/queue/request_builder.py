"""Construct booking requests from queue and reservation data."""

from __future__ import annotations

from datetime import date, datetime
from typing import Any, Dict, Iterable, Optional, Sequence

from automation.shared.booking_contracts import (
    BookingRequest,
    BookingSource,
    BookingUser,
)
from reservations.models import ReservationRequest as ReservationRecord

REQUIRED_RESERVATION_FIELDS = {"target_date", "target_time"}


def _parse_date(value: Any) -> date:
    if isinstance(value, date):
        return value
    if isinstance(value, datetime):
        return value.date()
    if isinstance(value, str):
        return datetime.fromisoformat(value).date()
    raise ValueError(f"Unsupported date value: {value!r}")


def _normalise_courts(courts: Optional[Sequence[int]], fallback: Optional[int]) -> Iterable[int]:
    if courts:
        return [int(c) for c in courts if c]
    if fallback is not None:
        return [int(fallback)]
    raise ValueError("Queue reservation must specify at least one court preference")


def _resolve_user(reservation: Dict[str, Any], provided: Optional[Dict[str, Any]]) -> BookingUser:
    from botapp.booking.request_builder import booking_user_from_profile

    if provided:
        return booking_user_from_profile(provided)

    user_profile = {
        "user_id": reservation.get("user_id"),
        "first_name": reservation.get("first_name"),
        "last_name": reservation.get("last_name"),
        "email": reservation.get("email"),
        "phone": reservation.get("phone"),
        "tier_name": reservation.get("tier"),
    }
    return booking_user_from_profile(user_profile)


def build_request_from_reservation(
    reservation: Dict[str, Any],
    *,
    user_profile: Optional[Dict[str, Any]] = None,
    metadata: Optional[Dict[str, Any]] = None,
    executor_config: Optional[Dict[str, Any]] = None,
) -> BookingRequest:
    """Convert a raw reservation dict into a `BookingRequest`."""

    missing = [field for field in REQUIRED_RESERVATION_FIELDS if field not in reservation]
    if missing:
        raise ValueError(f"Reservation missing required fields: {', '.join(missing)}")

    target_date = _parse_date(reservation["target_date"])
    target_time = str(reservation["target_time"])
    courts_iterable = _normalise_courts(
        reservation.get("court_preferences"),
        reservation.get("court_number"),
    )

    user = _resolve_user(reservation, user_profile)

    base_metadata: Dict[str, Any] = {
        "source": BookingSource.QUEUED.value,
        "reservation_id": reservation.get("id"),
        "target_date": target_date.isoformat(),
        "target_time": target_time,
        "queue_status": reservation.get("status"),
    }
    if reservation.get("priority") is not None:
        base_metadata["priority"] = reservation.get("priority")
    if reservation.get("waitlist_position") is not None:
        base_metadata["waitlist_position"] = reservation.get("waitlist_position")
    if metadata:
        base_metadata.update(metadata)

    return BookingRequest.from_reservation_record(
        request_id=reservation.get("id"),
        user=user,
        target_date=target_date,
        target_time=target_time,
        courts=list(courts_iterable),
        source=BookingSource.QUEUED,
        metadata=base_metadata,
        executor_config=executor_config,
    )


def build_request_from_dataclass(
    reservation: ReservationRecord,
    *,
    metadata: Optional[Dict[str, Any]] = None,
    executor_config: Optional[Dict[str, Any]] = None,
) -> BookingRequest:
    """Adapter for `ReservationRequest` dataclasses used in queue services."""

    payload = {
        "id": reservation.request_id,
        "user_id": reservation.user.user_id,
        "first_name": reservation.user.first_name,
        "last_name": reservation.user.last_name,
        "email": reservation.user.email,
        "phone": reservation.user.phone,
        "tier": reservation.user.tier,
        "target_date": reservation.target_date,
        "target_time": reservation.target_time,
        "court_preferences": reservation.court_preferences,
        "status": reservation.status,
        "created_at": reservation.created_at,
    }

    base_metadata = metadata or {}

    return build_request_from_reservation(
        payload,
        metadata=base_metadata,
        executor_config=executor_config,
    )
