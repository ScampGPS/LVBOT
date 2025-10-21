"""Admin-specific Telegram UI helpers."""

from __future__ import annotations
from tracking import t

from telegram import InlineKeyboardButton, InlineKeyboardMarkup


def create_admin_menu_keyboard(
    pending_count: int = 0,
    *,
    test_mode_enabled: bool = False,
) -> InlineKeyboardMarkup:
    """Create the admin menu keyboard."""

    t('botapp.ui.admin.create_admin_menu_keyboard')
    test_label = "🧪 Test Mode: ON" if test_mode_enabled else "🧪 Test Mode: OFF"

    keyboard = [
        [InlineKeyboardButton(test_label, callback_data='admin_toggle_test_mode')],
        [
            InlineKeyboardButton(f"🆕 Pending ({pending_count})", callback_data='admin_pending'),
            InlineKeyboardButton("👥 All Users", callback_data='admin_users'),
        ],
        [
            InlineKeyboardButton("📊 Stats", callback_data='admin_stats'),
            InlineKeyboardButton("⚙️ Settings", callback_data='admin_settings'),
        ],
        [
            InlineKeyboardButton("🔍 Search User", callback_data='admin_search'),
            InlineKeyboardButton("📢 Broadcast", callback_data='admin_broadcast'),
        ],
        [InlineKeyboardButton("🔙 Back to Menu", callback_data='back_to_menu')],
    ]
    return InlineKeyboardMarkup(keyboard)


__all__ = ['create_admin_menu_keyboard']
