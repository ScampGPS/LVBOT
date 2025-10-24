"""Queue booking and reservation management callbacks."""

from __future__ import annotations
from tracking import t

from datetime import date
from typing import Any, Dict, List

from telegram import Update
from telegram.ext import ContextTypes

from botapp.handlers.dependencies import CallbackDependencies
from botapp.handlers.queue.flows import QueueBookingFlow, QueueReservationManager
from botapp.handlers.queue.messages import QueueMessageFactory
from botapp.handlers.mixins import CallbackResponseMixin
from botapp.notifications import (
    format_duplicate_reservation_message,
    format_queue_reservation_added,
)
from botapp.ui.telegram_ui import TelegramUI  # noqa: F401 - test monkeypatch support
from infrastructure.settings import get_test_mode


def _delegate(
    attr_name: str,
    method_name: str,
    tracking_id: str,
    doc: str,
):
    """Create an async handler that logs and forwards to a dependency."""

    async def handler(self, *args, **kwargs):
        t(tracking_id)
        target = getattr(self, attr_name)
        method = getattr(target, method_name)

        update = args[0] if args else None
        callback_data = None
        user_id = None
        if update is not None:
            user = getattr(update, "effective_user", None)
            if user is not None:
                user_id = getattr(user, "id", None)
            query = getattr(update, "callback_query", None)
            if query is not None:
                callback_data = getattr(query, "data", None)

        logger = getattr(self, "logger", None)
        if logger is not None:
            logger.info(
                "QueueHandler delegating to %s.%s user=%s callback_data=%s",
                attr_name,
                method_name,
                user_id,
                callback_data,
            )
        return await method(*args, **kwargs)

    handler.__doc__ = doc
    handler.__name__ = method_name
    return handler


class QueueHandler(CallbackResponseMixin):
    """Handles queue booking flows and reservation management."""

    def __init__(self, deps: CallbackDependencies) -> None:
        t("botapp.handlers.queue.QueueHandler.__init__")
        self.deps = deps
        self.logger = deps.logger
        self.messages = QueueMessageFactory()

        async def safe_answer(query, text: str | None = None) -> None:
            return await self._safe_answer_callback(query, text)

        async def edit_message(query, text: str, **kwargs) -> None:
            return await self._edit_callback_message(query, text, **kwargs)

        self.booking_flow = QueueBookingFlow(
            deps,
            self.messages,
            safe_answer,
            edit_message,
            lambda: globals()["get_test_mode"](),
            lambda *args, **kwargs: globals()["format_queue_reservation_added"](
                *args, **kwargs
            ),
            lambda *args, **kwargs: globals()["format_duplicate_reservation_message"](
                *args, **kwargs
            ),
            lambda update, context, selected_date: self._show_queue_time_selection(
                update, context, selected_date
            ),
        )
        self.reservation_manager = QueueReservationManager(
            deps,
            self.messages,
            safe_answer,
            edit_message,
            lambda: globals()["get_test_mode"](),
        )

    async def _show_queue_time_selection(
        self,
        update: Update,
        context: ContextTypes.DEFAULT_TYPE,
        selected_date: date,
    ) -> None:
        """Compatibility hook that delegates to the booking flow time selector."""
        user_id = (
            update.callback_query.from_user.id
            if update.callback_query and getattr(update.callback_query, 'from_user', None)
            else (update.effective_user.id if update.effective_user else None)
        )
        self.logger.info(
            "QueueHandler._show_queue_time_selection user=%s selected_date=%s",
            user_id,
            selected_date,
        )
        await self.booking_flow._show_time_selection(update, context, selected_date)

    handle_queue_booking_menu = _delegate(
        "booking_flow",
        "show_menu",
        "botapp.handlers.callback_handlers.CallbackHandler._handle_queue_booking_menu",
        "Handle Queue Booking menu option.",
    )

    handle_my_reservations_menu = _delegate(
        "reservation_manager",
        "show_user_menu",
        "botapp.handlers.callback_handlers.CallbackHandler._handle_my_reservations_menu",
        "Handle My Reservations menu option.",
    )

    handle_queue_booking_date_selection = _delegate(
        "booking_flow",
        "select_date",
        "botapp.handlers.callback_handlers.CallbackHandler._handle_queue_booking_date_selection",
        "Handle date selection for queue booking flow.",
    )

    handle_queue_booking_time_selection = _delegate(
        "booking_flow",
        "select_time",
        "botapp.handlers.callback_handlers.CallbackHandler._handle_queue_booking_time_selection",
        "Handle time selection for queue booking flow.",
    )

    handle_queue_booking_court_selection = _delegate(
        "booking_flow",
        "select_courts",
        "botapp.handlers.callback_handlers.CallbackHandler._handle_queue_booking_court_selection",
        "Handle court selection for queue booking flow.",
    )

    handle_queue_booking_confirm = _delegate(
        "booking_flow",
        "confirm",
        "botapp.handlers.callback_handlers.CallbackHandler._handle_queue_booking_confirm",
        "Handle confirmation of queue booking reservation.",
    )

    def clear_queue_booking_state(self, context: ContextTypes.DEFAULT_TYPE) -> None:
        """Remove queue-booking state from the user context."""

        self.booking_flow.clear_state(context)

    handle_blocked_date_selection = _delegate(
        "booking_flow",
        "handle_blocked_date",
        "botapp.handlers.queue.QueueHandler.handle_blocked_date_selection",
        "Allow selecting within-48h dates when test mode permits.",
    )

    handle_queue_booking_cancel = _delegate(
        "booking_flow",
        "cancel",
        "botapp.handlers.callback_handlers.CallbackHandler._handle_queue_booking_cancel",
        "Handle cancellation of queue booking reservation.",
    )

    handle_back_to_queue_courts = _delegate(
        "booking_flow",
        "back_to_courts",
        "botapp.handlers.callback_handlers.CallbackHandler._handle_back_to_queue_courts",
        "Handle returning to the court selection screen.",
    )

    handle_manage_reservation = _delegate(
        "reservation_manager",
        "manage_reservation",
        "botapp.handlers.callback_handlers.CallbackHandler._handle_manage_reservation",
        "Handle individual reservation management.",
    )

    handle_manage_queue_reservation = _delegate(
        "reservation_manager",
        "manage_queue_reservation",
        "botapp.handlers.callback_handlers.CallbackHandler._handle_manage_queue_reservation",
        "Handle management of a specific queued reservation.",
    )

    handle_reservation_action = _delegate(
        "reservation_manager",
        "handle_action",
        "botapp.handlers.callback_handlers.CallbackHandler._handle_reservation_action",
        "Handle reservation actions (cancel, modify, share).",
    )

    handle_cancel_reservation = _delegate(
        "reservation_manager",
        "cancel_reservation",
        "botapp.handlers.callback_handlers.CallbackHandler._handle_cancel_reservation",
        "Cancel a reservation.",
    )

    handle_modify_reservation = _delegate(
        "reservation_manager",
        "modify_reservation",
        "botapp.handlers.callback_handlers.CallbackHandler._handle_modify_reservation",
        "Modify a reservation.",
    )

    handle_share_reservation = _delegate(
        "reservation_manager",
        "share_reservation",
        "botapp.handlers.callback_handlers.CallbackHandler._handle_share_reservation",
        "Share reservation details.",
    )

    handle_modify_option = _delegate(
        "reservation_manager",
        "modify_option",
        "botapp.handlers.callback_handlers.CallbackHandler._handle_modify_option",
        "Handle modification options for queued reservations.",
    )

    handle_time_modification = _delegate(
        "reservation_manager",
        "time_modification",
        "botapp.handlers.callback_handlers.CallbackHandler._handle_time_modification",
        "Handle time modification from the modify menu.",
    )

    _display_user_reservations = _delegate(
        "reservation_manager",
        "display_user_reservations",
        "botapp.handlers.callback_handlers.CallbackHandler._display_user_reservations",
        "Display reservations for a specific user (reusable method)",
    )

    _display_all_reservations = _delegate(
        "reservation_manager",
        "display_all_reservations",
        "botapp.handlers.callback_handlers.CallbackHandler._display_all_reservations",
        "Display all reservations from all users",
    )
