"""Queue booking and reservation management callbacks."""

from __future__ import annotations
from tracking import t

import os
from datetime import date, datetime, timedelta
from typing import Any, Dict, List

from telegram import InlineKeyboardButton, InlineKeyboardMarkup, Update
from telegram.ext import ContextTypes

from botapp.handlers.dependencies import CallbackDependencies
from botapp.handlers.state import get_session_state, reset_flow
from botapp.notifications import (
    format_duplicate_reservation_message,
    format_queue_reservation_added,
)
from botapp.ui.telegram_ui import TelegramUI
from botapp.error_handler import ErrorHandler
from automation.availability import DateTimeHelpers
from infrastructure.settings import get_test_mode
from infrastructure.constants import get_court_hours

PRODUCTION_MODE = os.getenv('PRODUCTION_MODE', 'false').lower() == 'true'


class QueueHandler:
    QUEUE_BOOKING_WINDOW_DAYS = 7
    AVAILABLE_COURTS = [1, 2, 3]

    def __init__(self, deps: CallbackDependencies) -> None:
        self.deps = deps
        self.logger = deps.logger

    async def _safe_answer_callback(self, query, text: str | None = None) -> None:
        try:
            if text:
                await query.answer(text)
            else:
                await query.answer()
        except Exception as exc:
            self.logger.warning('Failed to answer callback query: %s', exc)


