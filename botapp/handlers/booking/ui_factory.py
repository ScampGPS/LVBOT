"""UI factories for booking handler messages and keyboards."""

from __future__ import annotations

from dataclasses import dataclass
from typing import Callable

from telegram import InlineKeyboardButton, InlineKeyboardMarkup

from botapp.ui.telegram_ui import TelegramUI


@dataclass(frozen=True)
class BookingMenuView:
    text: str
    reply_markup: InlineKeyboardMarkup


class BookingUIFactory:
    """Produces common booking handler views (text + keyboards)."""

    def __init__(self, telegram_ui: TelegramUI | None = None) -> None:
        # Allow dependency injection in tests
        self._ui = telegram_ui or TelegramUI

    def booking_type_selection(self) -> BookingMenuView:
        """Return the view for the top-level reserve menu."""

        keyboard = self._ui.create_48h_booking_type_keyboard()
        return BookingMenuView(
            text="🎾 Reserve Court\n\nChoose booking type:",
            reply_markup=keyboard,
        )

    def empty_reservations_view(self) -> BookingMenuView:
        """Return the view shown when a user has no reservations."""

        return BookingMenuView(
            text=(
                "📅 **My Reservations**\n\n"
                "You don't have any active reservations.\n\n"
                "Use '🎾 Reserve Court' to make a booking!"
            ),
            reply_markup=self._ui.create_back_to_menu_keyboard(),
        )

    def admin_reservations_menu(
        self,
        *,
        button_factory: Callable[[], InlineKeyboardMarkup] | None = None,
    ) -> BookingMenuView:
        """Return the admin reservation management menu."""

        if button_factory:
            reply_markup = button_factory()
        else:
            reply_markup = InlineKeyboardMarkup(
                [
                    [InlineKeyboardButton("📋 My Reservations", callback_data='admin_view_my_reservations')],
                    [InlineKeyboardButton("👥 View by User", callback_data='admin_view_users_list')],
                    [InlineKeyboardButton("📊 All Reservations", callback_data='admin_view_all_reservations')],
                    [InlineKeyboardButton("⬅️ Back", callback_data='back_to_menu')],
                ]
            )

        return BookingMenuView(
            text="👮 **Admin Reservations Menu**\n\nSelect which reservations to view:",
            reply_markup=reply_markup,
        )
