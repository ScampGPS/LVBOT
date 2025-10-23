"""Shared Markdown message builders for queue flows."""

from __future__ import annotations

from typing import Iterable


class QueueMessageFactory:
    """Produces Markdown strings shared across queue booking flows."""

    SESSION_EXPIRED = "❌ Session expired. Please start the booking process again."
    SESSION_EXPIRED_RETRY = "Session expired. Please try again."
    INVALID_DATE = "❌ Invalid date selection received. Please try again."
    RESERVATION_DETAILS_ERROR = "❌ Error loading reservation details."
    RESERVATION_LIST_ERROR = "❌ Error loading reservations."
    RESERVATION_CANCELLED = (
        "✅ **Reservation Cancelled**\n\n"
        "Your reservation has been cancelled successfully."
    )
    MODIFY_PROMPT = (
        "✏️ **Modify Reservation**\n\n"
        "What would you like to change?"
    )
    MODIFY_UNAVAILABLE = (
        "✏️ **Modify Reservation**\n\n"
        "Modification of confirmed bookings is coming soon!\n\n"
        "For now, you can cancel this reservation and create a new one."
    )

    def session_expired(self) -> str:
        """Return the standard session expired copy."""

        return self.SESSION_EXPIRED

    def session_expired_retry(self) -> str:
        """Return the shorter retry variant used for inline answers."""

        return self.SESSION_EXPIRED_RETRY

    def invalid_date(self) -> str:
        """Return invalid date selection copy."""

        return self.INVALID_DATE

    def profile_incomplete(self, missing_fields: Iterable[str]) -> str:
        """Return profile warning text including missing field names."""

        missing = ", ".join(missing_fields)
        return (
            "❌ **Profile Incomplete**\n\n"
            "Please update your profile before adding a reservation to the queue.\n"
            f"Missing fields: {missing}"
        )

    def reservation_details_error(self) -> str:
        """Return error text when specific reservation details cannot be loaded."""

        return self.RESERVATION_DETAILS_ERROR

    def reservation_list_error(self) -> str:
        """Return error text when the reservation list cannot be loaded."""

        return self.RESERVATION_LIST_ERROR

    def reservation_cancelled(self) -> str:
        """Return confirmation copy for cancelled reservations."""

        return self.RESERVATION_CANCELLED

    def modification_prompt(self) -> str:
        """Return the modification menu prompt."""

        return self.MODIFY_PROMPT

    def modification_unavailable(self) -> str:
        """Return copy for reservations that cannot be modified."""

        return self.MODIFY_UNAVAILABLE

    def time_updated(self, new_time: str) -> str:
        """Return success text for reservation time updates."""

        return (
            "✅ **Time Updated!**\n\n"
            f"Your reservation time has been changed to {new_time}."
        )

    def courts_updated(self, courts_label: str | None = None) -> str:
        """Return success text for reservation court updates."""

        suffix = (
            f"Your court preferences have been updated to {courts_label}."
            if courts_label
            else "Your court preferences have been updated."
        )
        return "✅ **Courts Updated!**\n\n" + suffix
