"""Profile management keyboards and messages."""

from __future__ import annotations
from tracking import t

from typing import Any, Dict

from telegram import InlineKeyboardButton, InlineKeyboardMarkup

from .constants import TIER_BADGES


def create_profile_keyboard() -> InlineKeyboardMarkup:
    """Create profile view keyboard with Edit and Back buttons."""

    t('botapp.ui.profile.create_profile_keyboard')
    keyboard = [
        [InlineKeyboardButton("✏️ Edit Profile", callback_data='edit_profile')],
        [InlineKeyboardButton("🔙 Back to Menu", callback_data='back_to_menu')],
    ]
    return InlineKeyboardMarkup(keyboard)


def create_edit_profile_keyboard() -> InlineKeyboardMarkup:
    """Create edit profile menu keyboard."""

    t('botapp.ui.profile.create_edit_profile_keyboard')
    keyboard = [
        [InlineKeyboardButton("👤 Edit Name", callback_data='edit_name')],
        [InlineKeyboardButton("📱 Edit Phone", callback_data='edit_phone')],
        [InlineKeyboardButton("📧 Edit Email", callback_data='edit_email')],
        [InlineKeyboardButton("🔙 Back to Profile", callback_data='menu_profile')],
    ]
    return InlineKeyboardMarkup(keyboard)


def create_cancel_edit_keyboard() -> InlineKeyboardMarkup:
    """Create a cancel button for edit operations."""

    t('botapp.ui.profile.create_cancel_edit_keyboard')
    return InlineKeyboardMarkup([[InlineKeyboardButton("❌ Cancel", callback_data='cancel_edit')]])


def create_phone_keypad() -> InlineKeyboardMarkup:
    """Create numeric keypad for phone number input."""

    t('botapp.ui.profile.create_phone_keypad')
    keyboard = [
        [
            InlineKeyboardButton("1", callback_data='phone_digit_1'),
            InlineKeyboardButton("2", callback_data='phone_digit_2'),
            InlineKeyboardButton("3", callback_data='phone_digit_3'),
        ],
        [
            InlineKeyboardButton("4", callback_data='phone_digit_4'),
            InlineKeyboardButton("5", callback_data='phone_digit_5'),
            InlineKeyboardButton("6", callback_data='phone_digit_6'),
        ],
        [
            InlineKeyboardButton("7", callback_data='phone_digit_7'),
            InlineKeyboardButton("8", callback_data='phone_digit_8'),
            InlineKeyboardButton("9", callback_data='phone_digit_9'),
        ],
        [
            InlineKeyboardButton("⬅️ Delete", callback_data='phone_delete'),
            InlineKeyboardButton("0", callback_data='phone_digit_0'),
            InlineKeyboardButton("✅ Done", callback_data='phone_done'),
        ],
        [InlineKeyboardButton("❌ Cancel", callback_data='cancel_edit')],
    ]
    return InlineKeyboardMarkup(keyboard)


def create_name_type_keyboard() -> InlineKeyboardMarkup:
    """Create keyboard to choose which name to edit."""

    t('botapp.ui.profile.create_name_type_keyboard')
    keyboard = [
        [InlineKeyboardButton("👤 Edit First Name", callback_data='edit_first_name')],
        [InlineKeyboardButton("👥 Edit Last Name", callback_data='edit_last_name')],
        [InlineKeyboardButton("📋 Use Telegram Name", callback_data='name_use_telegram')],
        [InlineKeyboardButton("🔙 Back", callback_data='edit_profile')],
    ]
    return InlineKeyboardMarkup(keyboard)


def create_letter_keyboard() -> InlineKeyboardMarkup:
    """Create keyboard for letter-by-letter name input."""

    t('botapp.ui.profile.create_letter_keyboard')
    letters = [
        ["A", "B", "C", "D", "E", "F"],
        ["G", "H", "I", "J", "K", "L"],
        ["M", "N", "O", "P", "Q", "R"],
        ["S", "T", "U", "V", "W", "X"],
        ["Y", "Z", "-", "'"],
    ]

    keyboard = []
    for row in letters:
        kb_row = []
        for letter in row:
            callback = 'letter_apostrophe' if letter == "'" else f'letter_{letter}'
            kb_row.append(InlineKeyboardButton(letter, callback_data=callback))
        keyboard.append(kb_row)

    keyboard.append(
        [
            InlineKeyboardButton("⬅️ Delete", callback_data='letter_delete'),
            InlineKeyboardButton("✅ Done", callback_data='letter_done'),
        ]
    )
    keyboard.append([InlineKeyboardButton("❌ Cancel", callback_data='cancel_edit')])
    return InlineKeyboardMarkup(keyboard)


def create_email_confirm_keyboard() -> InlineKeyboardMarkup:
    """Create keyboard to confirm email."""

    t('botapp.ui.profile.create_email_confirm_keyboard')
    keyboard = [
        [InlineKeyboardButton("✅ Yes, Save This Email", callback_data='email_confirm')],
        [InlineKeyboardButton("🔄 Try Again", callback_data='edit_email')],
        [InlineKeyboardButton("❌ Cancel", callback_data='cancel_edit')],
    ]
    return InlineKeyboardMarkup(keyboard)


def create_email_char_keyboard() -> InlineKeyboardMarkup:
    """Create keyboard for email character input."""

    t('botapp.ui.profile.create_email_char_keyboard')
    chars = [
        ["a", "b", "c", "d", "e", "f"],
        ["g", "h", "i", "j", "k", "l"],
        ["m", "n", "o", "p", "q", "r"],
        ["s", "t", "u", "v", "w", "x"],
        ["y", "z", "0", "1", "2", "3"],
        ["4", "5", "6", "7", "8", "9"],
        [".", "_", "-", "@"],
    ]

    keyboard = []
    for row in chars:
        keyboard.append(
            [InlineKeyboardButton(char, callback_data=f'email_char_{char}') for char in row]
        )

    keyboard.append(
        [
            InlineKeyboardButton("⬅️ Delete", callback_data='email_delete'),
            InlineKeyboardButton("✅ Done", callback_data='email_done'),
        ]
    )
    keyboard.append([InlineKeyboardButton("❌ Cancel", callback_data='cancel_edit')])
    return InlineKeyboardMarkup(keyboard)


def format_user_profile_message(user_data: Dict[str, Any], is_hardcoded: bool = False) -> str:
    """Format user profile display."""

    t('botapp.ui.profile.format_user_profile_message')
    status_emoji = "✅" if user_data.get('is_active', True) else "🔴"

    phone = user_data.get('phone', 'Not set')
    if phone and phone != 'Not set':
        phone = f"(+502) {phone}"

    message = (
        f"{status_emoji} **User Profile**\n\n"
        f"👤 Name: {user_data.get('first_name', '')} {user_data.get('last_name', '')}\n"
        f"📱 Phone: {phone}\n"
        f"📧 Email: {user_data.get('email', 'Not set')}\n"
        f"🎾 Court Preference: {', '.join([f'Court {c}' for c in user_data.get('court_preference', [])])}\n"
        f"📊 Total Reservations: {user_data.get('total_reservations', 0)}"
    )

    if user_data.get('telegram_username'):
        message += f"\n💬 Telegram: @{user_data['telegram_username']}"

    if is_hardcoded:
        message += "\n\n⚡ *Premium User (Hardcoded)*"

    if user_data.get('is_vip'):
        message += "\n\n⭐ *VIP User* (Priority booking)"

    if user_data.get('is_admin'):
        message += "\n\n👮 *Administrator*"

    return message


def format_user_tier_badge(tier_name: str) -> str:
    """Format user tier into an emoji badge."""

    t('botapp.ui.profile.format_user_tier_badge')
    return TIER_BADGES.get(tier_name, '👤')


__all__ = [
    'create_profile_keyboard',
    'create_edit_profile_keyboard',
    'create_cancel_edit_keyboard',
    'create_phone_keypad',
    'create_name_type_keyboard',
    'create_letter_keyboard',
    'create_email_confirm_keyboard',
    'create_email_char_keyboard',
    'format_user_profile_message',
    'format_user_tier_badge',
]
