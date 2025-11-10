"""Builders for converting bot payloads into booking contracts."""

from __future__ import annotations
from tracking import t

from datetime import date
from typing import Any, Dict, Optional

from automation.shared.booking_contracts import (
    BookingRequest,
    BookingSource,
    BookingUser,
    compose_booking_metadata,
)

REQUIRED_USER_FIELDS = {"user_id", "first_name", "last_name", "email", "phone"}


def booking_user_from_profile(user_profile: Dict[str, Any]) -> BookingUser:
    """Translate a user_manager profile dict into a `BookingUser`."""
    t('botapp.booking.request_builder.booking_user_from_profile')

    missing = [field for field in REQUIRED_USER_FIELDS if not user_profile.get(field)]
    if missing:
        raise ValueError(f"User profile missing required fields: {', '.join(missing)}")

    return BookingUser(
        user_id=int(user_profile["user_id"]),
        first_name=str(user_profile["first_name"]).strip(),
        last_name=str(user_profile["last_name"]).strip(),
        email=str(user_profile["email"]).strip(),
        phone=str(user_profile["phone"]).strip(),
        tier=user_profile.get("tier_name") or user_profile.get("tier"),
    )


def build_immediate_booking_request(
    user_profile: Dict[str, Any],
    *,
    target_date: date,
    time_slot: str,
    court_number: int,
    metadata: Optional[Dict[str, Any]] = None,
    executor_config: Optional[Dict[str, Any]] = None,
) -> BookingRequest:
    """Construct a `BookingRequest` for immediate Telegram-triggered bookings."""
    t('botapp.booking.request_builder.build_immediate_booking_request')

    user = booking_user_from_profile(user_profile)
    base_metadata: Dict[str, Any] = compose_booking_metadata(
        BookingSource.IMMEDIATE,
        target_date,
        time_slot,
        extras={"court_number": court_number},
    )
    if metadata:
        base_metadata.update(metadata)

    return BookingRequest.from_immediate_payload(
        user=user,
        target_date=target_date,
        time_slot=time_slot,
        court_number=court_number,
        metadata=base_metadata,
        executor_config=executor_config,
    )


def build_admin_booking_request(
    user_profile: Dict[str, Any],
    *,
    target_date: date,
    time_slot: str,
    courts: Optional[Any] = None,
    request_id: Optional[str] = None,
    metadata: Optional[Dict[str, Any]] = None,
    executor_config: Optional[Dict[str, Any]] = None,
) -> BookingRequest:
    """Construct a booking request for admin-triggered overrides."""
    t('botapp.booking.request_builder.build_admin_booking_request')

    user = booking_user_from_profile(user_profile)
    courts_list = list(courts or [])
    if not courts_list:
        raise ValueError("Admin booking requires at least one court")

    meta = {
        "source": BookingSource.ADMIN.value,
        "target_date": target_date.isoformat(),
        "target_time": time_slot,
    }
    if metadata:
        meta.update(metadata)

    return BookingRequest.from_reservation_record(
        request_id=request_id or f"admin-{user.user_id}-{target_date.isoformat()}-{time_slot}",
        user=user,
        target_date=target_date,
        target_time=time_slot,
        courts=courts_list,
        source=BookingSource.ADMIN,
        metadata=meta,
        executor_config=executor_config,
    )

