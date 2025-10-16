"""Static profile callback route definitions."""

from __future__ import annotations
from typing import Callable, Dict

from telegram import Update
from telegram.ext import ContextTypes

CallbackFn = Callable[[Update, ContextTypes.DEFAULT_TYPE], object]


def build_routes(handler) -> Dict[str, CallbackFn]:
    """Return callback mappings for profile management actions."""

    return {
        'menu_profile': handler._handle_profile_menu,
        'edit_profile': handler._handle_edit_profile,
        'edit_name': handler._handle_edit_name,
        'edit_first_name': handler._handle_edit_first_name,
        'edit_last_name': handler._handle_edit_last_name,
        'edit_phone': handler._handle_edit_phone,
        'edit_email': handler._handle_edit_email,
        'cancel_edit': handler._handle_cancel_edit,
    }
