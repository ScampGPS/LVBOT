"""Profile management keyboards and messages."""

from __future__ import annotations
from tracking import t

from typing import Any, Dict

from telegram import InlineKeyboardButton, InlineKeyboardMarkup

from .constants import TIER_BADGES
from .text_blocks import MarkdownBlockBuilder, MarkdownBuilderBase


def _keyboard(rows: list[list[tuple[str, str]]]) -> InlineKeyboardMarkup:
    return InlineKeyboardMarkup(
        [
            [InlineKeyboardButton(text, callback_data=callback) for text, callback in row]
            for row in rows
        ]
    )


def create_profile_keyboard() -> InlineKeyboardMarkup:
    """Create profile view keyboard with Edit and Back buttons."""

    t("botapp.ui.profile.create_profile_keyboard")
    return _keyboard(
        [
            [("✏️ Edit Profile", "edit_profile")],
            [("🔙 Back to Menu", "back_to_menu")],
        ]
    )


def create_edit_profile_keyboard() -> InlineKeyboardMarkup:
    """Create edit profile menu keyboard."""

    t("botapp.ui.profile.create_edit_profile_keyboard")
    return _keyboard(
        [
            [("👤 Edit Name", "edit_name")],
            [("📱 Edit Phone", "edit_phone")],
            [("📧 Edit Email", "edit_email")],
            [("🔙 Back to Profile", "menu_profile")],
        ]
    )


def create_cancel_edit_keyboard() -> InlineKeyboardMarkup:
    """Create a cancel button for edit operations."""

    t("botapp.ui.profile.create_cancel_edit_keyboard")
    return _keyboard(
        [[("❌ Cancel", "cancel_edit")]]
    )


def create_phone_keypad() -> InlineKeyboardMarkup:
    """Create numeric keypad for phone number input."""

    t("botapp.ui.profile.create_phone_keypad")
    rows = [
        [("1", "phone_digit_1"), ("2", "phone_digit_2"), ("3", "phone_digit_3")],
        [("4", "phone_digit_4"), ("5", "phone_digit_5"), ("6", "phone_digit_6")],
        [("7", "phone_digit_7"), ("8", "phone_digit_8"), ("9", "phone_digit_9")],
        [("⬅️ Delete", "phone_delete"), ("0", "phone_digit_0"), ("✅ Done", "phone_done")],
        [("❌ Cancel", "cancel_edit")],
    ]
    return _keyboard(rows)


def create_name_type_keyboard() -> InlineKeyboardMarkup:
    """Create keyboard to choose which name to edit."""

    t("botapp.ui.profile.create_name_type_keyboard")
    return _keyboard(
        [
            [("👤 Edit First Name", "edit_first_name")],
            [("👥 Edit Last Name", "edit_last_name")],
            [("📋 Use Telegram Name", "name_use_telegram")],
            [("🔙 Back", "edit_profile")],
        ]
    )


def create_letter_keyboard() -> InlineKeyboardMarkup:
    """Create keyboard for letter-by-letter name input."""

    t("botapp.ui.profile.create_letter_keyboard")
    letters = [
        ["A", "B", "C", "D", "E", "F"],
        ["G", "H", "I", "J", "K", "L"],
        ["M", "N", "O", "P", "Q", "R"],
        ["S", "T", "U", "V", "W", "X"],
        ["Y", "Z", "-", "'"],
    ]

    rows = [
        [
            (letter, "letter_apostrophe" if letter == "'" else f"letter_{letter}")
            for letter in row
        ]
        for row in letters
    ]
    rows.append([("⬅️ Delete", "letter_delete"), ("✅ Done", "letter_done")])
    rows.append([("❌ Cancel", "cancel_edit")])
    return _keyboard(rows)


def create_email_confirm_keyboard() -> InlineKeyboardMarkup:
    """Create keyboard to confirm email."""

    t("botapp.ui.profile.create_email_confirm_keyboard")
    return _keyboard(
        [
            [("✅ Yes, Save This Email", "email_confirm")],
            [("🔄 Try Again", "edit_email")],
            [("❌ Cancel", "cancel_edit")],
        ]
    )


def create_email_char_keyboard() -> InlineKeyboardMarkup:
    """Create keyboard for email character input."""

    t("botapp.ui.profile.create_email_char_keyboard")
    chars = [
        ["a", "b", "c", "d", "e", "f"],
        ["g", "h", "i", "j", "k", "l"],
        ["m", "n", "o", "p", "q", "r"],
        ["s", "t", "u", "v", "w", "x"],
        ["y", "z", "0", "1", "2", "3"],
        ["4", "5", "6", "7", "8", "9"],
        [".", "_", "-", "@"],
    ]

    rows = [
        [(char, f"email_char_{char}") for char in row]
        for row in chars
    ]
    rows.append([("⬅️ Delete", "email_delete"), ("✅ Done", "email_done")])
    rows.append([("❌ Cancel", "cancel_edit")])
    return _keyboard(rows)


def format_user_profile_message(
    user_data: Dict[str, Any], is_hardcoded: bool = False
) -> str:
    """Format user profile display."""

    t("botapp.ui.profile.format_user_profile_message")
    return ProfileViewBuilder().build(user_data, is_hardcoded=is_hardcoded)


def format_user_tier_badge(tier_name: str) -> str:
    """Format user tier into an emoji badge."""

    t("botapp.ui.profile.format_user_tier_badge")
    return TIER_BADGES.get(tier_name, "👤")


__all__ = [
    "create_profile_keyboard",
    "create_edit_profile_keyboard",
    "create_cancel_edit_keyboard",
    "create_phone_keypad",
    "create_name_type_keyboard",
    "create_letter_keyboard",
    "create_email_confirm_keyboard",
    "create_email_char_keyboard",
    "format_user_profile_message",
    "format_user_tier_badge",
    "ProfileViewBuilder",
]


class ProfileViewBuilder(MarkdownBuilderBase):
    """Compose the user profile view using shared Markdown helpers."""

    def __init__(self, builder_factory=MarkdownBlockBuilder) -> None:
        t("botapp.ui.profile.ProfileViewBuilder.__init__")
        super().__init__(builder_factory=builder_factory)

    def build(self, user_data: Dict[str, Any], *, is_hardcoded: bool = False) -> str:
        t("botapp.ui.profile.ProfileViewBuilder.build")

        builder = self.create_builder()
        status_emoji = "✅" if user_data.get("is_active", True) else "🔴"

        phone = user_data.get("phone", "Not set")
        if phone and phone != "Not set":
            phone = f"(+502) {phone}"

        builder.heading(f"{status_emoji} **User Profile**").blank()
        builder.line(
            f"👤 Name: {user_data.get('first_name', '')} {user_data.get('last_name', '')}"
        )
        builder.line(f"📱 Phone: {phone}")
        builder.line(f"📧 Email: {user_data.get('email', 'Not set')}")

        court_pref = user_data.get("court_preference", []) or []
        if court_pref:
            courts_text = ", ".join([f"Court {c}" for c in court_pref])
        else:
            courts_text = "Not set"
        builder.line(f"🎾 Court Preference: {courts_text}")
        builder.line(f"📊 Total Reservations: {user_data.get('total_reservations', 0)}")

        if user_data.get("telegram_username"):
            builder.line(f"💬 Telegram: @{user_data['telegram_username']}")

        extras = []
        if is_hardcoded:
            extras.append("⚡ *Premium User (Hardcoded)*")
        if user_data.get("is_vip"):
            extras.append("⭐ *VIP User* (Priority booking)")
        if user_data.get("is_admin"):
            extras.append("👮 *Administrator*")

        if extras:
            for extra in extras:
                builder.blank().line(extra)

        return builder.build()
