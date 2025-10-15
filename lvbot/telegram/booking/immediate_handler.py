"""
Immediate booking handler for direct court reservations
Manages the flow from availability display to booking execution
"""

from typing import Dict, Any, Optional
from datetime import datetime, date
from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import ContextTypes
import logging

from lvbot.telegram.callbacks.parser import CallbackParser
from lvbot.telegram.ui.telegram_ui import TelegramUI
from lvbot.automation.executors.tennis_executor import TennisExecutor, create_tennis_config_from_user_info
from lvbot.automation.executors import UnifiedAsyncBookingExecutor

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
        query = update.callback_query
        await query.answer()
        
        # Parse callback data
        parsed = self.parser.parse_booking_callback(query.data)
        if not parsed or parsed['action'] != 'confirm':
            await self._send_error(query, "Invalid confirmation format")
            return
        
        # Show processing message
        await query.edit_message_text("🔄 Processing your booking, please wait...")
        
        # Execute booking
        result = await self._execute_booking(query.from_user.id, parsed)
        
        # Show result
        if result['success']:
            message = self._format_success_message(result, parsed)
            
            # Save successful booking to reservation tracker
            try:
                from lvbot.domain.queue.reservation_tracker import ReservationTracker
                tracker = ReservationTracker()
                
                # Extract confirmation ID from message if available
                confirmation_id = None
                confirmation_url = None
                if 'message' in result and 'ID:' in result['message']:
                    # Try to extract confirmation ID from message
                    import re
                    match = re.search(r'ID:\s*([a-zA-Z0-9]+)', result['message'])
                    if match:
                        confirmation_id = match.group(1)
                        confirmation_url = f"https://clublavilla.as.me/schedule/7d558012/confirmation/{confirmation_id}"
                
                booking_data = {
                    'court': parsed['court_number'],
                    'date': parsed['date'].isoformat(),
                    'time': parsed['time'],
                    'confirmation_id': confirmation_id,
                    'confirmation_url': confirmation_url,
                    'type': 'immediate',
                    'status': 'confirmed'
                }
                
                reservation_id = tracker.add_immediate_reservation(query.from_user.id, booking_data)
                self.logger.info(f"Saved immediate reservation: {reservation_id}")
                
            except Exception as e:
                self.logger.error(f"Failed to save reservation to tracker: {e}")
                # Don't fail the booking notification due to tracking error
        else:
            message = self._format_failure_message(result, parsed)
        
        await query.edit_message_text(
            message,
            parse_mode='Markdown',
            reply_markup=TelegramUI.create_back_to_menu_keyboard()
        )
    
    async def handle_booking_cancellation(self, update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
        """
        Handle booking cancellation - return to availability view
        
        Args:
            update: Telegram update with callback query
            context: Callback context
        """
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
    
    async def _execute_booking(self, user_id: int, 
                             booking_data: Dict[str, Any]) -> Dict[str, Any]:
        """
        Execute the actual booking using smart executor
        
        Args:
            user_id: Telegram user ID
            booking_data: Parsed booking data
            
        Returns:
            Result dict with 'success' and other fields
        """
        try:
            # Get user data
            user = self.user_manager.get_user(user_id)
            if not user:
                return {
                    'success': False,
                    'message': 'User profile not found'
                }
            
            # Create tennis config using existing helper
            # Pass browser pool if available for optimized execution
            executor = TennisExecutor(browser_pool=self.browser_pool)
            tennis_config = create_tennis_config_from_user_info({
                'email': user.get('email'),
                'first_name': user.get('first_name'),
                'last_name': user.get('last_name'),
                'phone': user.get('phone'),
                'court_preference': [booking_data['court_number']],
                'preferred_times': [booking_data['time']]
            })
            
            # Convert date to datetime
            target_datetime = datetime.combine(booking_data['date'], datetime.min.time())
            
            # Try natural flow booking first (optimized for within 48h)
            result = None
            if self.browser_pool:
                self.logger.info("🎯 IMMEDIATE BOOKING - Using natural flow with 2.5x speed optimization")
                try:
                    async_executor = UnifiedAsyncBookingExecutor(self.browser_pool)
                    result = await async_executor.execute_booking(
                        court_number=booking_data['court_number'],
                        time_slot=booking_data['time'],
                        user_info={
                            'first_name': user.get('first_name'),
                            'last_name': user.get('last_name'),
                            'email': user.get('email'),
                            'phone': user.get('phone')
                        },
                        target_date=booking_data['date']
                    )
                    
                    if result.success:
                        self.logger.info("✅ Natural flow booking successful")
                        return {
                            'success': True,
                            'message': result.message or f"Court {booking_data['court_number']} booked successfully",
                            'confirmation_code': getattr(result, 'confirmation_code', None),
                            'court': booking_data['court_number']
                        }
                    else:
                        self.logger.warning(f"❌ Natural flow booking failed: {result.error_message}")
                        # Continue to fallback if needed
                        
                except Exception as e:
                    self.logger.error(f"❌ Natural flow booking exception: {e}")
                    # Continue to fallback if an exception occurs
            
            # Keep existing fallback logic for when natural flow fails
            if not result or not result.success:
                self.logger.info("Falling back to TennisExecutor approach")
                result = await executor.execute(
                    tennis_config,
                    target_datetime,
                    check_availability_48h=False,
                    get_dates=False
                )
            
            return {
                'success': result.success,
                'message': result.message or result.error_message,
                'confirmation_code': getattr(result, 'confirmation_code', None),
                'court': booking_data['court_number']
            }
            
        except Exception as e:
            self.logger.error(f"Booking execution error: {e}")
            return {
                'success': False,
                'message': str(e)
            }
    
    def _format_success_message(self, result: Dict[str, Any], 
                               booking_data: Dict[str, Any]) -> str:
        """
        Format successful booking message
        
        Args:
            result: Execution result
            booking_data: Original booking data
            
        Returns:
            Formatted success message
        """
        return (
            f"✅ **Booking Successful!**\n\n"
            f"🎾 Court {booking_data['court_number']} has been booked\n"
            f"📅 Date: {booking_data['date'].strftime('%A, %B %d, %Y')}\n"
            f"⏰ Time: {booking_data['time']}\n"
            f"🔑 Confirmation: {result.get('confirmation_code', 'Pending')}\n\n"
            f"See you on the court!"
        )
    
    def _format_failure_message(self, result: Dict[str, Any], 
                               booking_data: Dict[str, Any]) -> str:
        """
        Format booking failure message
        
        Args:
            result: Execution result with error
            booking_data: Original booking data
            
        Returns:
            Formatted failure message
        """
        # Escape the error message to prevent Telegram parsing errors
        error_message = result.get('message', 'Unknown error')
        # Replace characters that might break Markdown
        error_message = error_message.replace('_', '\\_').replace('*', '\\*').replace('[', '\\[').replace(']', '\\]').replace('`', '\\`')
        
        return (
            f"❌ **Booking Failed**\n\n"
            f"Could not book Court {booking_data['court_number']} at {booking_data['time']}\n"
            f"Reason: {error_message}\n\n"
            f"Please try another time slot or check back later."
        )
    
    async def _send_error(self, query, message: str) -> None:
        """
        Send error message with back to menu button
        
        Args:
            query: Callback query
            message: Error message
        """
        await query.edit_message_text(
            f"❌ {message}",
            reply_markup=TelegramUI.create_back_to_menu_keyboard()
        )
