"""Static queue callback route definitions."""

from __future__ import annotations
from typing import Callable, Dict

from telegram import Update
from telegram.ext import ContextTypes

CallbackFn = Callable[[Update, ContextTypes.DEFAULT_TYPE], object]


def build_routes(handler) -> Dict[str, CallbackFn]:
    """Return callback mappings for queue management actions."""

    return {
        'menu_queue_booking': handler._handle_queue_booking_menu,
        'menu_queued': handler._handle_my_reservations_menu,
        'queue_confirm': handler._handle_queue_booking_confirm,
        'queue_cancel': handler._handle_queue_booking_cancel,
        'back_to_queue_dates': handler._handle_48h_future_booking,
        'back_to_queue_courts': handler._handle_back_to_queue_courts,
    }
