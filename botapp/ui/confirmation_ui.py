"""Confirmation UI builders shared across booking flows."""

from __future__ import annotations
from tracking import t

from typing import Any, Dict

from telegram import InlineKeyboardButton, InlineKeyboardMarkup

from botapp.callbacks.parser import CallbackParser


def format_immediate_confirmation_message(booking_data: Dict[str, Any], user_data: Dict[str, Any]) -> str:
    """Compose the confirmation message shown before immediate booking."""
    t('botapp.ui.confirmation_ui.format_immediate_confirmation_message')

    booking_date = booking_data['date']
    formatted_date = booking_date.strftime('%A, %B %d, %Y') if hasattr(booking_date, 'strftime') else str(booking_date)

    first_name = user_data.get('first_name', '').strip()
    last_name = user_data.get('last_name', '').strip()
    full_name = f"{first_name} {last_name}".strip()

    phone = user_data.get('phone', 'Not set')

    return (
        "🎾 **Confirm Immediate Booking**\n\n"
        f"📅 Date: {formatted_date}\n"
        f"⏰ Time: {booking_data['time']}\n"
        f"🎾 Court: {booking_data['court_number']}\n"
        f"👤 Name: {full_name or 'Unknown'}\n"
        f"📱 Phone: {phone or 'Not set'}\n\n"
        "Would you like to book this court now?"
    )


def build_immediate_confirmation_keyboard(
    parser: CallbackParser,
    booking_data: Dict[str, Any],
) -> InlineKeyboardMarkup:
    """Create the inline keyboard for immediate booking confirmation."""
    t('botapp.ui.confirmation_ui.build_immediate_confirmation_keyboard')

    confirm_callback = parser.format_booking_callback(
        'confirm_book',
        booking_data['date'],
        booking_data['court_number'],
        booking_data['time'],
    )

    cancel_callback = parser.format_booking_callback(
        'cancel_book',
        booking_data['date'],
    )

    keyboard = InlineKeyboardMarkup(
        [
            [
                InlineKeyboardButton("✅ Book Now", callback_data=confirm_callback),
                InlineKeyboardButton("❌ Cancel", callback_data=cancel_callback),
            ]
        ]
    )

    return keyboard


def build_immediate_confirmation_ui(
    parser: CallbackParser,
    booking_data: Dict[str, Any],
    user_data: Dict[str, Any],
) -> Dict[str, Any]:
    """Return confirmation message and keyboard for immediate bookings."""
    t('botapp.ui.confirmation_ui.build_immediate_confirmation_ui')

    return {
        'message': format_immediate_confirmation_message(booking_data, user_data),
        'keyboard': build_immediate_confirmation_keyboard(parser, booking_data),
    }


__all__ = [
    'build_immediate_confirmation_keyboard',
    'build_immediate_confirmation_ui',
    'format_immediate_confirmation_message',
]
