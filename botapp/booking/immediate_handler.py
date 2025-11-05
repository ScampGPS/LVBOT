"""
Immediate booking handler for direct court reservations
Manages the flow from availability display to booking execution
"""
from tracking import t

from typing import Dict, Any, Optional, Callable
from datetime import datetime, date
from telegram import Update
from telegram.ext import ContextTypes
import asyncio
import logging

from automation.executors import AsyncExecutorConfig, UnifiedAsyncBookingExecutor
from automation.executors.request_factory import build_booking_result_from_execution
from automation.shared.booking_contracts import BookingRequest, BookingResult

from ..callbacks.parser import CallbackParser
from ..ui.confirmation_ui import build_immediate_confirmation_ui
from ..ui.telegram_ui import TelegramUI
from .request_builder import build_immediate_booking_request
from .persistence import persist_immediate_failure, persist_immediate_success
from ..notifications import send_failure_notification, send_success_notification

logger = logging.getLogger(__name__)


class ImmediateBookingHandler:
    """
    Handles immediate booking flow from court availability display
    
    Responsibilities:
    - Parse booking callbacks
    - Validate user and booking data
    - Show confirmation UI
    - Execute bookings
    - Format results
    """
    
    def __init__(self, user_manager, browser_pool=None):
        """
        Initialize handler with dependencies
        
        Args:
            user_manager: User management interface for retrieving user data
            browser_pool: Optional browser pool for optimized execution
        """
        t('botapp.booking.immediate_handler.ImmediateBookingHandler.__init__')
        self.user_manager = user_manager
        self.browser_pool = browser_pool
        self.parser = CallbackParser()
        self.logger = logging.getLogger(self.__class__.__name__)
    
    async def handle_booking_request(self, update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
        """
        Handle initial booking request when user clicks a time slot
        
        Shows confirmation dialog with booking details
        
        Args:
            update: Telegram update with callback query
            context: Callback context
        """
        t('botapp.booking.immediate_handler.ImmediateBookingHandler.handle_booking_request')
        query = update.callback_query
        await query.answer()
        
        # Parse callback data
        parsed = self.parser.parse_booking_callback(query.data)
        if not parsed or parsed['action'] != 'book_now':
            await self._send_error(query, "Invalid booking format")
            return
        
        # Get user info
        user = self._fetch_user_profile(query.from_user.id)
        if not user:
            await query.edit_message_text(
                TelegramUI.format_error_message('profile_incomplete'),
                reply_markup=TelegramUI.create_back_to_menu_keyboard()
            )
            return
        
        # Create confirmation UI
        confirm_ui = build_immediate_confirmation_ui(self.parser, parsed, user)

        await query.edit_message_text(
            confirm_ui['message'],
            parse_mode='Markdown',
            reply_markup=confirm_ui['keyboard']
        )
    
    async def handle_booking_confirmation(self, update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
        """
        Execute booking after user confirmation
        
        Args:
            update: Telegram update with callback query
            context: Callback context
        """
        t('botapp.booking.immediate_handler.ImmediateBookingHandler.handle_booking_confirmation')
        query = update.callback_query
        await query.answer()
        
        # Parse callback data
        parsed = self.parser.parse_booking_callback(query.data)
        if not parsed or parsed['action'] != 'confirm':
            await self._send_error(query, "Invalid confirmation format")
            return
        
        user_profile = self._fetch_user_profile(query.from_user.id)
        if not user_profile:
            await self._send_error(query, "User profile incomplete")
            return

        try:
            booking_request = build_immediate_booking_request(
                user_profile,
                target_date=parsed['date'],
                time_slot=parsed['time'],
                court_number=parsed['court_number'],
                metadata={
                    'trigger': 'immediate_handler',
                    'callback_action': parsed['action'],
                    'telegram_user_id': query.from_user.id,
                },
            )
        except ValueError as exc:
            self.logger.error("Failed to build booking request: %s", exc)
            await self._send_error(query, str(exc))
            return

        await query.edit_message_text("🔄 Processing your booking, please wait...")

        try:
            booking_result = await self._run_booking_attempts(booking_request)
        except Exception as exc:  # pragma: no cover - defensive guard
            self.logger.error("Booking execution error: %s", exc)
            booking_result = BookingResult.failure_result(
                booking_request.user,
                booking_request.request_id,
                message=str(exc),
                metadata={**booking_request.metadata, 'exception': str(exc)},
            )

        if booking_result.success:
            await self._handle_successful_booking(query, booking_request, booking_result)
        else:
            await self._handle_failed_booking(query, booking_request, booking_result)
    
    async def handle_booking_cancellation(self, update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
        """
        Handle booking cancellation - return to availability view
        
        Args:
            update: Telegram update with callback query
            context: Callback context
        """
        t('botapp.booking.immediate_handler.ImmediateBookingHandler.handle_booking_cancellation')
        query = update.callback_query
        await query.answer("Booking cancelled")
        
        # Parse to get date for potential return to availability
        parsed = self.parser.parse_booking_callback(query.data)
        if not parsed or parsed['action'] != 'cancel':
            # Just return to menu on parse error
            await query.edit_message_text(
                "Booking cancelled. Returning to main menu.",
                reply_markup=TelegramUI.create_main_menu_keyboard()
            )
            return
        
        # Could re-trigger availability check here if needed
        # For now, just return to menu
        await query.edit_message_text(
            "Booking cancelled. Use the menu to check availability again.",
            reply_markup=TelegramUI.create_main_menu_keyboard()
        )
    
    def _fetch_user_profile(self, user_id: int) -> Optional[Dict[str, Any]]:
        """
        Get and validate user data
        
        Args:
            user_id: Telegram user ID
            
        Returns:
            User dict if valid, None otherwise
        """
        t('botapp.booking.immediate_handler.ImmediateBookingHandler._fetch_user_profile')
        user = self.user_manager.get_user(user_id)
        
        if not user:
            return None
        
        # Validate required fields
        required_fields = ['email', 'first_name', 'last_name', 'phone']
        for field in required_fields:
            if not user.get(field):
                self.logger.warning(f"User {user_id} missing required field: {field}")
                return None
        
        return user
    
    def _build_booking_request(
        self,
        user_profile: Dict[str, Any],
        parsed: Dict[str, Any],
        telegram_user_id: int,
    ) -> BookingRequest:
        """Assemble the booking request payload from callback data and user profile."""

        t('botapp.booking.immediate_handler.ImmediateBookingHandler._build_booking_request')

        required_keys = {'date', 'time', 'court_number'}
        if not required_keys <= parsed.keys():
            missing = ', '.join(sorted(required_keys - parsed.keys()))
            raise ValueError(f'Missing booking details: {missing}')

        return build_immediate_booking_request(
            user_profile,
            target_date=parsed['date'],
            time_slot=parsed['time'],
            court_number=parsed['court_number'],
            metadata={
                'trigger': 'immediate_handler',
                'callback_action': parsed['action'],
                'telegram_user_id': telegram_user_id,
            },
        )

    def _build_executor_user_info(self, booking_request: BookingRequest) -> Dict[str, Any]:
        t('botapp.booking.immediate_handler.ImmediateBookingHandler._build_executor_user_info')
        return booking_request.user.as_executor_payload(include_tier_when_none=True)

    async def execute_queue_booking(self, booking_request: BookingRequest) -> BookingResult:
        """Compatibility wrapper used by the reservation scheduler."""
        t('botapp.booking.immediate_handler.ImmediateBookingHandler.execute_queue_booking')
        return await self._run_booking_attempts(booking_request)

    async def _execute_booking(self, booking_request: BookingRequest) -> BookingResult:
        """Legacy entrypoint used by older scheduler paths and tests."""
        return await self._run_booking_attempts(booking_request)

    async def _run_booking_attempts(self, booking_request: BookingRequest) -> BookingResult:
        """Attempt the natural booking flow and return its result."""

        t('botapp.booking.immediate_handler.ImmediateBookingHandler._run_booking_attempts')

        user_info = self._build_executor_user_info(booking_request)
        natural_result = await self._attempt_natural_flow(booking_request, user_info)
        if natural_result is not None:
            return natural_result

        failure_message = "Browser pool unavailable for natural booking"
        return BookingResult.failure_result(
            booking_request.user,
            booking_request.request_id,
            message=failure_message,
            errors=[failure_message],
            metadata={'executor': 'UnifiedAsyncBookingExecutor', 'flow': 'natural', 'reason': 'browser_pool_unavailable'},
        )

    async def _attempt_natural_flow(
        self,
        booking_request: BookingRequest,
        user_info: Dict[str, Any],
    ) -> Optional[BookingResult]:
        t('botapp.booking.immediate_handler.ImmediateBookingHandler._attempt_natural_flow')
        if not self.browser_pool:
            return None

        self.logger.info("🎯 IMMEDIATE BOOKING - Attempting natural flow execution")
        try:
            async_executor = UnifiedAsyncBookingExecutor(
                self.browser_pool,
                config=AsyncExecutorConfig(natural_flow=True),
            )
            execution = await async_executor.execute_booking(
                court_number=booking_request.court_preference.primary,
                time_slot=booking_request.target_time,
                user_info=user_info,
                target_date=booking_request.target_date,
            )
            result = build_booking_result_from_execution(
                booking_request,
                execution,
                metadata={'executor': 'UnifiedAsyncBookingExecutor', 'flow': 'natural'},
            )
            if result.success:
                self.logger.info("✅ Natural flow booking successful")
            else:
                self.logger.warning(
                    "❌ Natural flow booking failed: %s",
                    result.message or ', '.join(result.errors),
                )
            return result
        except Exception as exc:  # pragma: no cover - fallback guard
            self.logger.error("❌ Natural flow execution error: %s", exc)
            return None

    async def _handle_booking_outcome(
        self,
        query,
        booking_request: BookingRequest,
        booking_result: BookingResult,
        *,
        persist: Callable[[BookingRequest, BookingResult], str],
        notifier: Callable[[int, BookingResult], Dict[str, Any]],
        persist_error: str,
    ) -> None:
        try:
            persist(booking_request, booking_result)
        except Exception as exc:  # pragma: no cover - persistence guard
            self.logger.error(persist_error, exc)

        notification = notifier(booking_request.user.user_id, booking_result)
        await self._send_notification(query, notification)

    async def _handle_successful_booking(
        self,
        query,
        booking_request: BookingRequest,
        booking_result: BookingResult,
    ) -> None:
        t('botapp.booking.immediate_handler.ImmediateBookingHandler._handle_successful_booking')
        await self._handle_booking_outcome(
            query,
            booking_request,
            booking_result,
            persist=self._persist_success,
            notifier=send_success_notification,
            persist_error="Failed to persist immediate success: %s",
        )

        # Send main menu follow-up after booking confirmation
        await self._send_main_menu_followup(query, booking_request.user.user_id)

    async def _handle_failed_booking(
        self,
        query,
        booking_request: BookingRequest,
        booking_result: BookingResult,
    ) -> None:
        t('botapp.booking.immediate_handler.ImmediateBookingHandler._handle_failed_booking')
        await self._handle_booking_outcome(
            query,
            booking_request,
            booking_result,
            persist=self._persist_failure,
            notifier=send_failure_notification,
            persist_error="Failed to record immediate failure: %s",
        )

    def _persist_success(self, booking_request: BookingRequest, booking_result: BookingResult) -> str:
        t('botapp.booking.immediate_handler.ImmediateBookingHandler._persist_success')
        return persist_immediate_success(booking_request, booking_result)

    def _persist_failure(self, booking_request: BookingRequest, booking_result: BookingResult) -> str:
        t('botapp.booking.immediate_handler.ImmediateBookingHandler._persist_failure')
        return persist_immediate_failure(booking_request, booking_result)

    async def _send_notification(self, query, notification: Dict[str, Any]) -> None:
        t('botapp.booking.immediate_handler.ImmediateBookingHandler._send_notification')
        await query.edit_message_text(
            notification['message'],
            parse_mode=notification.get('parse_mode', 'Markdown'),
            reply_markup=notification.get('reply_markup', TelegramUI.create_back_to_menu_keyboard()),
        )
    
    async def _send_error(self, query, message: str) -> None:
        """
        Send error message with back to menu button

        Args:
            query: Callback query
            message: Error message
        """
        t('botapp.booking.immediate_handler.ImmediateBookingHandler._send_error')
        await query.edit_message_text(
            f"❌ {message}",
            reply_markup=TelegramUI.create_back_to_menu_keyboard()
        )

    async def _send_main_menu_followup(self, query, user_id: int) -> None:
        """
        Send main menu as a follow-up message after booking confirmation

        Args:
            query: Callback query
            user_id: User ID for checking admin status and tier
        """
        t('botapp.booking.immediate_handler.ImmediateBookingHandler._send_main_menu_followup')

        # Wait a few seconds before showing the menu
        await asyncio.sleep(5)

        # Get user info for tier badge
        is_admin = self.user_manager.is_admin(user_id)
        tier = self.user_manager.get_user_tier(user_id)
        tier_badge = TelegramUI.format_user_tier_badge(tier.name)

        # Send main menu
        reply_markup = TelegramUI.create_main_menu_keyboard(is_admin=is_admin)
        await query.message.reply_text(
            f"🎾 What would you like to do next? {tier_badge}",
            reply_markup=reply_markup,
        )
