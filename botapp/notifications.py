"""Notification helpers that operate on shared booking results."""

from __future__ import annotations

import asyncio
from datetime import datetime
from typing import Dict, Sequence

from tracking import t

from automation.shared.booking_contracts import BookingResult
from botapp.ui.telegram_ui import TelegramUI
from botapp.ui.text_blocks import MarkdownBlockBuilder, MarkdownBuilderBase
from infrastructure.settings import TestModeConfig
from telegram.helpers import escape_markdown
from telegram import InlineKeyboardButton, InlineKeyboardMarkup

SUCCESS_HEADER = "✅ *Booking Confirmed!*"
FAILURE_HEADER = "❌ *Booking Attempt Failed*"


def _md(text: object) -> str:
    """Escape text for Telegram Markdown."""

    return escape_markdown(str(text))


def _bold(text: object) -> str:
    """Return bold Markdown text."""

    return f"*{_md(text)}*"


class NotificationBuilder(MarkdownBuilderBase):
    """Build common booking notifications with shared Markdown formatting."""

    def __init__(self, builder_factory=MarkdownBlockBuilder) -> None:
        super().__init__(builder_factory=builder_factory)

    def success_message(self, result: BookingResult) -> str:
        builder = self.create_builder().heading(SUCCESS_HEADER)

        if result.court_reserved:
            builder.bullet(f"Court: {result.court_reserved}")
        if result.time_reserved:
            builder.bullet(f"Time: {result.time_reserved}")
        if result.confirmation_code:
            builder.bullet(f"Confirmation: `{result.confirmation_code}`")

        if result.message:
            builder.blank().line(result.message)

        # Note: Calendar links are now shown as inline buttons instead of text links
        builder.blank().line("Use the buttons below to add to your calendar or manage your reservation.")

        return builder.build()

    def failure_message(self, result: BookingResult) -> str:
        builder = self.create_builder().heading(FAILURE_HEADER)

        if result.message:
            builder.line(result.message)
        if result.errors:
            builder.blank().bullets(result.errors)

        return builder.build()

    def duplicate_warning(self, error_message: str) -> str:
        lines = [
            f"⚠️ {_bold('Duplicate Reservation')}",
            "",
            _md(error_message),
            "",
            _md(
                "You can only have one reservation per time slot. Please check your existing reservations or choose a different time."
            ),
        ]
        return "\n".join(lines)

    def queue_reservation_added(
        self,
        booking_summary: Dict[str, object],
        reservation_id: str,
        *,
        test_mode_config: TestModeConfig,
    ) -> str:
        display_date = datetime.strptime(
            booking_summary["target_date"], "%Y-%m-%d"
        ).strftime("%A, %B %d, %Y")
        courts = booking_summary.get("court_preferences", [])

        if isinstance(courts, str) and courts == "all":
            courts_label = "All Courts"
        else:
            court_values: Sequence[int] = courts if isinstance(courts, Sequence) else []
            courts_label = (
                ", ".join(f"Court {court}" for court in sorted(court_values))
                or "All Courts"
            )

        lines = [
            f"✅ {_bold('Reservation Added to Queue!')}",
            "",
            f"📅 Date: {_md(display_date)}",
            f"⏱️ Time: {_md(booking_summary['target_time'])}",
            f"🎾 Courts: {_md(courts_label)}",
            "",
            f"🤖 {_bold('Queue ID:')} {_md(reservation_id[:8] + '...')}",
            "",
        ]

        if test_mode_config.enabled:
            lines.append(_bold("TEST MODE ACTIVE"))
            lines.append(
                _md(
                    f"This reservation will be executed in {test_mode_config.trigger_delay_minutes} minutes!"
                )
            )
            lines.append("")
        else:
            lines.append(
                _md(
                    "Your reservation has been successfully added to the queue. The bot will automatically attempt to book this court when the booking window opens."
                )
            )
            lines.append("")

        lines.append(
            _md("You can view your queued reservations anytime using the My Reservations option.")
        )

        return "\n".join(lines)


_NOTIFICATIONS = NotificationBuilder()


def _format_notification(method_name: str, doc: str):
    def _format(result: BookingResult) -> str:
        builder_method = getattr(_NOTIFICATIONS, method_name)
        return builder_method(result)

    _format.__name__ = f"format_{method_name}"
    _format.__doc__ = doc
    return _format


format_success_message = _format_notification(
    "success_message",
    "Generate a Markdown-formatted success message.",
)

format_failure_message = _format_notification(
    "failure_message",
    "Generate a Markdown-formatted failure message with error context.",
)


def _send_notification(
    formatter,
    user_id: int,
    result: BookingResult,
) -> Dict[str, object]:
    # Build inline keyboard with calendar links and cancel button
    keyboard = []

    # Extract links from metadata
    google_calendar_link = result.metadata.get("google_calendar_link")
    ics_calendar_link = result.metadata.get("ics_calendar_link")
    cancel_modify_link = result.metadata.get("cancel_modify_link")

    # Add calendar buttons (first row)
    calendar_row = []
    if google_calendar_link:
        calendar_row.append(InlineKeyboardButton("📅 Google Calendar", url=google_calendar_link))
    if ics_calendar_link:
        calendar_row.append(InlineKeyboardButton("📆 Outlook/iCal", url=ics_calendar_link))
    if calendar_row:
        keyboard.append(calendar_row)

    # Add cancel/modify button (second row) - special interactive button
    if cancel_modify_link and result.request_id:
        keyboard.append([
            InlineKeyboardButton(
                "🗑️ Cancel Reservation",
                callback_data=f"cancel_reservation:{result.request_id}"
            )
        ])

    # Create inline keyboard markup if we have buttons
    reply_markup = InlineKeyboardMarkup(keyboard) if keyboard else TelegramUI.create_back_to_menu_keyboard()

    return {
        "user_id": user_id,
        "message": formatter(result),
        "parse_mode": "Markdown",
        "reply_markup": reply_markup,
    }


def send_success_notification(user_id: int, result: BookingResult) -> Dict[str, object]:
    """Prepare payload for delivering a success notification to Telegram."""

    return _send_notification(format_success_message, user_id, result)


def send_failure_notification(user_id: int, result: BookingResult) -> Dict[str, object]:
    """Prepare payload for delivering a failure notification to Telegram."""

    return _send_notification(format_failure_message, user_id, result)


def format_queue_reservation_added(
    booking_summary: Dict[str, object],
    reservation_id: str,
    *,
    test_mode_config: TestModeConfig,
) -> str:
    """Build the confirmation message when a queue reservation is added."""

    return _NOTIFICATIONS.queue_reservation_added(
        booking_summary,
        reservation_id,
        test_mode_config=test_mode_config,
    )


def format_duplicate_reservation_message(error_message: str) -> str:
    """Build a user-friendly duplicate reservation warning message."""

    return _NOTIFICATIONS.duplicate_warning(error_message)


async def deliver_notification_with_menu(
    application,
    user_manager,
    user_id: int,
    message: str,
    *,
    logger,
    follow_up_delay_seconds: int = 7,
) -> None:
    """Send a notification and optionally follow up with the main menu."""

    t("botapp.notifications.deliver_notification_with_menu")

    if not application:
        logger.warning("No application context for notification to %s", user_id)
        return

    await application.bot.send_message(
        chat_id=user_id, text=message, parse_mode="Markdown"
    )
    logger.info("Sent notification to %s: %s", user_id, message[:50])

    def _looks_like_booking_result(text: str) -> bool:
        lower_text = text.lower()
        return (
            ("✅" in text and ("reservation" in lower_text or "booked" in lower_text))
            or ("❌" in text and "reservation" in lower_text)
            or ("⚠️" in text and "booking" in lower_text)
        )

    if not _looks_like_booking_result(message):
        return

    await asyncio.sleep(max(0, follow_up_delay_seconds))

    is_admin = user_manager.is_admin(user_id)
    tier = user_manager.get_user_tier(user_id)
    tier_badge = TelegramUI.format_user_tier_badge(tier.name)

    reply_markup = TelegramUI.create_main_menu_keyboard(is_admin=is_admin)
    await application.bot.send_message(
        chat_id=user_id,
        text=f"🎾 What would you like to do next? {tier_badge}",
        reply_markup=reply_markup,
    )
    logger.info("Sent main menu follow-up to %s", user_id)


__all__ = [
    "NotificationBuilder",
    "format_success_message",
    "format_failure_message",
    "send_success_notification",
    "send_failure_notification",
    "format_queue_reservation_added",
    "format_duplicate_reservation_message",
    "deliver_notification_with_menu",
]
