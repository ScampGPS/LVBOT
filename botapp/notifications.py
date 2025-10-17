"""Notification helpers that operate on shared booking results."""

from __future__ import annotations

import asyncio
from datetime import datetime
from typing import Dict, Sequence

from tracking import t

from automation.shared.booking_contracts import BookingResult
from botapp.ui.telegram_ui import TelegramUI


SUCCESS_HEADER = "✅ *Booking Confirmed!*"
FAILURE_HEADER = "❌ *Booking Attempt Failed*"


def format_success_message(result: BookingResult) -> str:
    """Generate a Markdown-formatted success message."""

    lines = [SUCCESS_HEADER]
    if result.court_reserved:
        lines.append(f"• Court: {result.court_reserved}")
    if result.time_reserved:
        lines.append(f"• Time: {result.time_reserved}")
    if result.confirmation_code:
        lines.append(f"• Confirmation: `{result.confirmation_code}`")
    if result.confirmation_url:
        lines.append(f"[View Confirmation]({result.confirmation_url})")
    if result.message:
        lines.append("")
        lines.append(result.message)
    return "\n".join(lines)


def format_failure_message(result: BookingResult) -> str:
    """Generate a Markdown-formatted failure message with error context."""

    lines = [FAILURE_HEADER]
    if result.message:
        lines.append(result.message)
    if result.errors:
        lines.append("")
        lines.extend(f"• {error}" for error in result.errors)
    return "\n".join(lines)


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
    test_mode_enabled: bool,
    test_mode_delay_minutes: int,
) -> str:
    """Build the confirmation message when a queue reservation is added."""

    display_date = datetime.strptime(booking_summary['target_date'], '%Y-%m-%d').strftime('%A, %B %d, %Y')
    courts = booking_summary.get('court_preferences', [])

    if isinstance(courts, str) and courts == 'all':
        courts_label = "All Courts"
    else:
        court_values: Sequence[int] = courts if isinstance(courts, Sequence) else []
        courts_label = ', '.join(f"Court {court}" for court in sorted(court_values)) or "All Courts"

    message_lines = [
        "✅ **Reservation Added to Queue!**",
        "",
        f"📅 Date: {display_date}",
        f"⏱️ Time: {booking_summary['target_time']}",
        f"🎾 Courts: {courts_label}",
        "",
        f"🤖 **Queue ID:** {reservation_id[:8]}...",
        "",
    ]

    if test_mode_enabled:
        message_lines.extend(
            [
                "🧪 **TEST MODE ACTIVE**",
                f"This reservation will be executed in {test_mode_delay_minutes} minutes!",
                "",
            ]
        )
    else:
        message_lines.extend(
            [
                "Your reservation has been successfully added to the queue. The bot will automatically attempt to book this court when the booking window opens.",
                "",
            ]
        )

    message_lines.append(
        "You can view your queued reservations anytime using the **'My Reservations'** option."
    )

    return "\n".join(message_lines)


def format_duplicate_reservation_message(error_message: str) -> str:
    """Build a user-friendly duplicate reservation warning message."""

    return "\n".join(
        [
            "⚠️ **Duplicate Reservation**",
            "",
            error_message,
            "",
            "You can only have one reservation per time slot. Please check your existing reservations or choose a different time.",
        ]
    )


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

    t('botapp.notifications.deliver_notification_with_menu')

    if not application:
        logger.warning("No application context for notification to %s", user_id)
        return

    await application.bot.send_message(chat_id=user_id, text=message, parse_mode='Markdown')
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
