"""Static admin callback route definitions."""

from __future__ import annotations
from typing import Callable, Dict

from telegram import Update
from telegram.ext import ContextTypes

CallbackFn = Callable[[Update, ContextTypes.DEFAULT_TYPE], object]


def build_routes(handler) -> Dict[str, CallbackFn]:
    """Return callback mappings for admin actions."""

    return {
        'menu_admin': handler._handle_admin_menu,
        'admin_view_my_reservations': handler._handle_admin_my_reservations,
        'admin_view_users_list': handler._handle_admin_users_list,
        'admin_view_all_reservations': handler._handle_admin_all_reservations,
        'admin_toggle_test_mode': handler._handle_admin_toggle_test_mode,
    }
