"""Notification helpers that operate on shared booking results."""

from __future__ import annotations

from typing import Dict

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

