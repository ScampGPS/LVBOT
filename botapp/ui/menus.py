"""Menu-related keyboard builders for the Telegram UI."""

from __future__ import annotations
from tracking import t

from datetime import datetime
from typing import List

from telegram import InlineKeyboardButton, InlineKeyboardMarkup, ReplyKeyboardMarkup

from infrastructure.settings import get_test_mode


def create_main_menu_keyboard(is_admin: bool = False, pending_count: int = 0) -> InlineKeyboardMarkup:
    """Create the main menu keyboard."""

    t('botapp.ui.menus.create_main_menu_keyboard')
    keyboard = [
        [
            InlineKeyboardButton("🎾 Reserve Court", callback_data='menu_reserve'),
            InlineKeyboardButton("📋 Queued Reservations", callback_data='menu_queued'),
        ],
        [
            InlineKeyboardButton("👤 Profile", callback_data='menu_profile'),
            InlineKeyboardButton("📊 Performance", callback_data='menu_performance'),
        ],
        [
            InlineKeyboardButton("📅 Reservations", callback_data='menu_reservations'),
            InlineKeyboardButton("💡 Help", callback_data='menu_help'),
        ],
        [InlineKeyboardButton("ℹ️ About", callback_data='menu_about')],
    ]

    if is_admin:
        admin_text = "👮 Admin Panel"
        if pending_count > 0:
            admin_text += f" ({pending_count} pending)"
        keyboard.append([InlineKeyboardButton(admin_text, callback_data='menu_admin')])

    return InlineKeyboardMarkup(keyboard)


def create_yes_no_keyboard() -> ReplyKeyboardMarkup:
    """Create a simple yes/no keyboard."""

    t('botapp.ui.menus.create_yes_no_keyboard')
    return ReplyKeyboardMarkup([["Yes", "No"]], one_time_keyboard=True, resize_keyboard=True)


def create_cancel_keyboard() -> ReplyKeyboardMarkup:
    """Create a keyboard with only a cancel option."""

    t('botapp.ui.menus.create_cancel_keyboard')
    return ReplyKeyboardMarkup([["Cancel"]], one_time_keyboard=True, resize_keyboard=True)


def create_back_to_menu_keyboard() -> InlineKeyboardMarkup:
    """Create a standard "Back to Menu" inline keyboard."""

    t('botapp.ui.menus.create_back_to_menu_keyboard')
    keyboard = [[InlineKeyboardButton("🔙 Back to Menu", callback_data='back_to_menu')]]
    return InlineKeyboardMarkup(keyboard)


def create_48h_booking_type_keyboard() -> InlineKeyboardMarkup:
    """Create the 48-hour booking type selection keyboard."""

    t('botapp.ui.menus.create_48h_booking_type_keyboard')
    config = get_test_mode()
    future_text = "📅 Reserve after 48h"
    if config.enabled:
        future_text = "🧪 TEST: Queue Booking"

    keyboard = [
        [InlineKeyboardButton("🏃‍♂️ Reserve within 48h", callback_data='reserve_48h_immediate')],
        [InlineKeyboardButton(future_text, callback_data='reserve_48h_future')],
        [InlineKeyboardButton("⬅️ Back to Menu", callback_data='back_to_menu')],
    ]
    return InlineKeyboardMarkup(keyboard)


def create_year_selection_keyboard() -> InlineKeyboardMarkup:
    """Create year selection keyboard for future bookings."""

    t('botapp.ui.menus.create_year_selection_keyboard')
    current_year = datetime.now().year
    keyboard = [
        [InlineKeyboardButton(f"📅 {current_year}", callback_data=f'year_{current_year}')],
        [InlineKeyboardButton(f"📅 {current_year + 1}", callback_data=f'year_{current_year + 1}')],
        [InlineKeyboardButton("🔙 Back", callback_data='back_to_booking_type')],
    ]
    return InlineKeyboardMarkup(keyboard)


def create_month_selection_keyboard(year: int) -> InlineKeyboardMarkup:
    """Create month selection keyboard for a given year."""

    t('botapp.ui.menus.create_month_selection_keyboard')
    months = [
        "January",
        "February",
        "March",
        "April",
        "May",
        "June",
        "July",
        "August",
        "September",
        "October",
        "November",
        "December",
    ]

    current_date = datetime.now()
    current_year = current_date.year
    current_month = current_date.month

    keyboard: List[List[InlineKeyboardButton]] = []
    for i in range(0, 12, 3):
        row: List[InlineKeyboardButton] = []
        for j in range(3):
            if i + j >= 12:
                break
            month_num = i + j + 1
            if year == current_year and month_num < current_month:
                continue
            month_name = months[i + j]
            row.append(
                InlineKeyboardButton(
                    f"{month_name[:3]}",
                    callback_data=f'month_{year}_{month_num:02d}',
                )
            )
        if row:
            keyboard.append(row)

    keyboard.append([InlineKeyboardButton("🔙 Back to Year", callback_data='back_to_year_selection')])
    return InlineKeyboardMarkup(keyboard)


__all__ = [
    'create_main_menu_keyboard',
    'create_yes_no_keyboard',
    'create_cancel_keyboard',
    'create_back_to_menu_keyboard',
    'create_48h_booking_type_keyboard',
    'create_year_selection_keyboard',
    'create_month_selection_keyboard',
]
