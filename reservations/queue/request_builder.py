"""Construct booking requests from queue and reservation data."""

from __future__ import annotations

from datetime import date, datetime
from typing import Any, Dict, Iterable, Optional, Sequence

from automation.shared.booking_contracts import (
    BookingRequest,
    BookingSource,
    BookingUser,
    compose_booking_metadata,
)
from reservations.models import ReservationRequest as ReservationRecord

REQUIRED_RESERVATION_FIELDS = {"target_date", "target_time"}



SUMMARY_REQUIRED_FIELDS = {
    "user_id",
    "first_name",
    "last_name",
    "email",
    "phone",
    "target_date",
    "target_time",
    "court_preferences",
}


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

    extras: Dict[str, Any] = {
        "reservation_id": reservation.get("id"),
        "queue_status": reservation.get("status"),
    }
    if reservation.get("priority") is not None:
        extras["priority"] = reservation.get("priority")
    if reservation.get("waitlist_position") is not None:
        extras["waitlist_position"] = reservation.get("waitlist_position")

    base_metadata = compose_booking_metadata(
        BookingSource.QUEUED,
        target_date,
        target_time,
        extras=extras,
    )
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




def build_reservation_request_from_summary(summary: Dict[str, Any]) -> ReservationRecord:
    """Convert a queue booking summary into a `ReservationRequest`."""

    missing = [field for field in SUMMARY_REQUIRED_FIELDS if field not in summary]
    if missing:
        raise ValueError(f"Queue booking summary missing fields: {', '.join(sorted(missing))}")

    target_date = _parse_date(summary["target_date"])
    target_time = str(summary["target_time"])
    court_preferences = [int(c) for c in summary.get("court_preferences", [])]
    if not court_preferences:
        raise ValueError("Queue booking summary requires at least one court preference")

    created_at_raw = summary.get("created_at")
    if isinstance(created_at_raw, datetime):
        created_at = created_at_raw
    elif isinstance(created_at_raw, str) and created_at_raw:
        created_at = datetime.fromisoformat(created_at_raw)
    else:
        created_at = datetime.utcnow()

    from botapp.booking.request_builder import booking_user_from_profile
    from reservations.models import ReservationRequest as ReservationRecordDataclass, UserProfile

    profile_dict = {
        "user_id": summary.get("user_id"),
        "first_name": summary.get("first_name"),
        "last_name": summary.get("last_name"),
        "email": summary.get("email"),
        "phone": summary.get("phone"),
        "tier_name": summary.get("tier"),
    }
    booking_user = booking_user_from_profile(profile_dict)
    user_profile = UserProfile(
        user_id=booking_user.user_id,
        first_name=booking_user.first_name,
        last_name=booking_user.last_name,
        email=booking_user.email,
        phone=booking_user.phone,
        tier=booking_user.tier,
    )

    return ReservationRecordDataclass(
        request_id=summary.get("reservation_id"),
        user=user_profile,
        target_date=target_date,
        target_time=target_time,
        court_preferences=court_preferences,
        created_at=created_at,
        status=summary.get("status", "pending"),
    )


def reservation_request_to_payload(reservation: ReservationRecord) -> Dict[str, Any]:
    """Serialize a `ReservationRequest` into the legacy queue payload shape."""

    payload = {
        'id': reservation.request_id,
        'user_id': reservation.user.user_id,
        'first_name': reservation.user.first_name,
        'last_name': reservation.user.last_name,
        'email': reservation.user.email,
        'phone': reservation.user.phone,
        'tier': reservation.user.tier,
        'target_date': reservation.target_date.isoformat(),
        'target_time': reservation.target_time,
        'court_preferences': reservation.court_preferences,
        'created_at': reservation.created_at.isoformat(),
        'status': reservation.status,
    }
    if reservation.court_preferences:
        payload['court_number'] = reservation.court_preferences[0]
    return payload


def build_request_from_dataclass(
    reservation: ReservationRecord,
    *,
    metadata: Optional[Dict[str, Any]] = None,
    executor_config: Optional[Dict[str, Any]] = None,
) -> BookingRequest:
    """Adapter for `ReservationRequest` dataclasses used in queue services."""

    payload = reservation_request_to_payload(reservation)

    base_metadata = metadata or {}

    return build_request_from_reservation(
        payload,
        metadata=base_metadata,
        executor_config=executor_config,
    )
