"""Shared Markdown message builders for queue flows."""

from __future__ import annotations
from tracking import t

from typing import Iterable


class QueueMessageFactory:
    """Produces Markdown strings shared across queue booking flows."""

    _STATIC_MESSAGES = {
        "session_expired": "❌ Session expired. Please start the booking process again.",
        "session_expired_retry": "Session expired. Please try again.",
        "invalid_date": "❌ Invalid date selection received. Please try again.",
        "reservation_details_error": "❌ Error loading reservation details.",
        "reservation_list_error": "❌ Error loading reservations.",
        "reservation_cancelled": (
            "✅ **Reservation Cancelled**\n\n"
            "Your reservation has been cancelled successfully."
        ),
        "modification_prompt": (
            "✏️ **Modify Reservation**\n\n"
            "What would you like to change?"
        ),
        "modification_unavailable": (
            "✏️ **Modify Reservation**\n\n"
            "Modification of confirmed bookings is coming soon!\n\n"
            "For now, you can cancel this reservation and create a new one."
        ),
    }

    SESSION_EXPIRED = _STATIC_MESSAGES["session_expired"]
    SESSION_EXPIRED_RETRY = _STATIC_MESSAGES["session_expired_retry"]
    INVALID_DATE = _STATIC_MESSAGES["invalid_date"]
    RESERVATION_DETAILS_ERROR = _STATIC_MESSAGES["reservation_details_error"]
    RESERVATION_LIST_ERROR = _STATIC_MESSAGES["reservation_list_error"]
    RESERVATION_CANCELLED = _STATIC_MESSAGES["reservation_cancelled"]
    MODIFY_PROMPT = _STATIC_MESSAGES["modification_prompt"]
    MODIFY_UNAVAILABLE = _STATIC_MESSAGES["modification_unavailable"]

    def __getattr__(self, name: str):
        t('botapp.handlers.queue.messages.QueueMessageFactory.__getattr__')
        if name in self._STATIC_MESSAGES:
            return lambda: self._STATIC_MESSAGES[name]
        raise AttributeError(name)

    def profile_incomplete(self, missing_fields: Iterable[str]) -> str:
        """Return profile warning text including missing field names."""
        t('botapp.handlers.queue.messages.QueueMessageFactory.profile_incomplete')

        missing = ", ".join(missing_fields)
        return (
            "❌ **Profile Incomplete**\n\n"
            "Please update your profile before adding a reservation to the queue.\n"
            f"Missing fields: {missing}"
        )

    def time_updated(self, new_time: str) -> str:
        """Return success text for reservation time updates."""
        t('botapp.handlers.queue.messages.QueueMessageFactory.time_updated')

        return (
            "✅ **Time Updated!**\n\n"
            f"Your reservation time has been changed to {new_time}."
        )

    def courts_updated(self, courts_label: str | None = None) -> str:
        """Return success text for reservation court updates."""
        t('botapp.handlers.queue.messages.QueueMessageFactory.courts_updated')

        suffix = (
            f"Your court preferences have been updated to {courts_label}."
            if courts_label
            else "Your court preferences have been updated."
        )
        return "✅ **Courts Updated!**\n\n" + suffix
