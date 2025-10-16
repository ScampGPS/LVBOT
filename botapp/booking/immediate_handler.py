"""
Immediate booking handler for direct court reservations
Manages the flow from availability display to booking execution
"""
from tracking import t

from typing import Dict, Any, Optional
from datetime import datetime, date
from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import ContextTypes
import logging

from automation.executors import AsyncExecutorConfig, UnifiedAsyncBookingExecutor
from automation.executors.request_factory import build_booking_result_from_execution
from automation.executors.tennis import (
    TennisExecutor,
    create_tennis_config_from_user_info,
)
from automation.shared.booking_contracts import BookingRequest, BookingResult

from ..callbacks.parser import CallbackParser
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
        user = self._get_validated_user(query.from_user.id)
        if not user:
            await query.edit_message_text(
                TelegramUI.format_error_message('profile_incomplete'),
                reply_markup=TelegramUI.create_back_to_menu_keyboard()
            )
            return
        
        # Create confirmation UI
        confirm_ui = self._create_confirmation_ui(parsed, user)
        
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
        
        user_profile = self._get_validated_user(query.from_user.id)
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

        # Show processing message
        await query.edit_message_text("🔄 Processing your booking, please wait...")

        booking_result = await self._execute_booking(booking_request)

        if booking_result.success:
            try:
                persist_immediate_success(booking_request, booking_result)
            except Exception as exc:  # pragma: no cover - persistence guard
                self.logger.error("Failed to persist immediate success: %s", exc)
            notification = send_success_notification(
                booking_request.user.user_id,
                booking_result,
            )
        else:
            try:
                persist_immediate_failure(booking_request, booking_result)
            except Exception as exc:  # pragma: no cover - persistence guard
                self.logger.error("Failed to record immediate failure: %s", exc)
            notification = send_failure_notification(
                booking_request.user.user_id,
                booking_result,
            )

        await query.edit_message_text(
            notification['message'],
            parse_mode=notification.get('parse_mode', 'Markdown'),
            reply_markup=notification.get('reply_markup', TelegramUI.create_back_to_menu_keyboard()),
        )
    
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
    
    def _get_validated_user(self, user_id: int) -> Optional[Dict[str, Any]]:
        """
        Get and validate user data
        
        Args:
            user_id: Telegram user ID
            
        Returns:
            User dict if valid, None otherwise
        """
        t('botapp.booking.immediate_handler.ImmediateBookingHandler._get_validated_user')
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
    
    def _create_confirmation_ui(self, booking_data: Dict[str, Any], 
                               user_data: Dict[str, Any]) -> Dict[str, Any]:
        """
        Create confirmation dialog UI components
        
        Args:
            booking_data: Parsed booking data from callback
            user_data: User information
            
        Returns:
            Dict with 'message' and 'keyboard' keys
        """
        t('botapp.booking.immediate_handler.ImmediateBookingHandler._create_confirmation_ui')
        # Format confirmation message
        message = (
            f"🎾 **Confirm Immediate Booking**\n\n"
            f"📅 Date: {booking_data['date'].strftime('%A, %B %d, %Y')}\n"
            f"⏰ Time: {booking_data['time']}\n"
            f"🎾 Court: {booking_data['court_number']}\n"
            f"👤 Name: {user_data.get('first_name', '')} {user_data.get('last_name', '')}\n"
            f"📱 Phone: {user_data.get('phone', 'Not set')}\n\n"
            f"Would you like to book this court now?"
        )
        
        # Create keyboard using CallbackParser for consistent formatting
        confirm_callback = self.parser.format_booking_callback(
            'confirm_book',
            booking_data['date'],
            booking_data['court_number'],
            booking_data['time']
        )
        
        cancel_callback = self.parser.format_booking_callback(
            'cancel_book',
            booking_data['date']
        )
        
        keyboard = InlineKeyboardMarkup([
            [
                InlineKeyboardButton("✅ Book Now", callback_data=confirm_callback),
                InlineKeyboardButton("❌ Cancel", callback_data=cancel_callback)
            ]
        ])
        
        return {
            'message': message,
            'keyboard': keyboard
        }
    
    async def _execute_booking(self, booking_request: BookingRequest) -> BookingResult:
        """Execute a booking request and return a shared booking result."""

        t('botapp.booking.immediate_handler.ImmediateBookingHandler._execute_booking')

        try:
            court_number = booking_request.court_preference.primary
            user_info = {
                'first_name': booking_request.user.first_name,
                'last_name': booking_request.user.last_name,
                'email': booking_request.user.email,
                'phone': booking_request.user.phone,
                'user_id': booking_request.user.user_id,
                'tier': booking_request.user.tier,
            }

            natural_result: Optional[BookingResult] = None

            if self.browser_pool:
                self.logger.info("🎯 IMMEDIATE BOOKING - Attempting natural flow execution")
                try:
                    async_executor = UnifiedAsyncBookingExecutor(
                        self.browser_pool,
                        config=AsyncExecutorConfig(natural_flow=True),
                    )
                    execution = await async_executor.execute_booking(
                        court_number=court_number,
                        time_slot=booking_request.target_time,
                        user_info=user_info,
                        target_date=booking_request.target_date,
                    )
                    natural_result = build_booking_result_from_execution(
                        booking_request,
                        execution,
                        metadata={
                            'executor': 'UnifiedAsyncBookingExecutor',
                            'flow': 'natural',
                        },
                    )
                    if natural_result.success:
                        self.logger.info("✅ Natural flow booking successful")
                        return natural_result
                    self.logger.warning(
                        "❌ Natural flow booking failed: %s",
                        natural_result.message or ', '.join(natural_result.errors),
                    )
                except Exception as exc:  # pragma: no cover - fallback guard
                    self.logger.error("❌ Natural flow execution error: %s", exc)

            self.logger.info("Falling back to TennisExecutor flow")
            executor = TennisExecutor(browser_pool=self.browser_pool)
            tennis_config = create_tennis_config_from_user_info(
                {
                    'email': booking_request.user.email,
                    'first_name': booking_request.user.first_name,
                    'last_name': booking_request.user.last_name,
                    'phone': booking_request.user.phone,
                    'user_id': booking_request.user.user_id,
                    'court_preference': booking_request.court_preference.as_list(),
                    'preferred_times': [booking_request.target_time],
                    'target_time': booking_request.target_time,
                }
            )
            target_datetime = datetime.combine(booking_request.target_date, datetime.min.time())
            execution = await executor.execute(
                tennis_config,
                target_datetime,
                check_availability_48h=False,
                get_dates=False,
            )
            fallback_result = build_booking_result_from_execution(
                booking_request,
                execution,
                metadata={
                    'executor': 'TennisExecutor',
                    'flow': 'fallback',
                },
            )

            if not fallback_result.success and natural_result and not natural_result.success:
                combined_errors = tuple({*natural_result.errors, *fallback_result.errors})
                fallback_result = BookingResult.failure_result(
                    booking_request.user,
                    booking_request.request_id,
                    message=fallback_result.message,
                    errors=combined_errors,
                    metadata=dict(fallback_result.metadata),
                )

            return fallback_result

        except Exception as exc:  # pragma: no cover - defensive guard
            self.logger.error("Booking execution error: %s", exc)
            return BookingResult.failure_result(
                booking_request.user,
                booking_request.request_id,
                message=str(exc),
                errors=[str(exc)],
                metadata={
                    **booking_request.metadata,
                    'executor': 'ImmediateBookingHandler',
                    'flow': 'exception',
                },
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
