"""Queue booking specific UI formatters."""

from __future__ import annotations
from tracking import t

from datetime import date


def format_time_selection_prompt(selected_date: date, availability_note: str) -> str:
    """Return the message shown before picking a time slot."""

    t('botapp.ui.queue.format_time_selection_prompt')
    return (
        "⏰ **Queue Booking**\n\n"
        f"📅 Selected Date: {selected_date.strftime('%A, %B %d, %Y')}\n\n"
        "⏱️ Select a time for your queued reservation:\n"
        f"{availability_note}"
    )


def format_no_time_slots_message(selected_date: date) -> str:
    """Return the message shown when no time slots remain."""

    t('botapp.ui.queue.format_no_time_slots_message')
    return (
        "⚠️ **No time slots available**\n\n"
        f"📅 Date: {selected_date.strftime('%A, %B %d, %Y')}\n\n"
        "All time slots on this date are within 48 hours.\n"
        "Please select a later date for queue booking."
    )


def format_confirmation_message(selected_date: date, selected_time: str, courts_text: str) -> str:
    """Return the queue confirmation summary shown before enqueueing."""

    t('botapp.ui.queue.format_confirmation_message')
    return (
        "⏰ **Queue Booking Confirmation**\n\n"
        f"📅 Date: {selected_date.strftime('%A, %B %d, %Y')}\n"
        f"⏱️ Time: {selected_time}\n"
        f"🎾 Courts: {courts_text}\n\n"
        "🤖 This reservation will be queued and automatically booked when the booking window opens.\n\n"
        "**Confirm to add this reservation to your queue?**"
    )


def format_cancellation_message() -> str:
    """Return the user-facing cancellation message."""

    t('botapp.ui.queue.format_cancellation_message')
    return (
        "❌ **Queue Booking Cancelled**\n\n"
        "Your reservation request has been cancelled. "
        "No changes have been made to your queue.\n\n"
        "You can start a new booking anytime using the main menu."
    )

