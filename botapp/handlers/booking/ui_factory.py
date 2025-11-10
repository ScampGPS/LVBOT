"""UI factories for booking handler messages and keyboards."""

from __future__ import annotations
from tracking import t

from dataclasses import dataclass
from typing import Callable

from telegram import InlineKeyboardButton, InlineKeyboardMarkup

from botapp.ui.telegram_ui import TelegramUI
from botapp.i18n import Translator


@dataclass(frozen=True)
class BookingMenuView:
    text: str
    reply_markup: InlineKeyboardMarkup


class BookingUIFactory:
    """Produces common booking handler views (text + keyboards)."""

    def __init__(self, telegram_ui: TelegramUI | None = None) -> None:
        # Allow dependency injection in tests
        t('botapp.handlers.booking.ui_factory.BookingUIFactory.__init__')
        self._ui = telegram_ui or TelegramUI

    def booking_type_selection(
        self,
        *,
        translator: Translator | None = None,
    ) -> BookingMenuView:
        """Return the view for the top-level reserve menu."""
        t('botapp.handlers.booking.ui_factory.BookingUIFactory.booking_type_selection')

        language = translator.get_language() if translator else None
        keyboard = self._ui.create_48h_booking_type_keyboard(language=language)
        if translator:
            text = (
                f"{translator.t('booking.menu_title')}\n\n"
                f"{translator.t('booking.menu_prompt')}"
            )
        else:
            text = "🎾 Reserve Court\n\nChoose booking type:"
        return BookingMenuView(text=text, reply_markup=keyboard)

    def empty_reservations_view(
        self,
        *,
        translator: Translator | None = None,
    ) -> BookingMenuView:
        """Return the view shown when a user has no reservations."""
        t('botapp.handlers.booking.ui_factory.BookingUIFactory.empty_reservations_view')

        language = translator.get_language() if translator else None
        if translator:
            text = (
                f"{translator.t('booking.empty_title')}\n\n"
                f"{translator.t('booking.empty_message')}\n\n"
                f"{translator.t('booking.empty_cta')}"
            )
        else:
            text = (
                "📅 **My Reservations**\n\n"
                "You don't have any active reservations.\n\n"
                "Use '🎾 Reserve Court' to make a booking!"
            )
        return BookingMenuView(
            text=text,
            reply_markup=self._ui.create_back_to_menu_keyboard(language=language),
        )

    def admin_reservations_menu(
        self,
        *,
        translator: Translator | None = None,
        button_factory: Callable[[], InlineKeyboardMarkup] | None = None,
    ) -> BookingMenuView:
        """Return the admin reservation management menu."""
        t('botapp.handlers.booking.ui_factory.BookingUIFactory.admin_reservations_menu')

        language = translator.get_language() if translator else None
        if button_factory:
            reply_markup = button_factory()
        else:
            if translator:
                my_reservations_label = translator.t('menu.reservations')
                by_user_label = translator.t('admin.view_by_user_button')
                all_reservations_label = translator.t('admin.view_all_reservations_button')
                back_label = translator.t('nav.back_to_menu')
            else:
                my_reservations_label = "📋 My Reservations"
                by_user_label = "👥 View by User"
                all_reservations_label = "📊 All Reservations"
                back_label = "⬅️ Back"
            reply_markup = InlineKeyboardMarkup(
                [
                    [InlineKeyboardButton(my_reservations_label, callback_data='admin_view_my_reservations')],
                    [InlineKeyboardButton(by_user_label, callback_data='admin_view_users_list')],
                    [InlineKeyboardButton(all_reservations_label, callback_data='admin_view_all_reservations')],
                    [InlineKeyboardButton(back_label, callback_data='back_to_menu')],
                ]
            )

        if translator:
            text = (
                f"{translator.t('admin.reservations_menu.title')}\n\n"
                f"{translator.t('admin.reservations_menu.prompt')}"
            )
        else:
            text = "👮 **Admin Reservations Menu**\n\nSelect which reservations to view:"

        return BookingMenuView(text=text, reply_markup=reply_markup)
