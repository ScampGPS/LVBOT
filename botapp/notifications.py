"""Notification helpers that operate on shared booking results."""

from __future__ import annotations

import asyncio
from datetime import datetime
from typing import Dict, Sequence

from tracking import t

from automation.shared.booking_contracts import BookingResult
from botapp.ui.telegram_ui import TelegramUI
from botapp.ui.text_blocks import MarkdownBlockBuilder
from infrastructure.settings import TestModeConfig

SUCCESS_HEADER = "✅ *Booking Confirmed!*"
FAILURE_HEADER = "❌ *Booking Attempt Failed*"


class NotificationBuilder:
    """Build common booking notifications with shared Markdown formatting."""

    def __init__(self, builder_factory=MarkdownBlockBuilder) -> None:
        self._builder_factory = builder_factory

    def success_message(self, result: BookingResult) -> str:
        builder = self._builder_factory().heading(SUCCESS_HEADER)

        if result.court_reserved:
            builder.bullet(f"Court: {result.court_reserved}")
        if result.time_reserved:
            builder.bullet(f"Time: {result.time_reserved}")
        if result.confirmation_code:
            builder.bullet(f"Confirmation: `{result.confirmation_code}`")
        if result.confirmation_url:
            builder.line(f"[View Confirmation]({result.confirmation_url})")
        if result.message:
            builder.blank().line(result.message)

        return builder.build()

    def failure_message(self, result: BookingResult) -> str:
        builder = self._builder_factory().heading(FAILURE_HEADER)

        if result.message:
            builder.line(result.message)
        if result.errors:
            builder.blank().bullets(result.errors)

        return builder.build()

    def duplicate_warning(self, error_message: str) -> str:
        builder = self._builder_factory().heading("⚠️ **Duplicate Reservation**")
        builder.blank().line(error_message).blank()
        builder.line(
            "You can only have one reservation per time slot. "
            "Please check your existing reservations or choose a different time."
        )
        return builder.build()

    def queue_reservation_added(
        self,
        booking_summary: Dict[str, object],
        reservation_id: str,
        *,
        test_mode_config: TestModeConfig,
    ) -> str:
        builder = self._builder_factory().heading("✅ **Reservation Added to Queue!**")
        builder.blank()

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

        builder.line(f"📅 Date: {display_date}")
        builder.line(f"⏱️ Time: {booking_summary['target_time']}")
        builder.line(f"🎾 Courts: {courts_label}")
        builder.blank()
        builder.line(f"🤖 **Queue ID:** {reservation_id[:8]}...")
        builder.blank()

        if test_mode_config.enabled:
            builder.line("🧪 **TEST MODE ACTIVE**")
            builder.line(
                f"This reservation will be executed in {test_mode_config.trigger_delay_minutes} minutes!"
            )
            builder.blank()
        else:
            builder.line(
                "Your reservation has been successfully added to the queue. "
                "The bot will automatically attempt to book this court when the booking window opens."
            )
            builder.blank()

        builder.line(
            "You can view your queued reservations anytime using the **'My Reservations'** option."
        )

        return builder.build()


_NOTIFICATIONS = NotificationBuilder()


def format_success_message(result: BookingResult) -> str:
    """Generate a Markdown-formatted success message."""

    return _NOTIFICATIONS.success_message(result)


def format_failure_message(result: BookingResult) -> str:
    """Generate a Markdown-formatted failure message with error context."""

    return _NOTIFICATIONS.failure_message(result)


def send_success_notification(user_id: int, result: BookingResult) -> Dict[str, object]:
    """Prepare payload for delivering a success notification to Telegram."""

    return {
        "user_id": user_id,
        "message": format_success_message(result),
        "parse_mode": "Markdown",
        "reply_markup": TelegramUI.create_back_to_menu_keyboard(),
    }


def send_failure_notification(user_id: int, result: BookingResult) -> Dict[str, object]:
    """Prepare payload for delivering a failure notification to Telegram."""

    return {
        "user_id": user_id,
        "message": format_failure_message(result),
        "parse_mode": "Markdown",
        "reply_markup": TelegramUI.create_back_to_menu_keyboard(),
    }


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
