"""Static booking callback route definitions."""

from __future__ import annotations
from typing import Callable, Dict

from telegram.ext import ContextTypes
from telegram import Update

CallbackFn = Callable[[Update, ContextTypes.DEFAULT_TYPE], object]


def build_routes(handler) -> Dict[str, CallbackFn]:
    """Return callback mappings for booking-related actions."""

    return {
        'menu_reserve': handler._handle_reserve_menu,
        'menu_performance': handler._handle_performance_menu,
        'menu_reservations': handler._handle_reservations_menu,
        'menu_help': handler._handle_help_menu,
        'menu_about': handler._handle_about_menu,
        'back_to_menu': handler._handle_back_to_menu,
        'reserve_48h_immediate': handler._handle_48h_immediate_booking,
        'reserve_48h_future': handler._handle_48h_future_booking,
        'back_to_booking_type': handler._handle_reserve_menu,
        'back_to_year_selection': handler._handle_48h_future_booking,
        'back_to_reserve': handler._handle_reserve_menu,
    }
