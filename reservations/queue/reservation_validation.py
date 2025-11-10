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
    courts: Any = None,
    logger: Any,
) -> None:
    """Raise ``ValueError`` if the user already has a reservation for the slot."""

    t('reservations.queue.reservation_validation.ensure_unique_slot')
    
    def _normalise_courts(raw_value: Any) -> set:
        t('reservations.queue.reservation_validation.ensure_unique_slot._normalise_courts')
        if raw_value is None:
            return set()
        if isinstance(raw_value, (list, tuple, set)):
            return {court for court in raw_value if court is not None}
        return {raw_value}

    requested_courts = _normalise_courts(courts)
    requesting_any_court = not requested_courts

    for existing in reservations:
        if existing.get('user_id') != user_id:
            continue
        if existing.get('status') not in {'pending', 'scheduled', 'attempting'}:
            continue
        existing_date = existing.get('target_date')
        existing_time = existing.get('target_time') or existing.get('time')
        if existing_date != target_date or existing_time != target_time:
            continue

        existing_courts = _normalise_courts(
            existing.get('court_preferences') or existing.get('court_number')
        )
        existing_any_court = not existing_courts

        conflict = (
            existing_any_court
            or requesting_any_court
            or bool(requested_courts & existing_courts)
        )

        if conflict:
            conflicting = requested_courts & existing_courts
            if not conflicting:
                conflicting = existing_courts or requested_courts
            conflict_label = (
                ', '.join(str(court) for court in sorted(conflicting))
                if conflicting else 'this time slot'
            )
            logger.warning(
                """DUPLICATE RESERVATION REJECTED
                User %s already has a reservation for %s at %s on court(s): %s
                Existing reservation ID: %s
                """,
                user_id,
                target_date,
                target_time,
                conflict_label,
                existing.get('id'),
            )
            if conflicting:
                conflict_text = ', '.join(
                    f"Court {court}" for court in sorted(conflicting)
                )
            else:
                conflict_text = "this time slot"
            raise ValueError(
                f"You already have {conflict_text} reserved on {target_date} at {target_time}"
            )
