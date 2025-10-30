"""Queue booking specific UI formatters."""

from __future__ import annotations
from tracking import t

from datetime import date
from botapp.ui.text_blocks import escape_telegram_markdown, bold_telegram_text


def _md(value: object) -> str:
    """Escape text for Telegram Markdown with special character escaping."""
    return escape_telegram_markdown(value, escape_special_chars=True)


def _bold(value: object) -> str:
    """Return bold Markdown text with proper escaping."""
    return bold_telegram_text(value, escape_special_chars=True)


def format_time_selection_prompt(selected_date: date, availability_note: str | None = None) -> str:
    """Return the message shown before picking a time slot."""

    t('botapp.ui.queue.format_time_selection_prompt')
    lines = [
        f"⏰ {_bold('Queue Booking')}",
        "",
        f"📅 Selected Date: {_md(selected_date.strftime('%A, %B %d, %Y'))}",
        "",
        _md("⏱️ Select a time for your queued reservation:"),
    ]
    if availability_note:
        lines.append(_md(availability_note))
    return "\n".join(lines)


def format_no_time_slots_message(selected_date: date) -> str:
    """Return the message shown when no time slots remain."""

    t('botapp.ui.queue.format_no_time_slots_message')
    return "\n".join(
        [
            f"⚠️ {_bold('No time slots available')}",
            "",
            f"📅 Date: {_md(selected_date.strftime('%A, %B %d, %Y'))}",
            "",
            _md("All time slots on this date are within 48 hours."),
            _md("Please select a later date for queue booking."),
        ]
    )


def format_confirmation_message(selected_date: date, selected_time: str, courts_text: str) -> str:
    """Return the queue confirmation summary shown before enqueueing."""

    t('botapp.ui.queue.format_confirmation_message')
    lines = [
        f"⏰ {_bold('Queue Booking Confirmation')}",
        "",
        f"📅 Date: {_md(selected_date.strftime('%A, %B %d, %Y'))}",
        f"⏱️ Time: {_md(selected_time)}",
        f"🎾 Courts: {_md(courts_text)}",
        "",
        _md(
            "🤖 This reservation will be queued and automatically booked when the booking window opens."
        ),
        "",
        _bold("Confirm to add this reservation to your queue?"),
    ]
    return "\n".join(lines)


def format_cancellation_message() -> str:
    """Return the user-facing cancellation message."""

    t('botapp.ui.queue.format_cancellation_message')
    return "\n".join(
        [
            f"❌ {_bold('Queue Booking Cancelled')}",
            "",
            _md(
                "Your reservation request has been cancelled. No changes have been made to your queue."
            ),
            "",
            _md("You can start a new booking anytime using the main menu."),
        ]
    )


def format_court_selection_prompt(selected_date: date, selected_time: str) -> str:
    """Return the prompt shown before choosing preferred courts."""

    t('botapp.ui.queue.format_court_selection_prompt')
    lines = [
        f"⏰ {_bold('Queue Booking')}",
        "",
        f"📅 Date: {_md(selected_date.strftime('%A, %B %d, %Y'))}",
        f"⏱️ Time: {_md(selected_time)}",
        "",
        _md("🎾 Select your preferred court(s) for the reservation:"),
    ]
    return "\n".join(lines)
