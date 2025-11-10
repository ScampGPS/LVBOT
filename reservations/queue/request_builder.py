"""Builders for transforming queue reservations into booking requests."""

from __future__ import annotations
from tracking import t

from datetime import date, datetime
from typing import Any, Dict, Iterable, Mapping, Optional, Sequence

from automation.shared.booking_contracts import (
    BookingRequest,
    BookingSource,
    BookingUser,
    compose_booking_metadata,
)
from reservations.models import ReservationRequest as ReservationRecord, UserProfile

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


class ReservationRequestBuilder:
    """Construct queue reservation dataclasses and booking requests."""

    def __init__(
        self,
        *,
        booking_user_factory: Optional[Any] = None,
    ) -> None:
        t('reservations.queue.request_builder.ReservationRequestBuilder.__init__')
        self._booking_user_factory = booking_user_factory or _default_booking_user_factory

    # ------------------------------------------------------------------
    # Public API
    # ------------------------------------------------------------------
    def from_summary(self, summary: Mapping[str, Any]) -> ReservationRecord:
        """Convert a queue booking summary dict into a `ReservationRequest`."""
        t('reservations.queue.request_builder.ReservationRequestBuilder.from_summary')

        self._ensure_fields(summary, SUMMARY_REQUIRED_FIELDS, "Queue booking summary")

        target_date = self._parse_date(summary["target_date"])
        target_time = str(summary["target_time"])

        court_preferences = [int(c) for c in summary.get("court_preferences", []) if c]
        if not court_preferences:
            raise ValueError("Queue booking summary requires at least one court preference")

        created_at = self._resolve_created_at(summary.get("created_at"))

        user_profile = self._build_user_profile(summary)

        return ReservationRecord(
            request_id=summary.get("reservation_id"),
            user=user_profile,
            target_date=target_date,
            target_time=target_time,
            court_preferences=court_preferences,
            created_at=created_at,
            status=summary.get("status", "pending"),
        )

    def from_dict(
        self,
        reservation: Mapping[str, Any],
        *,
        user_profile: Optional[Mapping[str, Any]] = None,
        metadata: Optional[Dict[str, Any]] = None,
        executor_config: Optional[Dict[str, Any]] = None,
    ) -> BookingRequest:
        """Convert a raw reservation mapping into a `BookingRequest`."""
        t('reservations.queue.request_builder.ReservationRequestBuilder.from_dict')

        self._ensure_fields(reservation, REQUIRED_RESERVATION_FIELDS, "Reservation")

        target_date = self._parse_date(reservation["target_date"])
        target_time = str(reservation["target_time"])
        courts = list(
            self._normalise_courts(
                reservation.get("court_preferences"),
                reservation.get("court_number"),
            )
        )

        booking_user = self._resolve_user(reservation, user_profile)
        metadata_payload = self._compose_metadata(reservation, target_date, target_time, metadata)

        return BookingRequest.from_reservation_record(
            request_id=reservation.get("id"),
            user=booking_user,
            target_date=target_date,
            target_time=target_time,
            courts=courts,
            source=BookingSource.QUEUED,
            metadata=metadata_payload,
            executor_config=executor_config,
        )

    def from_record(
        self,
        reservation: ReservationRecord,
        *,
        metadata: Optional[Dict[str, Any]] = None,
        executor_config: Optional[Dict[str, Any]] = None,
    ) -> BookingRequest:
        """Adapter to build a `BookingRequest` from a dataclass reservation."""
        t('reservations.queue.request_builder.ReservationRequestBuilder.from_record')

        payload = self.to_payload(reservation)
        return self.from_dict(
            payload,
            metadata=metadata,
            executor_config=executor_config,
        )

    def to_payload(self, reservation: ReservationRecord) -> Dict[str, Any]:
        """Serialize a `ReservationRequest` into the legacy queue payload structure."""
        t('reservations.queue.request_builder.ReservationRequestBuilder.to_payload')

        payload = {
            "id": reservation.request_id,
            "user_id": reservation.user.user_id,
            "first_name": reservation.user.first_name,
            "last_name": reservation.user.last_name,
            "email": reservation.user.email,
            "phone": reservation.user.phone,
            "tier": reservation.user.tier,
            "target_date": reservation.target_date.isoformat(),
            "target_time": reservation.target_time,
            "court_preferences": list(reservation.court_preferences),
            "created_at": reservation.created_at.isoformat(),
            "status": reservation.status,
        }
        if reservation.court_preferences:
            payload["court_number"] = reservation.court_preferences[0]
        return payload

    def record_from_payload(self, payload: Mapping[str, Any]) -> ReservationRecord:
        """Convert a stored queue payload back into a `ReservationRequest`."""
        t('reservations.queue.request_builder.ReservationRequestBuilder.record_from_payload')

        target_date = self._parse_date(payload["target_date"])
        target_time = str(payload["target_time"])
        try:
            court_preferences = list(
                self._normalise_courts(
                    payload.get("court_preferences"),
                    payload.get("court_number"),
                )
            )
        except ValueError:
            court_preferences = []
        created_at = self._resolve_created_at(payload.get("created_at"))
        user_profile = self._build_user_profile(payload)

        return ReservationRecord(
            request_id=payload.get("id"),
            user=user_profile,
            target_date=target_date,
            target_time=target_time,
            court_preferences=court_preferences,
            created_at=created_at,
            status=payload.get("status", "pending"),
        )

    # ------------------------------------------------------------------
    # Internal helpers
    # ------------------------------------------------------------------
    def _build_user_profile(self, source: Mapping[str, Any]) -> UserProfile:
        t('reservations.queue.request_builder.ReservationRequestBuilder._build_user_profile')
        profile_payload = self._profile_payload(source)
        booking_user = self._booking_user_factory(profile_payload)
        return UserProfile(
            user_id=booking_user.user_id,
            first_name=booking_user.first_name,
            last_name=booking_user.last_name,
            email=booking_user.email,
            phone=booking_user.phone,
            tier=booking_user.tier,
        )

    def _resolve_user(
        self,
        reservation: Mapping[str, Any],
        provided: Optional[Mapping[str, Any]],
    ) -> BookingUser:
        t('reservations.queue.request_builder.ReservationRequestBuilder._resolve_user')
        if provided:
            profile_payload = self._profile_payload(provided)
            return self._booking_user_factory(profile_payload)  # type: ignore[arg-type]

        profile_payload = self._profile_payload(reservation)
        return self._booking_user_factory(profile_payload)

    def _profile_payload(self, source: Mapping[str, Any]) -> Dict[str, Any]:
        t('reservations.queue.request_builder.ReservationRequestBuilder._profile_payload')
        user_id = source.get("user_id") or -1
        first_name = source.get("first_name") or "Queue"
        last_name = source.get("last_name") or "User"
        email = source.get("email") or f"queue-user-{user_id}@example.com"
        phone = source.get("phone") or "000-000-0000"

        return {
            "user_id": user_id,
            "first_name": first_name,
            "last_name": last_name,
            "email": email,
            "phone": phone,
            "tier_name": source.get("tier") or source.get("tier_name"),
        }

    @staticmethod
    def _parse_date(value: Any) -> date:
        t('reservations.queue.request_builder.ReservationRequestBuilder._parse_date')
        if isinstance(value, date) and not isinstance(value, datetime):
            return value
        if isinstance(value, datetime):
            return value.date()
        if isinstance(value, str):
            return datetime.fromisoformat(value).date()
        raise ValueError(f"Unsupported date value: {value!r}")

    @staticmethod
    def _normalise_courts(
        courts: Optional[Sequence[int]],
        fallback: Optional[int],
    ) -> Iterable[int]:
        t('reservations.queue.request_builder.ReservationRequestBuilder._normalise_courts')
        if courts:
            return [int(c) for c in courts if c]
        if fallback is not None:
            return [int(fallback)]
        raise ValueError("Queue reservation must specify at least one court preference")

    @staticmethod
    def _resolve_created_at(value: Any) -> datetime:
        t('reservations.queue.request_builder.ReservationRequestBuilder._resolve_created_at')
        if isinstance(value, datetime):
            return value
        if isinstance(value, str) and value:
            return datetime.fromisoformat(value)
        return datetime.utcnow()

    def _compose_metadata(
        self,
        reservation: Mapping[str, Any],
        target_date: date,
        target_time: str,
        metadata: Optional[Dict[str, Any]],
    ) -> Dict[str, Any]:
        t('reservations.queue.request_builder.ReservationRequestBuilder._compose_metadata')
        extras: Dict[str, Any] = {
            "reservation_id": reservation.get("id"),
            "queue_status": reservation.get("status"),
        }
        if reservation.get("priority") is not None:
            extras["priority"] = reservation.get("priority")
        if reservation.get("waitlist_position") is not None:
            extras["waitlist_position"] = reservation.get("waitlist_position")

        composed = compose_booking_metadata(
            BookingSource.QUEUED,
            target_date,
            target_time,
            extras=extras,
        )
        if metadata:
            composed.update(metadata)
        return composed

    @staticmethod
    def _ensure_fields(
        source: Mapping[str, Any],
        required: Iterable[str],
        label: str,
    ) -> None:
        t('reservations.queue.request_builder.ReservationRequestBuilder._ensure_fields')
        missing = [field for field in required if field not in source]
        if missing:
            raise ValueError(f"{label} missing required fields: {', '.join(sorted(missing))}")


def _default_booking_user_factory(profile: Mapping[str, Any]) -> BookingUser:
    t('reservations.queue.request_builder._default_booking_user_factory')
    from botapp.booking.request_builder import booking_user_from_profile

    return booking_user_from_profile(profile)


DEFAULT_BUILDER = ReservationRequestBuilder()

__all__ = ["ReservationRequestBuilder", "DEFAULT_BUILDER"]
