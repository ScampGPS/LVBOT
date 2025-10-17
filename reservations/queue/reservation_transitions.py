"""State transition helpers for reservation queue entries."""

from __future__ import annotations

from typing import Any, Dict

from tracking import t

def apply_status_update(
    reservation: Dict[str, Any],
    new_status: str,
    **updates: Any,
) -> Dict[str, Any]:
    """Mutate a reservation with a new status and additional fields."""

    t('reservations.queue.reservation_transitions.apply_status_update')
    reservation['status'] = new_status
    for key, value in updates.items():
        reservation[key] = value
    return reservation


def add_to_waitlist(reservation: Dict[str, Any], position: int) -> Dict[str, Any]:
    """Mark a reservation as waitlisted with the provided position."""

    t('reservations.queue.reservation_transitions.add_to_waitlist')
    reservation['status'] = 'waitlisted'
    reservation['waitlist_position'] = position
    reservation['original_position'] = position
    return reservation
