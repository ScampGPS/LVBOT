"""Queue flow classes extracted from the queue handler."""

from __future__ import annotations
from tracking import t

from datetime import date, datetime, timedelta
from typing import Any, Callable, Iterable, Mapping, Sequence
from telegram.constants import ParseMode

import pytz

from telegram import InlineKeyboardMarkup, InlineKeyboardButton, Update
from telegram.ext import ContextTypes

from botapp.error_handler import ErrorHandler
from botapp.i18n import create_translator
from botapp.handlers.queue.session import QueueSessionStore
from reservations.queue.court_utils import normalize_court_sequence
from botapp.handlers.queue.guards import (
    IncompleteProfileError,
    MissingModificationContextError,
    MissingQueueSummaryError,
    ensure_modification,
    ensure_profile_fields,
    ensure_summary,
)
from botapp.handlers.queue.messages import QueueMessageFactory
from botapp.handlers.queue.live_availability import (
    fetch_live_time_slots,
    fetch_live_availability_matrix,
)
from botapp.handlers.state import reset_flow
from infrastructure.constants import get_court_hours
from reservations.queue.request_builder import DEFAULT_BUILDER, ReservationRequestBuilder
from botapp.ui.telegram_ui import TelegramUI


SafeAnswer = Callable[[Any, str | None], Any]
EditCallback = Callable[..., Any]


def format_court_preferences(
    selected_courts: Sequence[int],
    all_courts: Sequence[int] | None = None,
) -> str:
    """Create a readable label for court selections."""
    t('botapp.handlers.queue.flows.format_court_preferences')

    courts = list(selected_courts)
    if not courts:
        return "No Courts Selected"

    reference = set(all_courts or selected_courts)
    if set(courts) == reference:
        return "All Courts"

    return ", ".join(f"Court {court}" for court in sorted(courts))


class QueueFlowBase:
    """Shared helpers for queue flows."""

    def __init__(
        self,
        deps,
        messages: QueueMessageFactory,
        safe_answer: SafeAnswer,
        edit_message: EditCallback,
        *,
        request_builder: ReservationRequestBuilder | None = None,
    ) -> None:
        t('botapp.handlers.queue.flows.QueueFlowBase.__init__')
        self.deps = deps
        self.logger = deps.logger
        self.messages = messages
        self._safe_answer = safe_answer
        self._edit_message = edit_message
        self._request_builder = request_builder or DEFAULT_BUILDER

    async def answer_callback(self, query, text: str | None = None) -> None:
        """Safely answer callback queries using the provided helper."""
        t('botapp.handlers.queue.flows.QueueFlowBase.answer_callback')

        try:
            await self._safe_answer(query, text)
        except TypeError:
            # Backwards compatibility: some callers still pass the coroutine function
            await self._safe_answer(query)  # pragma: no cover

    async def edit_callback(self, query, text: str, **kwargs) -> None:
        """Edit callback messages through the shared helper."""
        t('botapp.handlers.queue.flows.QueueFlowBase.edit_callback')

        await self._edit_message(query, text, **kwargs)

    def _translator_for_user(self, user_id: int | None):
        """Return a translator instance and language code for a user."""
        t('botapp.handlers.queue.flows.QueueFlowBase._translator_for_user')

        language = None
        user_manager = getattr(self.deps, 'user_manager', None)
        if user_id and user_manager:
            try:
                language = user_manager.get_user_language(user_id)
            except Exception:
                language = None
        translator = create_translator(language)
        return translator, language


class QueueBookingFlow(QueueFlowBase):
    """Encapsulates the queue booking callback flow."""

    QUEUE_BOOKING_WINDOW_DAYS = 7
    AVAILABLE_COURTS = (1, 2, 3)
    _MEXICO_TZ = pytz.timezone('America/Mexico_City')

    def __init__(
        self,
        deps,
        messages: QueueMessageFactory,
        safe_answer: SafeAnswer,
        edit_message: EditCallback,
        get_test_mode,
        format_queue_reservation_added,
        format_duplicate_reservation_message,
        show_time_selection,
        *,
        request_builder: ReservationRequestBuilder | None = None,
    ) -> None:
        t('botapp.handlers.queue.flows.QueueBookingFlow.__init__')
        super().__init__(
            deps,
            messages,
            safe_answer,
            edit_message,
            request_builder=request_builder,
        )
        self._get_test_mode = get_test_mode
        self._format_queue_reservation_added = format_queue_reservation_added
        self._format_duplicate_reservation_message = format_duplicate_reservation_message
        self._show_time_selection_callback = show_time_selection

    @staticmethod
    def _session_store(context: ContextTypes.DEFAULT_TYPE) -> QueueSessionStore:
        t('botapp.handlers.queue.flows.QueueBookingFlow._session_store')
        return QueueSessionStore(context)

    async def show_menu(self, update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
        """Display the queue booking menu with date options."""
        t('botapp.handlers.queue.flows.QueueBookingFlow.show_menu')

        query = update.callback_query
        await self.answer_callback(query)

        user_id = (
            query.from_user.id
            if query and getattr(query, 'from_user', None)
            else (update.effective_user.id if update.effective_user else None)
        )
        _, language = self._translator_for_user(user_id)
        self.logger.info(
            "QueueBookingFlow.show_menu user=%s current_flow=%s",
            user_id,
            context.user_data.get('current_flow'),
        )

        user_id = (
            query.from_user.id
            if query and getattr(query, 'from_user', None)
            else (update.effective_user.id if update.effective_user else None)
        )

        self.logger.info(
            "QueueBookingFlow.handle_matrix_day_cycle user=%s new_date=%s",
            user_id,
            new_date,
        )

        store = self._session_store(context)
        reset_flow(context, 'queue_booking')
        context.user_data['current_flow'] = 'queue_booking'
        store.clear()
        context.user_data.pop('queue_live_time_cache', None)
        context.user_data.pop('queue_live_matrix', None)
        context.user_data.pop('queue_available_dates', None)

        today = date.today()
        config = self._get_test_mode()
        tz = self._MEXICO_TZ
        now = datetime.now(tz)

        dates = [
            (candidate, self._format_date_label(candidate, today))
            for candidate in (today + timedelta(days=offset) for offset in range(self.QUEUE_BOOKING_WINDOW_DAYS))
            if self._date_has_available_slots(candidate, config, tz, now)
        ]

        self.logger.info(
            "QueueBookingFlow.show_menu computed %s available dates for user=%s",
            len(dates),
            user_id,
        )

        if not dates:
            self.logger.info(
                "QueueBookingFlow.show_menu no selectable dates user=%s",
                user_id,
            )
            reply_markup = TelegramUI.create_back_to_menu_keyboard()
            await self.edit_callback(
                query,
                "⏰ Queue Booking\n\n"
                "❌ No dates available for queue booking.\n\n"
                "All available time slots are within the 48-hour booking window. "
                "Please use the 'Check Availability' option for immediate bookings.",
                reply_markup=reply_markup,
            )
            return

        keyboard = TelegramUI.create_date_selection_keyboard(dates, language=language)
        await self.edit_callback(
            query,
            "⏰ Queue Booking\n\n"
            "📅 Select a date for your queued reservation:\n\n"
            "ℹ️ Note: Only time slots more than 48 hours away will be shown.",
            reply_markup=keyboard,
        )

    async def select_date(self, update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
        """Handle queue booking date selection."""
        t('botapp.handlers.queue.flows.QueueBookingFlow.select_date')

        query = update.callback_query
        await self.answer_callback(query)

        user_id = (
            query.from_user.id
            if query and getattr(query, 'from_user', None)
            else (update.effective_user.id if update.effective_user else None)
        )
        callback_data = query.data if query else None
        self.logger.info(
            "QueueBookingFlow.select_date user=%s callback_data=%s",
            user_id,
            callback_data,
        )

        callback_data = query.data
        date_str = callback_data.replace('queue_date_', '')

        try:
            selected_date = datetime.strptime(date_str, '%Y-%m-%d').date()
        except ValueError:
            await ErrorHandler.handle_booking_error(
                update,
                context,
                'invalid_date',
                f'Invalid date format received: {callback_data}',
            )
            return

        store = self._session_store(context)
        store.selected_date = selected_date
        store.selected_time = None
        store.selected_courts = []

        self.logger.info(
            "QueueBookingFlow.select_date stored user=%s selected_date=%s",
            user_id,
            selected_date,
        )

        await self._show_time_selection(update, context, selected_date)

    async def select_time(self, update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
        """Handle queue booking time selection."""
        t('botapp.handlers.queue.flows.QueueBookingFlow.select_time')

        query = update.callback_query
        await self.answer_callback(query)

        user_id = (
            query.from_user.id
            if query and getattr(query, 'from_user', None)
            else (update.effective_user.id if update.effective_user else None)
        )
        callback_data = query.data if query else None
        self.logger.info(
            "QueueBookingFlow.select_time user=%s callback_data=%s",
            user_id,
            callback_data,
        )

        callback_data = query.data
        try:
            parts = callback_data.split('_') if callback_data else []
            if len(parts) != 4:
                raise ValueError('Unexpected queue time callback format')

            _, _, callback_date_str, selected_time = parts
            callback_date = datetime.strptime(callback_date_str, '%Y-%m-%d').date()
        except (ValueError, IndexError):
            self.logger.error("Invalid queue time callback format: %s", callback_data)
            await self.edit_callback(
                query,
                f"❌ Invalid time selection format received: {callback_data}. Please try again.",
            )
            return

        self.logger.info(
            "QueueBookingFlow.select_time parsed user=%s time=%s date=%s",
            user_id,
            selected_time,
            callback_date,
        )

        store = self._session_store(context)
        modifying_id, modifying_option = store.modification
        if modifying_id and modifying_option == 'time':
            reservation = self.deps.reservation_queue.get_reservation(modifying_id)
            if reservation:
                reservation['target_time'] = selected_time
                self.deps.reservation_queue.update_reservation(modifying_id, reservation)

                store.set_modification(None, None)

                await self.edit_callback(
                    query,
                    self.messages.time_updated(selected_time),
                    parse_mode='Markdown',
                    reply_markup=InlineKeyboardMarkup([
                        [InlineKeyboardButton("📋 View Reservation", callback_data=f"manage_queue_{modifying_id}")],
                        [InlineKeyboardButton("🏠 Main Menu", callback_data='back_to_menu')],
                    ]),
                )
                return

        store.selected_time = selected_time
        selected_date = store.selected_date

        if selected_date is None:
            self.logger.error("Missing queue_booking_date in user context")
            await self.edit_callback(query, self.messages.session_expired())
            return

        if selected_date != callback_date:
            self.logger.warning(
                "Date mismatch: stored=%s, callback=%s",
                selected_date,
                callback_date,
            )
            await ErrorHandler.handle_booking_error(
                update,
                context,
                'invalid_date',
                'Date mismatch between stored and callback data. Please restart the booking process.',
            )
            return

        await self._present_court_selection(query, selected_date, selected_time)

    async def select_courts(self, update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
        """Handle court selection for queue booking."""
        t('botapp.handlers.queue.flows.QueueBookingFlow.select_courts')

        query = update.callback_query
        await self.answer_callback(query)

        user_id = (
            query.from_user.id
            if query and getattr(query, 'from_user', None)
            else (update.effective_user.id if update.effective_user else None)
        )
        callback_data = query.data if query else None
        self.logger.info(
            "QueueBookingFlow.select_courts user=%s callback_data=%s",
            user_id,
            callback_data,
        )

        callback_data = query.data
        selected_courts = [
            int(part)
            for part in callback_data.replace('queue_courts_', '').split('_')
            if part.isdigit()
        ]

        if not selected_courts:
            cleaned_courts = list(self.AVAILABLE_COURTS)
        else:
            cleaned_courts = normalize_court_sequence(
                selected_courts,
                allowed=self.AVAILABLE_COURTS,
            )
            if not cleaned_courts:
                cleaned_courts = list(self.AVAILABLE_COURTS)

        self.logger.info(
            "QueueBookingFlow.select_courts parsed user=%s courts=%s",
            user_id,
            cleaned_courts,
        )

        await self._complete_court_selection(
            query,
            context,
            cleaned_courts,
            user_id=user_id,
        )

    async def confirm(self, update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
        """Confirm queue booking and add reservation to queue."""
        t('botapp.handlers.queue.flows.QueueBookingFlow.confirm')

        query = update.callback_query
        await self.answer_callback(query)

        user_id = (
            query.from_user.id
            if query and getattr(query, 'from_user', None)
            else (update.effective_user.id if update.effective_user else None)
        )
        self.logger.info("QueueBookingFlow.confirm user=%s", user_id)

        store = self._session_store(context)

        try:
            booking_summary = ensure_summary(context)
        except MissingQueueSummaryError:
            self.logger.error("Missing queue_booking_summary in user context")
            await self.edit_callback(query, self.messages.session_expired())
            return

        self.logger.info(
            "QueueBookingFlow.confirm summary user=%s target=%s %s",
            user_id,
            booking_summary.get('target_date'),
            booking_summary.get('target_time'),
        )

        config = self._get_test_mode()

        try:
            reservation_request = self._request_builder.from_summary(booking_summary)
            reservation_id = self.deps.reservation_queue.add_reservation_request(reservation_request)

            store.clear()
            context.user_data.pop('current_flow', None)

            self.logger.info(
                "QueueBookingFlow.confirm queued reservation user=%s reservation_id=%s",
                user_id,
                reservation_id,
            )

            reply_markup = TelegramUI.create_back_to_menu_keyboard()
            success_message = self._format_queue_reservation_added(
                booking_summary,
                reservation_id,
                test_mode_config=config,
            )

            await self.edit_callback(
                query,
                success_message,
                parse_mode=ParseMode.MARKDOWN_V2,
                reply_markup=reply_markup,
            )

        except ValueError as error:
            self.logger.warning("Duplicate reservation attempt: %s", error)

            reply_markup = TelegramUI.create_back_to_menu_keyboard()
            duplicate_message = self._format_duplicate_reservation_message(str(error))

            await self.edit_callback(
                query,
                duplicate_message,
                parse_mode=ParseMode.MARKDOWN_V2,
                reply_markup=reply_markup,
            )

            store.clear()
            context.user_data.pop('current_flow', None)

        except Exception:
            await ErrorHandler.handle_booking_error(
                update,
                context,
                'booking_failed',
                'Failed to add reservation to queue',
            )

    async def handle_matrix_time_selection(self, update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
        """Handle time selection from the matrix keyboard."""
        t('botapp.handlers.queue.flows.QueueBookingFlow.handle_matrix_time_selection')

        query = update.callback_query
        await self.answer_callback(query)

        data = query.data or ''
        payload = data.replace('queue_matrix_', '')
        parts = payload.split('_')
        if len(parts) != 3:
            self.logger.error("Invalid queue matrix callback format: %s", data)
            await self.edit_callback(
                query,
                f"❌ Invalid time selection format received: {data}. Please try again.",
            )
            return

        date_str, court_str, time_str = parts
        try:
            selected_date = datetime.strptime(date_str, '%Y-%m-%d').date()
            court_num = int(court_str)
        except ValueError:
            self.logger.error("Failed to parse matrix selection payload: %s", data)
            await self.edit_callback(
                query,
                f"❌ Invalid time selection format received: {data}. Please try again.",
            )
            return

        user_id = (
            query.from_user.id
            if query and getattr(query, 'from_user', None)
            else (update.effective_user.id if update.effective_user else None)
        )

        self.logger.info(
            "QueueBookingFlow.handle_matrix_time_selection user=%s date=%s court=%s time=%s",
            user_id,
            selected_date,
            court_num,
            time_str,
        )

        store = self._session_store(context)
        store.selected_date = selected_date
        store.selected_time = time_str

        await self._complete_court_selection(
            query,
            context,
            [court_num],
            user_id=user_id,
        )

    async def handle_matrix_day_cycle(self, update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
        """Cycle to the next available date within the live matrix."""
        t('botapp.handlers.queue.flows.QueueBookingFlow.handle_matrix_day_cycle')

        query = update.callback_query
        await self.answer_callback(query)

        data = query.data or ''
        new_date_str = data.replace('queue_cycle_', '')
        try:
            new_date = datetime.strptime(new_date_str, '%Y-%m-%d').date()
        except ValueError:
            self.logger.error("Invalid queue cycle callback format: %s", data)
            await self.edit_callback(
                query,
                self.messages.invalid_date(),
                reply_markup=TelegramUI.create_back_to_menu_keyboard(),
            )
            return

        store = self._session_store(context)
        store.selected_date = new_date

        tz = self._MEXICO_TZ
        now = datetime.now(tz)
        await self._show_matrix_time_selection(update, context, new_date, tz, now)

    async def cancel(self, update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
        """Cancel queue booking and clean up state."""
        t('botapp.handlers.queue.flows.QueueBookingFlow.cancel')

        query = update.callback_query
        await self.answer_callback(query)

        user_id = (
            query.from_user.id
            if query and getattr(query, 'from_user', None)
            else (update.effective_user.id if update.effective_user else None)
        )
        self.logger.info("QueueBookingFlow.cancel user=%s", user_id)

        _, language = self._translator_for_user(user_id)
        store.clear()
        context.user_data.pop('current_flow', None)

        reply_markup = TelegramUI.create_back_to_menu_keyboard(language=language)
        await self.edit_callback(
            query,
            "⏰ Queue Booking\n\nThe booking process has been cancelled.",
            reply_markup=reply_markup,
        )

    async def handle_blocked_date(self, update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
        """Allow selecting within-48h dates when test mode permits."""
        t('botapp.handlers.queue.flows.QueueBookingFlow.handle_blocked_date')

        query = update.callback_query
        config = self._get_test_mode()

        user_id = (
            query.from_user.id
            if query and getattr(query, 'from_user', None)
            else (update.effective_user.id if update.effective_user else None)
        )
        callback_data = query.data if query else None
        self.logger.info(
            "QueueBookingFlow.handle_blocked_date user=%s callback_data=%s test_mode_enabled=%s allow_within_48h=%s",
            user_id,
            callback_data,
            config.enabled,
            config.allow_within_48h,
        )

        if not (config.enabled and config.allow_within_48h):
            self.logger.info(
                "QueueBookingFlow.handle_blocked_date denied user=%s date_data=%s",
                user_id,
                callback_data,
            )
            await self.edit_callback(
                query,
                "⚠️ This date is within the 48-hour booking window. Enable test mode to queue it.",
                parse_mode='Markdown',
                reply_markup=TelegramUI.create_back_to_menu_keyboard(),
            )
            return

        date_str = query.data.replace('blocked_date_', '')
        try:
            selected_date = datetime.strptime(date_str, '%Y-%m-%d').date()
        except ValueError:
            await self.edit_callback(
                query,
                self.messages.invalid_date(),
                reply_markup=TelegramUI.create_back_to_menu_keyboard(),
            )
            return

        store = self._session_store(context)
        reset_flow(context, 'queue_booking')
        store.selected_date = selected_date
        store.selected_time = None
        store.selected_courts = []
        context.user_data['current_flow'] = 'queue_booking'

        self.logger.info(
            "QueueBookingFlow.handle_blocked_date granted user=%s selected_date=%s",
            user_id,
            selected_date,
        )

        await self._show_time_selection_callback(update, context, selected_date)

    async def back_to_time(self, update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
        """Return the user to the time selection step."""
        t('botapp.handlers.queue.flows.QueueBookingFlow.back_to_time')

        query = update.callback_query
        await self.answer_callback(query)

        user_id = (
            query.from_user.id
            if query and getattr(query, 'from_user', None)
            else (update.effective_user.id if update.effective_user else None)
        )
        self.logger.info("QueueBookingFlow.back_to_time user=%s", user_id)

        store = self._session_store(context)
        selected_date = store.selected_date

        if not selected_date:
            self.logger.error("Missing selected_date when going back to time selection")
            await self.edit_callback(
                query,
                self.messages.session_expired(),
                reply_markup=TelegramUI.create_back_to_menu_keyboard(),
            )
            return

        # Show time selection again for the selected date
        await self._show_time_selection(update, context, selected_date)

    async def back_to_courts(self, update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
        """Return the user to the court selection step."""
        t('botapp.handlers.queue.flows.QueueBookingFlow.back_to_courts')

        query = update.callback_query
        await self.answer_callback(query)

        user_id = (
            query.from_user.id
            if query and getattr(query, 'from_user', None)
            else (update.effective_user.id if update.effective_user else None)
        )
        self.logger.info("QueueBookingFlow.back_to_courts user=%s", user_id)

        store = self._session_store(context)
        selected_date = store.selected_date
        selected_time = store.selected_time

        if not selected_date or not selected_time:
            self.logger.error("Missing booking details when going back to court selection")
            await self.edit_callback(
                query,
                self.messages.session_expired(),
                reply_markup=TelegramUI.create_back_to_menu_keyboard(),
            )
            return

        # Get user language for translated buttons
        user_id = (
            query.from_user.id
            if query and getattr(query, 'from_user', None)
            else None
        )
        language = None
        if user_id:
            user = self.deps.user_manager.get_user(user_id)
            language = user.get('language') if user else None

        from botapp.i18n.translator import create_translator
        translator = create_translator(language)

        reply_markup = TelegramUI.create_queue_court_selection_keyboard(self.AVAILABLE_COURTS, translator=translator)
        await self.edit_callback(
            query,
            f"⏰ **Queue Booking**\n\n"
            f"📅 Date: {selected_date.strftime('%A, %B %d, %Y')}\n"
            f"⏱️ Time: {selected_time}\n\n"
            "🎾 Select your preferred court(s) for the reservation:",
            parse_mode='Markdown',
            reply_markup=reply_markup,
        )

    def clear_state(self, context: ContextTypes.DEFAULT_TYPE) -> None:
        """Remove queue-booking state from the user context."""
        t('botapp.handlers.queue.flows.QueueBookingFlow.clear_state')

        self.logger.info("QueueBookingFlow.clear_state")
        self._session_store(context).clear()
        context.user_data.pop('current_flow', None)

    async def _show_time_selection(
        self,
        update: Update,
        context: ContextTypes.DEFAULT_TYPE,
        selected_date: date,
    ) -> None:
        """Display available time slots for the selected date."""
        t('botapp.handlers.queue.flows.QueueBookingFlow._show_time_selection')

        query = update.callback_query

        user_id = update.effective_user.id if update.effective_user else None
        self.logger.info(
            "QueueBookingFlow._show_time_selection user=%s selected_date=%s",
            user_id,
            selected_date,
        )

        config = self._get_test_mode()
        tz = self._MEXICO_TZ
        now = datetime.now(tz)

        if self._should_use_matrix(selected_date, config, tz, now):
            if await self._show_matrix_time_selection(update, context, selected_date, tz, now):
                return

        time_slots = await self._available_time_slots(context, selected_date)

        self.logger.info(
            "QueueBookingFlow._show_time_selection resolved %s slots for user=%s date=%s",
            len(time_slots) if time_slots else 0,
            user_id,
            selected_date,
        )

        if not time_slots:
            self.logger.info(
                "QueueBookingFlow._show_time_selection no slots available user=%s date=%s",
                user_id,
                selected_date,
            )
            await self.edit_callback(
                query,
                "⏰ Queue Booking\n\n"
                "❌ No time slots available for this date.\n\n"
                "Please pick a different date or try again later.",
                reply_markup=TelegramUI.create_back_to_menu_keyboard(),
            )
            return

        keyboard = TelegramUI.create_queue_time_selection_keyboard(selected_date, time_slots)
        message = TelegramUI.format_queue_time_prompt(selected_date)
        await self.edit_callback(
            query,
            message,
            reply_markup=keyboard,
            parse_mode=ParseMode.MARKDOWN_V2,
        )

    async def _available_time_slots(
        self,
        context: ContextTypes.DEFAULT_TYPE,
        selected_date: date,
    ) -> list[str]:
        """Return available queue time slots respecting test mode rules."""
        t('botapp.handlers.queue.flows.QueueBookingFlow._available_time_slots')

        config = self._get_test_mode()
        tz = self._MEXICO_TZ
        now = datetime.now(tz)
        all_slots = get_court_hours(selected_date)

        self.logger.info(
            "Queue availability requested for %s (test_mode=%s, allow_within_48h=%s)",
            selected_date,
            config.enabled,
            config.allow_within_48h,
        )

        if config.enabled and config.allow_within_48h:
            start_of_day = tz.localize(datetime.combine(selected_date, datetime.min.time()))
            if start_of_day < now + timedelta(hours=48):
                self.logger.info(
                    "Queue attempting live availability lookup for %s (within 48h window)",
                    selected_date,
                )
                live_slots = await fetch_live_time_slots(
                    self.deps,
                    context,
                    selected_date,
                    tz,
                    now,
                    self.logger,
                    log_prefix="Queue",
                )
                if live_slots is not None:
                    self.logger.info(
                        "Queue live availability returned %s slots for %s",
                        len(live_slots),
                        selected_date,
                    )
                    return live_slots
                self.logger.warning(
                    "Queue live availability unavailable for %s; falling back to static timetable",
                    selected_date,
                )

        filtered_slots = self._filter_slots_beyond_48_hours(all_slots, selected_date, tz, now)
        self.logger.info(
            "QueueBookingFlow._available_time_slots fallback returned %s slots for %s",
            len(filtered_slots),
            selected_date,
        )
        return filtered_slots

    def _filter_slots_beyond_48_hours(
        self,
        all_slots: Sequence[str],
        selected_date: date,
        tz,
        now: datetime,
    ) -> list[str]:
        """Return slots that are more than 48 hours away."""
        t('botapp.handlers.queue.flows.QueueBookingFlow._filter_slots_beyond_48_hours')

        filtered: list[str] = []
        for slot_str in all_slots:
            try:
                hour, minute = map(int, slot_str.split(':'))
            except ValueError:
                continue

            slot_dt = datetime.combine(selected_date, datetime.min.time().replace(hour=hour, minute=minute))
            slot_dt = tz.localize(slot_dt)
            if (slot_dt - now).total_seconds() > 48 * 3600:
                filtered.append(slot_str)

        return filtered

    def _date_has_available_slots(self, check_date: date, config, tz, now: datetime) -> bool:
        """Return True if the date has slots respecting the queue rules."""
        t('botapp.handlers.queue.flows.QueueBookingFlow._date_has_available_slots')

        if config.enabled and config.allow_within_48h:
            return True

        for hour_str in get_court_hours(check_date):
            try:
                hour, minute = map(int, hour_str.split(':'))
            except ValueError:
                continue

            slot_dt = datetime.combine(check_date, datetime.min.time().replace(hour=hour, minute=minute))
            slot_dt = tz.localize(slot_dt)
            if (slot_dt - now).total_seconds() > 48 * 3600:
                return True

        return False

    @staticmethod
    def _format_date_label(candidate: date, today: date) -> str:
        t('botapp.handlers.queue.flows.QueueBookingFlow._format_date_label')
        if candidate == today:
            return f"Today ({candidate.strftime('%b %d')})"
        if candidate == today + timedelta(days=1):
            return f"Tomorrow ({candidate.strftime('%b %d')})"
        return candidate.strftime("%a, %b %d")

    def _should_use_matrix(self, selected_date: date, config, tz, now: datetime) -> bool:
        t('botapp.handlers.queue.flows.QueueBookingFlow._should_use_matrix')
        if not (config.enabled and config.allow_within_48h):
            return False
        start_of_day = tz.localize(datetime.combine(selected_date, datetime.min.time()))
        return start_of_day < now + timedelta(hours=48)

    async def _show_matrix_time_selection(
        self,
        update: Update,
        context: ContextTypes.DEFAULT_TYPE,
        selected_date: date,
        tz,
        now: datetime,
    ) -> bool:
        """Render the matrix availability keyboard; return True if handled."""
        t('botapp.handlers.queue.flows.QueueBookingFlow._show_matrix_time_selection')

        query = update.callback_query

        matrix = await fetch_live_availability_matrix(
            self.deps,
            context,
            tz,
            now,
            self.logger,
            cache_key='queue_live_matrix',
            log_prefix='Queue',
        )
        if matrix is None:
            return False

        context.user_data['queue_live_matrix'] = matrix
        available_dates = sorted(matrix.keys())
        context.user_data['queue_available_dates'] = available_dates

        store = self._session_store(context)
        store.selected_date = selected_date

        date_key = selected_date.isoformat()
        available_times = matrix.get(date_key, {})
        if not available_times:
            self.logger.info(
                "QueueBookingFlow._show_matrix_time_selection no slots for %s",
                date_key,
            )
            await self.edit_callback(
                query,
                TelegramUI.format_queue_no_times(selected_date),
                parse_mode=ParseMode.MARKDOWN_V2,
                reply_markup=TelegramUI.create_back_to_menu_keyboard(),
            )
            return True

        total_slots = sum(len(times) for times in available_times.values())
        message = TelegramUI.format_interactive_availability_message(
            available_times,
            selected_date,
            total_slots,
            layout_type='matrix',
        )

        keyboard = TelegramUI.create_court_availability_keyboard(
            available_times,
            date_key,
            layout_type='matrix',
            available_dates=available_dates,
            callback_prefix='queue_matrix',
            cycle_prefix='queue_cycle_',
        )

        await self.edit_callback(
            query,
            message,
            reply_markup=keyboard,
            parse_mode=ParseMode.MARKDOWN_V2,
        )
        return True

    async def _present_court_selection(
        self,
        query,
        selected_date: date,
        selected_time: str,
    ) -> None:
        # Get user language for translated buttons
        t('botapp.handlers.queue.flows.QueueBookingFlow._present_court_selection')
        user_id = (
            query.from_user.id
            if query and getattr(query, 'from_user', None)
            else None
        )
        language = None
        if user_id:
            user = self.deps.user_manager.get_user(user_id)
            language = user.get('language') if user else None

        from botapp.i18n.translator import create_translator
        translator = create_translator(language)

        reply_markup = TelegramUI.create_queue_court_selection_keyboard(self.AVAILABLE_COURTS, translator=translator)
        await self.edit_callback(
            query,
            TelegramUI.format_queue_court_selection_prompt(selected_date, selected_time),
            parse_mode=ParseMode.MARKDOWN_V2,
            reply_markup=reply_markup,
        )

    async def _complete_court_selection(
        self,
        query,
        context: ContextTypes.DEFAULT_TYPE,
        cleaned_courts: Sequence[int],
        *,
        user_id: int | None = None,
    ) -> None:
        t('botapp.handlers.queue.flows.QueueBookingFlow._complete_court_selection')
        store = self._session_store(context)
        if user_id is None:
            user_id = (
                query.from_user.id
                if query and getattr(query, 'from_user', None)
                else None
            )

        modifying_id, modifying_option = store.modification
        if modifying_id and modifying_option == 'courts':
            reservation = self.deps.reservation_queue.get_reservation(modifying_id)
            if reservation:
                reservation['court_preferences'] = list(cleaned_courts)
                self.deps.reservation_queue.update_reservation(modifying_id, reservation)

                store.set_modification(None, None)

                courts_text = format_court_preferences(cleaned_courts, self.AVAILABLE_COURTS)
                await self.edit_callback(
                    query,
                    self.messages.courts_updated(courts_text),
                    parse_mode='Markdown',
                    reply_markup=InlineKeyboardMarkup([
                        [InlineKeyboardButton("📋 View Reservation", callback_data=f"manage_queue_{modifying_id}")],
                        [InlineKeyboardButton("🏠 Main Menu", callback_data='back_to_menu')],
                    ]),
                )
                return

        cleaned_list = normalize_court_sequence(
            cleaned_courts,
            allowed=self.AVAILABLE_COURTS,
        )
        store.selected_courts = cleaned_list

        selected_date = store.selected_date
        selected_time = store.selected_time

        self.logger.info(
            "QueueBookingFlow.select_courts context user=%s date=%s time=%s",
            user_id,
            selected_date,
            selected_time,
        )

        if not selected_date or not selected_time:
            self.logger.error("Missing booking details in user context")
            await self.edit_callback(query, self.messages.session_expired())
            return

        if user_id is None and query and getattr(query, 'from_user', None):
            user_id = query.from_user.id

        _, language = self._translator_for_user(user_id)

        user_profile = self.deps.user_manager.get_user(user_id) if user_id is not None else {}
        required_fields = ('first_name', 'last_name', 'email', 'phone')

        try:
            ensure_profile_fields(user_profile, required_fields)
        except IncompleteProfileError as exc:
            missing = ', '.join(exc.missing_fields)
            self.logger.warning(
                "User %s missing required fields for queued booking: %s",
                user_id,
                missing,
            )
            reply_markup = TelegramUI.create_profile_keyboard()
            await self.edit_callback(
                query,
                self.messages.profile_incomplete(exc.missing_fields),
                parse_mode='Markdown',
                reply_markup=reply_markup,
            )
            return

        store.summary = {
            'user_id': user_id,
            'first_name': user_profile.get('first_name'),
            'last_name': user_profile.get('last_name'),
            'email': user_profile.get('email'),
            'phone': user_profile.get('phone'),
            'tier': user_profile.get('tier_name') or user_profile.get('tier'),
            'target_date': selected_date.strftime('%Y-%m-%d'),
            'target_time': selected_time,
            'court_preferences': cleaned_list,
            'created_at': datetime.now().isoformat(),
        }

        self.logger.info(
            "QueueBookingFlow.select_courts summary ready user=%s date=%s time=%s courts=%s",
            user_id,
            store.summary['target_date'],
            store.summary['target_time'],
            cleaned_list,
        )

        reply_markup = TelegramUI.create_queue_confirmation_keyboard(language=language)
        courts_text = format_court_preferences(cleaned_list, self.AVAILABLE_COURTS)
        await self.edit_callback(
            query,
            TelegramUI.format_queue_confirmation_message(
                selected_date,
                selected_time,
                courts_text,
            ),
            parse_mode=ParseMode.MARKDOWN_V2,
            reply_markup=reply_markup,
        )


class QueueReservationManager(QueueFlowBase):
    """Encapsulates reservation viewing and modification flows."""

    def __init__(
        self,
        deps,
        messages: QueueMessageFactory,
        safe_answer: SafeAnswer,
        edit_message: EditCallback,
        get_test_mode,
        *,
        request_builder: ReservationRequestBuilder | None = None,
    ) -> None:
        t('botapp.handlers.queue.flows.QueueReservationManager.__init__')
        super().__init__(
            deps,
            messages,
            safe_answer,
            edit_message,
            request_builder=request_builder,
        )
        self._get_test_mode = get_test_mode

    async def show_user_menu(self, update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
        """Display the queued reservations menu for the current user."""
        t('botapp.handlers.queue.flows.QueueReservationManager.show_user_menu')

        query = update.callback_query
        await self.answer_callback(query)
        user_id = query.from_user.id

        self.logger.info("QueueReservationManager.show_user_menu user=%s", user_id)

        try:
            reservations = self.deps.reservation_queue.get_user_reservations(user_id)
        except Exception as exc:
            self.logger.exception("Failed to load queued reservations for %s", user_id)
            await ErrorHandler.handle_booking_error(
                update,
                context,
                'system_error',
                'Failed to retrieve reservations',
            )
            return

        self.logger.info(
            "QueueReservationManager.show_user_menu loaded %s reservations for user=%s",
            len(reservations),
            user_id,
        )

        # Get user language
        user = self.deps.user_manager.get_user(user_id) if user_id else None
        language = user.get('language') if user else None
        from botapp.i18n.translator import create_translator
        tr = create_translator(language)

        if not reservations:
            await self.edit_callback(
                query,
                f"{tr.t('booking.queue_empty_title')}\n\n"
                f"{tr.t('booking.queue_empty_message')}\n\n"
                f"{tr.t('booking.queue_empty_cta')}",
                parse_mode='Markdown',
                reply_markup=TelegramUI.create_back_to_menu_keyboard(language=language),
            )
            return

        reservations.sort(key=lambda item: (item.get('target_date', ''), item.get('target_time', '')))

        message = [
            f"{tr.t('booking.queue_title')}\n",
            f"{tr.t('booking.queue_count', count=len(reservations))}\n",
            f"{tr.t('booking.queue_prompt')}\n",
        ]

        keyboard: list[list[InlineKeyboardButton]] = []
        for reservation in reservations:
            date_str = reservation.get('target_date', 'Unknown')
            if date_str not in ('', 'Unknown'):
                try:
                    date_obj = datetime.strptime(date_str, '%Y-%m-%d')
                    day = date_obj.day
                    if 10 <= day % 100 <= 20:
                        suffix = 'th'
                    else:
                        suffix = {1: 'st', 2: 'nd', 3: 'rd'}.get(day % 10, 'th')
                    date_str = date_obj.strftime(f'%b {day}{suffix} %Y')
                except Exception:  # pragma: no cover - defensive formatting guard
                    pass

            time_str = reservation.get('target_time', 'Unknown')
            courts = reservation.get('court_preferences', [])
            status = reservation.get('status', 'pending')

            if courts:
                if len(courts) == 3:
                    court_str = "All Courts"
                else:
                    court_str = f"Court{'s' if len(courts) > 1 else ''} {', '.join(map(str, courts))}"
            else:
                court_str = "No courts"

            status_emoji = {
                'pending': '⏳',
                'scheduled': '🔄',
                'completed': '✅',
                'failed': '❌',
            }.get(status, '❓')

            button_text = f"{status_emoji} {date_str} {time_str} - {court_str}"
            keyboard.append([
                InlineKeyboardButton(button_text, callback_data=f"manage_queue_{reservation['id']}")
            ])

        keyboard.append([InlineKeyboardButton("⬅️ Back to Menu", callback_data='back_to_menu')])

        await self.edit_callback(
            query,
            ''.join(message),
            parse_mode='Markdown',
            reply_markup=InlineKeyboardMarkup(keyboard),
        )

    async def manage_reservation(self, update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
        """Show a combined reservation view with actions for the user."""
        t('botapp.handlers.queue.flows.QueueReservationManager.manage_reservation')

        query = update.callback_query
        await self.answer_callback(query)
        reservation_id = query.data.replace('manage_res_', '')
        user_id = query.from_user.id

        self.logger.info(
            "QueueReservationManager.manage_reservation user=%s reservation_id=%s",
            user_id,
            reservation_id,
        )

        try:
            reservation = self._get_queue_reservation(reservation_id, user_id)
            if not reservation and hasattr(self.deps, 'reservation_tracker'):
                reservation = self._get_tracker_reservation(reservation_id, user_id)

            if not reservation:
                await self.edit_callback(
                    query,
                    "❌ Reservation not found.\n\nIt may have been cancelled or expired.",
                    reply_markup=TelegramUI.create_back_to_menu_keyboard(),
                )
                return

            message, keyboard = self._reservation_detail_view(reservation, reservation_id)
            await self.edit_callback(
                query,
                message,
                parse_mode='Markdown',
                reply_markup=InlineKeyboardMarkup(keyboard),
            )

        except Exception as exc:
            self.logger.error("Error managing reservation %s: %s", reservation_id, exc)
            await self.edit_callback(
                query,
                self.messages.reservation_details_error(),
                reply_markup=TelegramUI.create_back_to_menu_keyboard(),
            )

    async def manage_queue_reservation(self, update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
        """Show details for a queued reservation with modification options."""
        t('botapp.handlers.queue.flows.QueueReservationManager.manage_queue_reservation')

        query = update.callback_query
        await self.answer_callback(query)
        reservation_id = query.data.replace('manage_queue_', '')

        try:
            reservation = self.deps.reservation_queue.get_reservation(reservation_id)
        except Exception as exc:
            self.logger.error("Error fetching queued reservation %s: %s", reservation_id, exc)
            reservation = None

        if not reservation:
            await self.edit_callback(
                query,
                "❌ Reservation not found.",
                reply_markup=TelegramUI.create_back_to_menu_keyboard(),
            )
            return

        message, keyboard = self._queued_reservation_view(reservation, reservation_id)
        await self.edit_callback(
            query,
            message,
            parse_mode='Markdown',
            reply_markup=InlineKeyboardMarkup(keyboard),
        )

    async def handle_action(self, update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
        """Dispatch reservation actions (cancel, modify, share)."""
        t('botapp.handlers.queue.flows.QueueReservationManager.handle_action')

        query = update.callback_query
        await self.answer_callback(query)
        callback_data = query.data

        try:
            _, _, action, *rest = callback_data.split('_')
        except ValueError:
            self.logger.warning("Invalid reservation action callback: %s", callback_data)
            await query.answer("Unknown action")
            return

        reservation_id = '_'.join(rest)

        if action == 'cancel':
            await self.cancel_reservation(update, context, reservation_id)
        elif action == 'modify':
            await self.modify_reservation(update, context, reservation_id)
        elif action == 'share':
            await self.share_reservation(update, context, reservation_id)
        else:
            self.logger.warning("Unknown reservation action: %s", action)
            await query.answer("Unknown action")

    async def cancel_reservation(
        self,
        update: Update,
        context: ContextTypes.DEFAULT_TYPE,
        reservation_id: str,
    ) -> None:
        """Cancel a reservation owned by the current user."""
        t('botapp.handlers.queue.flows.QueueReservationManager.cancel_reservation')

        query = update.callback_query
        await self.answer_callback(query)
        user_id = query.from_user.id

        try:
            cancelled = False
            reservation = self.deps.reservation_queue.get_reservation(reservation_id)
            if reservation and reservation.get('user_id') == user_id:
                cancelled = self.deps.reservation_queue.remove_reservation(reservation_id)

            if not cancelled and hasattr(self.deps, 'reservation_tracker'):
                tracker = getattr(self.deps, 'reservation_tracker')
                reservation = tracker.get_reservation(reservation_id)
                if reservation and reservation.get('user_id') == user_id:
                    cancelled = tracker.cancel_reservation(reservation_id)

            if cancelled:
                await self.edit_callback(
                    query,
                    self.messages.reservation_cancelled(),
                    parse_mode='Markdown',
                    reply_markup=InlineKeyboardMarkup([
                        [InlineKeyboardButton("📅 View Reservations", callback_data='menu_reservations')],
                        [InlineKeyboardButton("🏠 Main Menu", callback_data='back_to_menu')],
                    ]),
                )
            else:
                await query.answer("Could not cancel reservation")

        except Exception as exc:
            self.logger.error("Error cancelling reservation %s: %s", reservation_id, exc)
            await query.answer("Error cancelling reservation")

    async def modify_reservation(
        self,
        update: Update,
        context: ContextTypes.DEFAULT_TYPE,
        reservation_id: str,
    ) -> None:
        """Initiate modification flow for a queued reservation."""
        t('botapp.handlers.queue.flows.QueueReservationManager.modify_reservation')

        query = update.callback_query
        await self.answer_callback(query)
        user_id = query.from_user.id
        store = self._session_store(context)

        reservation = self.deps.reservation_queue.get_reservation(reservation_id)
        is_queued = bool(reservation and reservation.get('user_id') == user_id)

        if not reservation and hasattr(self.deps, 'reservation_tracker'):
            tracker_res = self.deps.reservation_tracker.get_reservation(reservation_id)
            if tracker_res and tracker_res.get('user_id') == user_id:
                reservation = tracker_res

        if not reservation:
            await query.answer("Reservation not found")
            return

        if is_queued:
            store.set_modification(reservation_id, None)
            keyboard = [
                [InlineKeyboardButton("📅 Change Date", callback_data=f"modify_date_{reservation_id}")],
                [InlineKeyboardButton("⏰ Change Time", callback_data=f"modify_time_{reservation_id}")],
                [InlineKeyboardButton("🏃 Change Courts", callback_data=f"modify_courts_{reservation_id}")],
                [InlineKeyboardButton("⬅️ Back", callback_data=f"manage_queue_{reservation_id}")],
                [InlineKeyboardButton("🏠 Main Menu", callback_data='back_to_menu')],
            ]

            await self.edit_callback(
                query,
                self.messages.modification_prompt(),
                parse_mode='Markdown',
                reply_markup=InlineKeyboardMarkup(keyboard),
            )
            return

        await self.edit_callback(
            query,
            self.messages.modification_unavailable(),
            parse_mode='Markdown',
            reply_markup=InlineKeyboardMarkup([
                [InlineKeyboardButton("❌ Cancel Reservation", callback_data=f"res_action_cancel_{reservation_id}")],
                [InlineKeyboardButton("⬅️ Back", callback_data=f"manage_queue_{reservation_id}")],
                [InlineKeyboardButton("🏠 Main Menu", callback_data='back_to_menu')],
            ]),
        )

    async def share_reservation(
        self,
        update: Update,
        context: ContextTypes.DEFAULT_TYPE,
        reservation_id: str,
    ) -> None:
        """Send a shareable reservation message to the user."""
        t('botapp.handlers.queue.flows.QueueReservationManager.share_reservation')

        query = update.callback_query
        await self.answer_callback(query)
        user_id = query.from_user.id

        reservation = self.deps.reservation_queue.get_reservation(reservation_id)
        if not reservation and hasattr(self.deps, 'reservation_tracker'):
            reservation = self.deps.reservation_tracker.get_reservation(reservation_id)

        if not reservation or reservation.get('user_id') != user_id:
            await query.answer("Reservation not found")
            return

        date_str = reservation.get('target_date', reservation.get('date', 'Unknown'))
        time_str = reservation.get('target_time', reservation.get('time', 'Unknown'))
        courts = reservation.get('court_preferences', reservation.get('court', 'TBD'))

        if isinstance(courts, list):
            court_str = f"Courts {', '.join(map(str, courts))}"
        else:
            court_str = f"Court {courts}"

        share_text = (
            "🎾 Tennis Reservation\n"
            f"📅 {date_str} at {time_str}\n"
            f"📍 Club La Villa - {court_str}\n"
        )

        keyboard = [[InlineKeyboardButton("⬅️ Back to reservation", callback_data=f"manage_queue_{reservation_id}")]]

        await context.bot.send_message(
            chat_id=user_id,
            text=share_text,
            reply_markup=InlineKeyboardMarkup(keyboard),
        )

        await query.answer("📤 Reservation details sent! You can forward the message.")

    async def modify_option(self, update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
        """Handle the intermediate modification option selection."""
        t('botapp.handlers.queue.flows.QueueReservationManager.modify_option')

        query = update.callback_query
        await self.answer_callback(query)
        data = query.data
        from_user = getattr(query, 'from_user', None)
        user_id = from_user.id if from_user else None
        _, language = self._translator_for_user(user_id)
        store = self._session_store(context)

        if data.startswith('modify_date_'):
            option = 'date'
            reservation_id = data.replace('modify_date_', '')
        elif data.startswith('modify_time_'):
            option = 'time'
            reservation_id = data.replace('modify_time_', '')
        elif data.startswith('modify_courts_'):
            option = 'courts'
            reservation_id = data.replace('modify_courts_', '')
        else:
            return

        store.set_modification(reservation_id, option)
        reservation = self.deps.reservation_queue.get_reservation(reservation_id)
        if not reservation:
            await query.answer("Reservation not found")
            return

        if option == 'date':
            keyboard = TelegramUI.create_year_selection_keyboard(language=language)
            await self.edit_callback(
                query,
                "📅 **Select New Year**\n\nChoose the year for your reservation:",
                parse_mode='Markdown',
                reply_markup=keyboard,
            )
        elif option == 'time':
            keyboard = TelegramUI.create_time_selection_keyboard_simple(
                reservation.date,
                language=language,
            )
            await self.edit_callback(
                query,
                "⏰ **Select New Time**\n\nChoose your preferred time:",
                parse_mode='Markdown',
                reply_markup=keyboard,
            )
        elif option == 'courts':
            keyboard = TelegramUI.create_court_selection_keyboard()
            await self.edit_callback(
                query,
                "🏃 **Select New Courts**\n\nChoose your court preferences:",
                parse_mode='Markdown',
                reply_markup=keyboard,
            )

    async def time_modification(self, update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
        """Apply a time change for the queued reservation under modification."""
        t('botapp.handlers.queue.flows.QueueReservationManager.time_modification')

        query = update.callback_query
        await self.answer_callback(query)
        time_str = query.data.replace('queue_time_modify_', '')
        store = self._session_store(context)

        try:
            modifying_id, _ = ensure_modification(context)
        except MissingModificationContextError:
            await query.answer(self.messages.session_expired_retry())
            return

        reservation = self.deps.reservation_queue.get_reservation(modifying_id)
        if reservation:
            reservation['target_time'] = time_str
            self.deps.reservation_queue.update_reservation(modifying_id, reservation)

        store.set_modification(None, None)

        await self.edit_callback(
            query,
            self.messages.time_updated(time_str),
            parse_mode='Markdown',
            reply_markup=InlineKeyboardMarkup([
                [InlineKeyboardButton("📋 View Reservation", callback_data=f"manage_queue_{modifying_id}")],
                [InlineKeyboardButton("🏠 Main Menu", callback_data='back_to_menu')],
            ]),
        )

    def _get_queue_reservation(self, reservation_id: str, user_id: int) -> dict[str, Any] | None:
        t('botapp.handlers.queue.flows.QueueReservationManager._get_queue_reservation')
        reservation = self.deps.reservation_queue.get_reservation(reservation_id)
        if reservation and reservation.get('user_id') == user_id:
            reservation = dict(reservation)
            reservation['source'] = 'queue'
            return reservation
        return None

    def _get_tracker_reservation(self, reservation_id: str, user_id: int) -> dict[str, Any] | None:
        t('botapp.handlers.queue.flows.QueueReservationManager._get_tracker_reservation')
        tracker = getattr(self.deps, 'reservation_tracker', None)
        if not tracker:
            return None
        reservation = tracker.get_reservation(reservation_id)
        if reservation and reservation.get('user_id') == user_id:
            reservation = dict(reservation)
            reservation['source'] = 'tracker'
            return reservation
        return None

    def _reservation_detail_view(
        self,
        reservation: Mapping[str, Any],
        reservation_id: str,
    ) -> tuple[str, list[list[InlineKeyboardButton]]]:
        t('botapp.handlers.queue.flows.QueueReservationManager._reservation_detail_view')
        date_str = reservation.get('target_date', reservation.get('date', 'Unknown'))
        formatted_date = self._format_date_with_suffix(date_str)
        time_str = reservation.get('target_time', reservation.get('time', 'Unknown'))
        courts = reservation.get('court_preferences', reservation.get('court', 'TBD'))
        status = reservation.get('status', 'pending')
        court_str = self._format_court_string(courts)

        message = (
            "📋 **Reservation Details**\n\n"
            f"📅 Date: {formatted_date}\n"
            f"⏰ Time: {time_str}\n"
            f"🎾 {court_str}\n"
            f"📊 Status: {status.capitalize()}\n"
        )

        if reservation.get('confirmation_id'):
            message += f"🔖 Confirmation: {reservation['confirmation_id']}\n"

        # Simple navigation-only keyboard (edit/cancel actions are in Queued Reservations menu)
        keyboard: list[list[InlineKeyboardButton]] = [
            [
                InlineKeyboardButton("⬅️ Back to Reservations", callback_data='menu_reservations'),
                InlineKeyboardButton("🏠 Main Menu", callback_data='back_to_menu'),
            ]
        ]

        return message, keyboard

    def _queued_reservation_view(
        self,
        reservation: Mapping[str, Any],
        reservation_id: str,
    ) -> tuple[str, list[list[InlineKeyboardButton]]]:
        t('botapp.handlers.queue.flows.QueueReservationManager._queued_reservation_view')
        target_date = datetime.strptime(reservation['target_date'], '%Y-%m-%d')
        formatted_date = self._format_date_object(target_date)
        time_str = reservation['target_time']
        courts = reservation.get('court_preferences', [])
        court_str = ', '.join(map(str, courts)) if courts else 'No courts'

        message = (
            "📋 **Queued Reservation**\n\n"
            f"📅 Date: {formatted_date}\n"
            f"⏰ Time: {time_str}\n"
            f"🎾 Courts: {court_str or 'TBD'}\n"
        )

        config = self._get_test_mode()
        if config.enabled:
            message += (
                f"🧪 *TEST MODE:* Will execute in {config.trigger_delay_minutes} minutes after creation\n"
            )
        else:
            message += (
                "This reservation will be automatically booked when the 48-hour booking window opens.\n"
            )

        keyboard = [
            [InlineKeyboardButton("❌ Cancel Reservation", callback_data=f"res_action_cancel_{reservation_id}")],
            [InlineKeyboardButton("✏️ Modify Reservation", callback_data=f"res_action_modify_{reservation_id}")],
            [InlineKeyboardButton("📤 Share Details", callback_data=f"res_action_share_{reservation_id}")],
            [InlineKeyboardButton("⬅️ Back to Reservations", callback_data='menu_reservations')],
            [InlineKeyboardButton("🏠 Main Menu", callback_data='back_to_menu')],
        ]

        return message, keyboard

    @staticmethod
    def _format_court_string(courts: Any) -> str:
        t('botapp.handlers.queue.flows.QueueReservationManager._format_court_string')
        if isinstance(courts, list):
            if len(courts) == 3:
                return "Courts 1, 2, 3"
            return f"Courts {', '.join(map(str, courts))}"
        if courts:
            return f"Court {courts}"
        return "No courts"

    @staticmethod
    def _format_date_with_suffix(date_str: str) -> str:
        t('botapp.handlers.queue.flows.QueueReservationManager._format_date_with_suffix')
        try:
            date_obj = datetime.strptime(date_str, '%Y-%m-%d')
        except Exception:
            return date_str
        return QueueReservationManager._format_date_object(date_obj)

    @staticmethod
    def _format_date_object(date_obj: datetime) -> str:
        t('botapp.handlers.queue.flows.QueueReservationManager._format_date_object')
        day = date_obj.day
        if 10 <= day % 100 <= 20:
            suffix = 'th'
        else:
            suffix = {1: 'st', 2: 'nd', 3: 'rd'}.get(day % 10, 'th')
        return date_obj.strftime(f'%B {day}{suffix}, %Y')

    async def display_user_reservations(
        self,
        update: Update,
        context: ContextTypes.DEFAULT_TYPE,
        target_user_id: int,
    ) -> None:
        """Display reservations for a specific user (admin helper)."""
        t('botapp.handlers.queue.flows.QueueReservationManager.display_user_reservations')

        query = update.callback_query
        await self.answer_callback(query)

        try:
            all_reservations: list[dict[str, Any]] = []
            queued = self.deps.reservation_queue.get_user_reservations(target_user_id)
            for res in queued:
                copy = dict(res)
                copy['source'] = 'queue'
                all_reservations.append(copy)

            tracker = getattr(self.deps, 'reservation_tracker', None)
            if tracker:
                active = tracker.get_user_active_reservations(target_user_id)
                for res in active:
                    copy = dict(res)
                    copy['source'] = 'tracker'
                    all_reservations.append(copy)

            user_name = self._get_user_name(target_user_id)

            if not all_reservations:
                await self.edit_callback(
                    query,
                    f"📅 **Reservations for {user_name}**\n\nNo active reservations found.",
                    parse_mode='Markdown',
                    reply_markup=InlineKeyboardMarkup([
                        [InlineKeyboardButton("⬅️ Back", callback_data='admin_view_users_list')],
                        [InlineKeyboardButton("🏠 Main Menu", callback_data='back_to_menu')],
                    ]),
                )
                return

            all_reservations.sort(
                key=lambda res: (
                    res.get('target_date', res.get('date', '')),
                    res.get('target_time', res.get('time', '')),
                )
            )

            keyboard: list[list[InlineKeyboardButton]] = []
            message = f"📅 **Reservations for {user_name}**\n\n"

            for res in all_reservations:
                date_obj = DateTimeHelpers.parse_date_string(res.get('target_date', res.get('date', '')))
                if date_obj:
                    day = date_obj.day
                    if 10 <= day % 100 <= 20:
                        suffix = 'th'
                    else:
                        suffix = {1: 'st', 2: 'nd', 3: 'rd'}.get(day % 10, 'th')
                    date_str = date_obj.strftime(f'%b {day}{suffix} %Y')
                else:
                    date_str = res.get('target_date', res.get('date', 'Unknown'))

                time_str = res.get('target_time', res.get('time', 'Unknown'))
                courts = res.get('court_preferences', res.get('court', 'TBD'))
                court_str = ', '.join([f"C{c}" for c in courts]) if isinstance(courts, list) else f"C{courts}"
                status = res.get('status', 'pending')
                status_emoji = "✅" if status == 'confirmed' else "⏳"

                button_text = f"{status_emoji} {date_str} {time_str} - {court_str}"
                res_id = res.get('id', f"{res.get('date')}_{res.get('time')}")
                keyboard.append([
                    InlineKeyboardButton(button_text, callback_data=f"manage_queue_{res_id}")
                ])

            keyboard.extend([
                [InlineKeyboardButton("⬅️ Back", callback_data='admin_view_users_list')],
                [InlineKeyboardButton("🏠 Main Menu", callback_data='back_to_menu')],
            ])

            await self.edit_callback(
                query,
                message,
                parse_mode='Markdown',
                reply_markup=InlineKeyboardMarkup(keyboard),
            )

        except Exception as exc:
            self.logger.error(
                "Error displaying reservations for user %s: %s", target_user_id, exc
            )
            await self.edit_callback(
                query,
                self.messages.reservation_list_error(),
                reply_markup=TelegramUI.create_back_to_menu_keyboard(),
            )

    async def display_all_reservations(
        self,
        query,
        all_reservations: list[dict[str, Any]],
    ) -> None:
        """Render all reservations grouped by date."""
        t('botapp.handlers.queue.flows.QueueReservationManager.display_all_reservations')

        message_lines = ["📊 **All Reservations**\n\n"]
        reservations_by_date: dict[str, list[dict[str, Any]]] = {}
        for res in all_reservations:
            date_key = res.get('target_date', res.get('date', 'Unknown'))
            reservations_by_date.setdefault(date_key, []).append(res)

        for date_str in sorted(reservations_by_date.keys()):
            try:
                date_obj = DateTimeHelpers.parse_date_string(date_str)
                if date_obj:
                    message_lines.append(f"**{self._format_date_object(date_obj).replace(',', '')}**\n")
                else:
                    message_lines.append(f"**{date_str}**\n")
            except Exception:
                message_lines.append(f"**{date_str}**\n")

            for res in reservations_by_date[date_str]:
                time_str = res.get('target_time', res.get('time', 'Unknown'))
                courts = res.get('court_preferences', res.get('court', 'TBD'))
                court_str = (
                    ', '.join([f"C{c}" for c in courts]) if isinstance(courts, list) else f"C{courts}"
                )
                user_name = res.get('user_name', 'Unknown')
                status = res.get('status', 'pending')
                status_emoji = "✅" if status == 'confirmed' else "⏳"
                message_lines.append(f"  {status_emoji} {time_str} - {court_str} - {user_name}\n")

            message_lines.append("\n")

        await self.edit_callback(
            query,
            ''.join(message_lines),
            parse_mode='Markdown',
            reply_markup=InlineKeyboardMarkup([
                [InlineKeyboardButton("⬅️ Back", callback_data='menu_reservations')],
                [InlineKeyboardButton("🏠 Main Menu", callback_data='back_to_menu')],
            ]),
        )

    def _get_user_name(self, user_id: int) -> str:
        t('botapp.handlers.queue.flows.QueueReservationManager._get_user_name')
        user = self.deps.user_manager.get_user(user_id)
        if not user:
            return f"User {user_id}"
        first = user.get('first_name') or ''
        last = user.get('last_name') or ''
        full = f"{first} {last}".strip()
        return full or user.get('username') or f"User {user_id}"
