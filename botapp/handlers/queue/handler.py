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

        await self.booking_flow._show_time_selection(update, context, selected_date)

    async def handle_queue_booking_menu(
        self, update: Update, context: ContextTypes.DEFAULT_TYPE
    ) -> None:
        """Handle Queue Booking menu option."""

        t(
            "botapp.handlers.callback_handlers.CallbackHandler._handle_queue_booking_menu"
        )
        await self.booking_flow.show_menu(update, context)

    async def handle_my_reservations_menu(
        self,
        update: Update,
        context: ContextTypes.DEFAULT_TYPE,
    ) -> None:
        """Handle My Reservations menu option."""

        t(
            "botapp.handlers.callback_handlers.CallbackHandler._handle_my_reservations_menu"
        )
        await self.reservation_manager.show_user_menu(update, context)

    async def handle_queue_booking_date_selection(
        self,
        update: Update,
        context: ContextTypes.DEFAULT_TYPE,
    ) -> None:
        """Handle date selection for queue booking flow."""

        t(
            "botapp.handlers.callback_handlers.CallbackHandler._handle_queue_booking_date_selection"
        )
        await self.booking_flow.select_date(update, context)

    async def handle_queue_booking_time_selection(
        self,
        update: Update,
        context: ContextTypes.DEFAULT_TYPE,
    ) -> None:
        """Handle time selection for queue booking flow."""

        t(
            "botapp.handlers.callback_handlers.CallbackHandler._handle_queue_booking_time_selection"
        )
        await self.booking_flow.select_time(update, context)

    async def handle_queue_booking_court_selection(
        self,
        update: Update,
        context: ContextTypes.DEFAULT_TYPE,
    ) -> None:
        """Handle court selection for queue booking flow."""

        t(
            "botapp.handlers.callback_handlers.CallbackHandler._handle_queue_booking_court_selection"
        )
        await self.booking_flow.select_courts(update, context)

    async def handle_queue_booking_confirm(
        self,
        update: Update,
        context: ContextTypes.DEFAULT_TYPE,
    ) -> None:
        """Handle confirmation of queue booking reservation."""

        t(
            "botapp.handlers.callback_handlers.CallbackHandler._handle_queue_booking_confirm"
        )
        await self.booking_flow.confirm(update, context)

    def clear_queue_booking_state(self, context: ContextTypes.DEFAULT_TYPE) -> None:
        """Remove queue-booking state from the user context."""

        self.booking_flow.clear_state(context)

    async def handle_blocked_date_selection(
        self,
        update: Update,
        context: ContextTypes.DEFAULT_TYPE,
    ) -> None:
        """Allow selecting within-48h dates when test mode permits."""

        t("botapp.handlers.queue.QueueHandler.handle_blocked_date_selection")
        await self.booking_flow.handle_blocked_date(update, context)

    async def handle_queue_booking_cancel(
        self,
        update: Update,
        context: ContextTypes.DEFAULT_TYPE,
    ) -> None:
        """Handle cancellation of queue booking reservation."""

        t(
            "botapp.handlers.callback_handlers.CallbackHandler._handle_queue_booking_cancel"
        )
        await self.booking_flow.cancel(update, context)

    async def handle_back_to_queue_courts(
        self,
        update: Update,
        context: ContextTypes.DEFAULT_TYPE,
    ) -> None:
        """Handle returning to the court selection screen."""

        t(
            "botapp.handlers.callback_handlers.CallbackHandler._handle_back_to_queue_courts"
        )
        await self.booking_flow.back_to_courts(update, context)

    async def handle_manage_reservation(
        self,
        update: Update,
        context: ContextTypes.DEFAULT_TYPE,
    ) -> None:
        """Handle individual reservation management."""

        t(
            "botapp.handlers.callback_handlers.CallbackHandler._handle_manage_reservation"
        )
        await self.reservation_manager.manage_reservation(update, context)

    async def handle_manage_queue_reservation(
        self,
        update: Update,
        context: ContextTypes.DEFAULT_TYPE,
    ) -> None:
        """Handle management of a specific queued reservation."""

        t(
            "botapp.handlers.callback_handlers.CallbackHandler._handle_manage_queue_reservation"
        )
        await self.reservation_manager.manage_queue_reservation(update, context)

    async def handle_reservation_action(
        self,
        update: Update,
        context: ContextTypes.DEFAULT_TYPE,
    ) -> None:
        """Handle reservation actions (cancel, modify, share)."""

        t(
            "botapp.handlers.callback_handlers.CallbackHandler._handle_reservation_action"
        )
        await self.reservation_manager.handle_action(update, context)

    async def handle_cancel_reservation(
        self,
        update: Update,
        context: ContextTypes.DEFAULT_TYPE,
        reservation_id: str,
    ) -> None:
        """Cancel a reservation."""

        t(
            "botapp.handlers.callback_handlers.CallbackHandler._handle_cancel_reservation"
        )
        await self.reservation_manager.cancel_reservation(
            update, context, reservation_id
        )

    async def handle_modify_reservation(
        self,
        update: Update,
        context: ContextTypes.DEFAULT_TYPE,
        reservation_id: str,
    ) -> None:
        """Modify a reservation."""

        t(
            "botapp.handlers.callback_handlers.CallbackHandler._handle_modify_reservation"
        )
        await self.reservation_manager.modify_reservation(
            update, context, reservation_id
        )

    async def handle_share_reservation(
        self,
        update: Update,
        context: ContextTypes.DEFAULT_TYPE,
        reservation_id: str,
    ) -> None:
        """Share reservation details."""

        t("botapp.handlers.callback_handlers.CallbackHandler._handle_share_reservation")
        await self.reservation_manager.share_reservation(
            update, context, reservation_id
        )

    async def handle_modify_option(
        self,
        update: Update,
        context: ContextTypes.DEFAULT_TYPE,
    ) -> None:
        """Handle modification options for queued reservations."""

        t("botapp.handlers.callback_handlers.CallbackHandler._handle_modify_option")
        await self.reservation_manager.modify_option(update, context)

    async def handle_time_modification(
        self,
        update: Update,
        context: ContextTypes.DEFAULT_TYPE,
    ) -> None:
        """Handle time modification from the modify menu."""

        t("botapp.handlers.callback_handlers.CallbackHandler._handle_time_modification")
        await self.reservation_manager.time_modification(update, context)

    async def _display_user_reservations(
        self, update: Update, context: ContextTypes.DEFAULT_TYPE, target_user_id: int
    ) -> None:
        """
        Display reservations for a specific user (reusable method)

        Args:
            update: The telegram update
            context: The callback context
            target_user_id: The user whose reservations to display
        """
        t(
            "botapp.handlers.callback_handlers.CallbackHandler._display_user_reservations"
        )
        await self.reservation_manager.display_user_reservations(
            update, context, target_user_id
        )

    async def _display_all_reservations(
        self, query, all_reservations: List[Dict[str, Any]]
    ) -> None:
        """
        Display all reservations from all users

        Args:
            query: The callback query
            all_reservations: List of all reservations with user info
        """
        t("botapp.handlers.callback_handlers.CallbackHandler._display_all_reservations")
        await self.reservation_manager.display_all_reservations(query, all_reservations)
