"""Callback dispatcher wiring domain handlers and router."""

from __future__ import annotations
from tracking import t

import logging
from typing import Callable

from telegram import Update
from telegram.ext import ContextTypes

from botapp.handlers.router import CallbackRouter
from botapp.handlers.dependencies import CallbackDependencies
from botapp.handlers.booking.handler import BookingHandler
from botapp.handlers.queue.handler import QueueHandler
from botapp.handlers.profile.handler import ProfileHandler
from botapp.handlers.admin.handler import AdminHandler
from botapp.handlers.state import get_session_state, reset_flow
from botapp.booking.immediate_handler import ImmediateBookingHandler
from botapp.error_handler import ErrorHandler
from reservations.queue.reservation_tracker import ReservationTracker
from reservations.services.cancellation_service import ReservationCancellationService


class CallbackHandler:
    """Main entrypoint invoked by Telegram callback queries."""

    def __init__(
        self,
        availability_checker,
        reservation_queue,
        user_manager,
        browser_pool=None,
        reservation_tracker: ReservationTracker | None = None,
    ) -> None:
        t('botapp.handlers.callback_handlers.CallbackHandler.__init__')
        self.logger = logging.getLogger('CallbackHandler')

        booking_handler = ImmediateBookingHandler(user_manager, browser_pool)
        reservation_tracker = reservation_tracker or ReservationTracker()

        self.deps = CallbackDependencies(
            logger=self.logger,
            availability_checker=availability_checker,
            reservation_queue=reservation_queue,
            user_manager=user_manager,
            browser_pool=browser_pool,
            booking_handler=booking_handler,
            reservation_tracker=reservation_tracker,
        )

        self.booking = BookingHandler(self.deps)
        self.profile = ProfileHandler(self.deps)
        self.queue = QueueHandler(self.deps)
        self.admin = AdminHandler(self.deps)
        self.cancellation_service = ReservationCancellationService()

        self.router = CallbackRouter(self.booking.handle_unknown_menu)
        self._register_routes()

    def _register_routes(self) -> None:
        """Register exact and dynamic routes with the router."""
        t('botapp.handlers.callback_handlers.CallbackHandler._register_routes')

        add = self.router.add_exact
        add('menu_reserve', self.booking.handle_reserve_menu)
        add('menu_reservations', self.booking.handle_reservations_menu)
        add('back_to_menu', self.booking.handle_back_to_menu)
        add('reserve_48h_immediate', self.booking.handle_48h_immediate_booking)
        add('reserve_48h_future', self.booking.handle_48h_future_booking)
        add('back_to_booking_type', self.booking.handle_reserve_menu)
        add('back_to_year_selection', self.booking.handle_48h_future_booking)
        add('back_to_reserve', self.booking.handle_reserve_menu)

        add('menu_profile', self.profile.handle_profile_menu)
        add('edit_profile', self.profile.handle_edit_profile)
        add('edit_name', self.profile.handle_edit_name)
        add('edit_first_name', self.profile.handle_edit_first_name)
        add('edit_last_name', self.profile.handle_edit_last_name)
        add('edit_phone', self.profile.handle_edit_phone)
        add('edit_email', self.profile.handle_edit_email)
        add('edit_language', self.profile.handle_edit_language)
        add('edit_court_preference', self.profile.handle_edit_court_preference)
        add('court_pref_done', self.profile.handle_court_preference_callbacks)
        add('noop', self.profile.handle_court_preference_callbacks)
        add('cancel_edit', self.profile.handle_cancel_edit)

        add('menu_queue_booking', self.queue.handle_queue_booking_menu)
        add('menu_queued', self.queue.handle_my_reservations_menu)
        add('queue_confirm', self.queue.handle_queue_booking_confirm)
        add('queue_cancel', self.queue.handle_queue_booking_cancel)
        add('back_to_queue_dates', self.booking.handle_48h_future_booking)
        add('back_to_queue_time', self.queue.handle_back_to_queue_time)
        add('back_to_queue_courts', self.queue.handle_back_to_queue_courts)

        add('menu_admin', self.admin.handle_admin_menu)
        add('admin_toggle_test_mode', self.admin.handle_admin_toggle_test_mode)
        add('admin_view_my_reservations', self.admin.handle_admin_my_reservations)
        add('admin_view_users_list', self.admin.handle_admin_users_list)
        add('admin_view_all_reservations', self.admin.handle_admin_all_reservations)

        # Prefix-based routes
        self.router.add_prefix('year_', self.booking.handle_year_selection)
        self.router.add_prefix('month_', self.booking.handle_month_selection)
        self.router.add_prefix('future_date_', self.booking.handle_future_date_selection)
        self.router.add_prefix('blocked_date_', self.queue.handle_blocked_date_selection)
        self.router.add_prefix('back_to_month_', self.booking.handle_back_to_month)
        self.router.add_prefix('cycle_day_', self.booking.handle_day_cycling)
        self.router.add_prefix('queue_court_', self.queue.handle_queue_booking_court_selection)
        self.router.add_prefix('queue_cycle_', self.queue.handle_queue_matrix_day_cycle)
        self.router.add_prefix('queue_matrix_', self.queue.handle_queue_matrix_time_selection)
        self.router.add_prefix('queue_time_modify_', self.queue.handle_time_modification)
        self.router.add_prefix('book_now_', self._handle_immediate_booking_request)
        self.router.add_prefix('confirm_book_', self._handle_immediate_booking_confirm)
        self.router.add_prefix('cancel_book_', self._handle_immediate_booking_cancel)
        self.router.add_prefix('manage_res_', self.queue.handle_manage_reservation)
        self.router.add_prefix('manage_queue_', self.queue.handle_manage_queue_reservation)
        self.router.add_prefix('res_action_', self.queue.handle_reservation_action)
        self.router.add_prefix('modify_date_', self.queue.handle_modify_option)
        self.router.add_prefix('modify_time_', self.queue.handle_modify_option)
        self.router.add_prefix('modify_courts_', self.queue.handle_modify_option)
        self.router.add_prefix('phone_digit_', self.profile.handle_phone_keypad)
        self.router.add_prefix('name_', self.profile.handle_name_callbacks)
        self.router.add_prefix('letter_', self.profile.handle_letter_input)
        self.router.add_prefix('email_char_', self.profile.handle_email_callbacks)
        self.router.add_prefix('lang_', self.profile.handle_language_selection)
        self.router.add_prefix('court_move_up_', self.profile.handle_court_preference_callbacks)
        self.router.add_prefix('court_move_down_', self.profile.handle_court_preference_callbacks)
        self.router.add_prefix('court_remove_', self.profile.handle_court_preference_callbacks)
        self.router.add_prefix('court_add_', self.profile.handle_court_preference_callbacks)
        self.router.add_prefix('admin_view_user_', self._handle_admin_view_user)
        self.router.add_prefix('cancel_reservation:', self._handle_cancel_reservation)

        # Predicate-based routes
        self.router.add_predicate(lambda data: data.startswith('date_'), self._handle_date_callback)
        self.router.add_predicate(lambda data: data.startswith('queue_time_'), self._handle_queue_time_callback)
        self.router.add_predicate(lambda data: data.startswith('email_'), self.profile.handle_email_callbacks)

    async def handle_callback(self, update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
        """Answer query and delegate to the registered handler."""

        t('botapp.handlers.callback_handlers.CallbackHandler.handle_callback')
        query = update.callback_query
        if query:
            try:
                await query.answer()
            except Exception as exc:  # pragma: no cover - defensive guard
                self.logger.warning("Failed to answer callback query: %s", exc)

            callback_data = query.data
            self.logger.info("Received callback %s from user %s", callback_data, update.effective_user.id if update.effective_user else 'Unknown')

        await self.router.dispatch(update, context)

    async def _handle_date_callback(self, update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
        """Delegate date callbacks based on current flow."""
        t('botapp.handlers.callback_handlers.CallbackHandler._handle_date_callback')

        session = get_session_state(context)
        if session.flow == 'queue_booking' or context.user_data.get('current_flow') == 'queue_booking':
            await self.queue.handle_queue_booking_date_selection(update, context)
        else:
            await self.booking.handle_date_selection(update, context)

    async def _handle_queue_time_callback(self, update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
        """Route queue time callbacks depending on modifier flag."""
        t('botapp.handlers.callback_handlers.CallbackHandler._handle_queue_time_callback')

        data = update.callback_query.data or ''
        if data.startswith('queue_time_modify_'):
            await self.queue.handle_time_modification(update, context)
        else:
            await self.queue.handle_queue_booking_time_selection(update, context)

    async def _handle_immediate_booking_request(self, update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
        t('botapp.handlers.callback_handlers.CallbackHandler._handle_immediate_booking_request')
        await self.deps.booking_handler.handle_booking_request(update, context)

    async def _handle_immediate_booking_confirm(self, update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
        t('botapp.handlers.callback_handlers.CallbackHandler._handle_immediate_booking_confirm')
        await self.deps.booking_handler.handle_booking_confirmation(update, context)

    async def _handle_immediate_booking_cancel(self, update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
        t('botapp.handlers.callback_handlers.CallbackHandler._handle_immediate_booking_cancel')
        await self.deps.booking_handler.handle_booking_cancellation(update, context)

    async def _handle_cancel_reservation(self, update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
        """Handle interactive cancellation of a reservation."""
        t('botapp.handlers.callback_handlers.CallbackHandler._handle_cancel_reservation')
        query = update.callback_query
        data = query.data or ''

        # Extract reservation_id from callback data (format: "cancel_reservation:reservation_id")
        try:
            reservation_id = data.split(':', 1)[1]
        except IndexError:
            await query.message.reply_text("❌ Invalid cancellation request")
            return

        self.logger.info("User %s requested cancellation of reservation %s", update.effective_user.id, reservation_id)

        # Send initial message
        await query.message.reply_text("🔄 Cancelling your reservation, please wait...")

        # Get the cancel URL from reservation tracker
        reservation = self.deps.reservation_tracker.get_reservation(reservation_id)

        if not reservation:
            self.logger.warning("Reservation %s not found in tracker", reservation_id)
            await query.message.reply_text(
                "❌ Could not find reservation information.\n\n"
                "The reservation may have already been cancelled or the booking details are no longer available."
            )
            return

        # Try to get cancel URL from metadata first, then from top-level
        metadata = reservation.get('metadata', {})
        cancel_url = metadata.get('cancel_modify_link') or reservation.get('cancel_modify_link')

        if not cancel_url:
            self.logger.warning("No cancel URL found for reservation %s", reservation_id)
            await query.message.reply_text(
                "❌ Could not find cancellation link for this reservation.\n\n"
                "Please try cancelling directly through your confirmation email."
            )
            return

        # Attempt to cancel using disposable browser
        try:
            result = await self.cancellation_service.cancel_reservation(cancel_url)

            if result.get('success'):
                self.logger.info("✅ Successfully cancelled reservation %s", reservation_id)

                # Update reservation status in tracker
                self.deps.reservation_tracker.cancel_reservation(reservation_id)

                await query.message.reply_text(
                    "✅ *Reservation Cancelled Successfully!*\n\n"
                    "Your court reservation has been cancelled.\n"
                    "You should receive a cancellation confirmation email shortly.",
                    parse_mode='Markdown'
                )
            else:
                error_msg = result.get('message', 'Unknown error')
                self.logger.warning("Failed to cancel reservation %s: %s", reservation_id, error_msg)

                await query.message.reply_text(
                    f"⚠️ *Could Not Cancel Reservation*\n\n"
                    f"{error_msg}\n\n"
                    f"You can try cancelling manually using the link in your confirmation email.",
                    parse_mode='Markdown'
                )

        except Exception as exc:
            self.logger.error("Exception during cancellation of %s: %s", reservation_id, exc, exc_info=True)
            await query.message.reply_text(
                "❌ An error occurred while cancelling your reservation.\n\n"
                "Please try cancelling directly through your confirmation email."
            )

    async def _handle_admin_view_user(self, update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
        t('botapp.handlers.callback_handlers.CallbackHandler._handle_admin_view_user')
        data = update.callback_query.data or ''
        try:
            user_id = int(data.replace('admin_view_user_', ''))
        except ValueError:
            await ErrorHandler.handle_booking_error(update, context, 'bad_callback', 'Invalid user identifier')
            return

        await self.admin.display_user_reservations(update, context, user_id)
