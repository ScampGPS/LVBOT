"""Validation helpers for reservation queue operations."""

from __future__ import annotations

from typing import Any, Dict, Iterable

from tracking import t


def ensure_unique_slot(
    reservations: Iterable[Dict[str, Any]],
    *,
    user_id: Any,
    target_date: Any,
    target_time: Any,
    logger: Any,
) -> None:
    """Raise ``ValueError`` if the user already has a reservation for the slot."""

    t('reservations.queue.reservation_validation.ensure_unique_slot')
    for existing in reservations:
        if existing.get('user_id') != user_id:
            continue
        if existing.get('status') not in {'pending', 'scheduled', 'attempting'}:
            continue
        existing_date = existing.get('target_date')
        existing_time = existing.get('target_time') or existing.get('time')
        if existing_date == target_date and existing_time == target_time:
            logger.warning(
                """DUPLICATE RESERVATION REJECTED
                User %s already has a reservation for %s at %s
                Existing reservation ID: %s
                """,
                user_id,
                target_date,
                target_time,
                existing.get('id'),
            )
            raise ValueError(
                f"You already have a reservation for {target_date} at {target_time}"
            )
