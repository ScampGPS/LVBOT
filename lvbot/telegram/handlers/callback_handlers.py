"""
Callback handlers for telegram bot
Handles all inline keyboard button callbacks in a modular way
"""

import os
import logging
from typing import Dict, Callable, Any, List
from datetime import datetime, timedelta, date
from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import ContextTypes
from lvbot.telegram.ui.telegram_ui import TelegramUI
from lvbot.automation.availability.datetime_helpers import DateTimeHelpers
from lvbot.telegram.error_handler import ErrorHandler
from lvbot.telegram.booking.immediate_handler import ImmediateBookingHandler
from lvbot.infrastructure.constants import COURT_HOURS, get_court_hours

# Read production mode setting
PRODUCTION_MODE = os.getenv('PRODUCTION_MODE', 'true').lower() == 'true'


class CallbackHandler:
    """Handles all callback queries from inline keyboards"""
    
    # Number of days in advance that users can book courts (48-hour booking window)
    BOOKING_WINDOW_DAYS = 2
    
    # Number of days to show for queue booking (needs to be longer since first 2 days are filtered out)
    QUEUE_BOOKING_WINDOW_DAYS = 7
    
    # Available courts for reservation
    AVAILABLE_COURTS = [1, 2, 3]
    
    def __init__(self, availability_checker, reservation_queue, user_manager, browser_pool=None) -> None:
        """
        Initialize the callback handler
        
        Args:
            availability_checker: Instance of AsyncAvailabilityChecker for court checking
            reservation_queue: Instance of ReservationQueue for managing reservations
            user_manager: Instance of UserManager for managing user profiles
            browser_pool: Optional browser pool for optimized booking execution
        
        Sets up logging and creates the callback routing map
        """
        self.logger = logging.getLogger('CallbackHandler')
        self.availability_checker = availability_checker
        self.reservation_queue = reservation_queue
        self.user_manager = user_manager
        self.browser_pool = browser_pool
        
        # Initialize immediate booking handler with browser pool
        self.booking_handler = ImmediateBookingHandler(user_manager, browser_pool)
        
        # Initialize reservation tracker for managing all reservations
        from lvbot.domain.queue.reservation_tracker import ReservationTracker
        self.reservation_tracker = ReservationTracker()
        
        # Map callback_data to handler methods
        self.callback_map: Dict[str, Callable] = {
            'menu_reserve': self._handle_reserve_menu,
            'menu_queued': self._handle_my_reservations_menu,  # Maps to My Reservations
            'menu_profile': self._handle_profile_menu,
            'edit_profile': self._handle_edit_profile,
            'edit_name': self._handle_edit_name,
            'edit_first_name': self._handle_edit_first_name,
            'edit_last_name': self._handle_edit_last_name,
            'edit_phone': self._handle_edit_phone,
            'edit_email': self._handle_edit_email,
            'cancel_edit': self._handle_cancel_edit,
            'menu_performance': self._handle_performance_menu,
            'menu_reservations': self._handle_reservations_menu,
            'menu_help': self._handle_help_menu,
            'menu_about': self._handle_about_menu,
            'menu_queue_booking': self._handle_queue_booking_menu,
            'menu_admin': self._handle_admin_menu,
            'back_to_menu': self._handle_back_to_menu,
            'reserve_48h_immediate': self._handle_48h_immediate_booking,
            'reserve_48h_future': self._handle_48h_future_booking,
            'back_to_booking_type': self._handle_reserve_menu,
            'back_to_year_selection': self._handle_48h_future_booking,
            'back_to_reserve': self._handle_reserve_menu,
            'back_to_queue_dates': self._handle_48h_future_booking,
            'queue_confirm': self._handle_queue_booking_confirm,
            'queue_cancel': self._handle_queue_booking_cancel,
            'back_to_queue_courts': self._handle_back_to_queue_courts,
            'admin_view_my_reservations': self._handle_admin_my_reservations,
            'admin_view_users_list': self._handle_admin_users_list,
            'admin_view_all_reservations': self._handle_admin_all_reservations,
        }
    
    async def handle_callback(self, update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
        """
        Main routing method for all callbacks
        
        Args:
            update: The telegram update containing the callback query
            context: The callback context
            
        Returns:
            None
        """
        query = update.callback_query
        
        # Safely answer the callback query with timeout handling
        try:
            await query.answer()
        except Exception as e:
            # Log the error but continue processing - this prevents the whole callback from failing
            self.logger.warning(f"Failed to answer callback query: {e}")
            # Don't return here - continue with callback processing
        
        # Get the callback data
        callback_data = query.data
        self.logger.info(f"Received callback: {callback_data}")
        
        # Log user button press for debugging and user interaction tracking
        user_id = update.effective_user.id if update.effective_user else "Unknown"
        self.logger.info(f"User {user_id} pressed button: {callback_data}")
        
        # Check if it's a year selection callback
        if callback_data.startswith('year_'):
            await self._handle_year_selection(update, context)
            return
        
        # Check if it's a month selection callback
        if callback_data.startswith('month_'):
            await self._handle_month_selection(update, context)
            return
        
        # Check if it's a future date selection callback
        if callback_data.startswith('future_date_'):
            await self._handle_future_date_selection(update, context)
            return
        
        # Check if it's a blocked date callback (within 48h)
        if callback_data.startswith('blocked_date_'):
            await self._handle_blocked_date_selection(update, context)
            return
        
        # Check if it's a back to month callback
        if callback_data.startswith('back_to_month_'):
            await self._handle_back_to_month(update, context)
            return
        
        # Check if it's a day cycling callback
        if callback_data.startswith('cycle_day_'):
            await self._handle_day_cycling(update, context)
            return
        
        # Check if it's a date callback
        if callback_data.startswith('date_'):
            # Route based on current flow state
            current_flow = context.user_data.get('current_flow')
            if current_flow is None:
                ErrorHandler.log_error_context(update, context, 'missing_current_flow_state', 
                                             {'callback_data': callback_data})
                current_flow = 'availability_check'  # Default fallback
            
            if current_flow == 'queue_booking':
                await self._handle_queue_booking_date_selection(update, context)
            else:
                await self._handle_date_selection(update, context)
            return
        
        # Check if it's a queue booking time callback
        if callback_data.startswith('queue_time_') and not callback_data.startswith('queue_time_modify_'):
            await self._handle_queue_booking_time_selection(update, context)
            return
        
        # Check if it's a time modification callback
        if callback_data.startswith('queue_time_modify_'):
            await self._handle_time_modification(update, context)
            return
        
        # Check if it's a queue booking court callback
        if callback_data.startswith('queue_court_'):
            await self._handle_queue_booking_court_selection(update, context)
            return
        
        # Check if it's an immediate booking callback
        if callback_data.startswith('book_now_'):
            await self.booking_handler.handle_booking_request(update, context)
            return
        
        # Check if it's a booking confirmation callback
        if callback_data.startswith('confirm_book_'):
            await self.booking_handler.handle_booking_confirmation(update, context)
            return
        
        # Check if it's a booking cancellation callback
        if callback_data.startswith('cancel_book_'):
            await self.booking_handler.handle_booking_cancellation(update, context)
            return
        
        # Check if it's a queue booking confirmation callback
        if callback_data == 'queue_confirm':
            await self._handle_queue_booking_confirm(update, context)
            return
        
        # Check if it's a queue booking cancellation callback
        if callback_data == 'queue_cancel':
            await self._handle_queue_booking_cancel(update, context)
            return
        
        # Check if it's a reservation management callback
        if callback_data.startswith('manage_res_'):
            await self._handle_manage_reservation(update, context)
            return
        
        # Check if it's a queue reservation management callback
        if callback_data.startswith('manage_queue_'):
            await self._handle_manage_queue_reservation(update, context)
            return
        
        # Check if it's an admin viewing specific user callback
        if callback_data.startswith('admin_view_user_'):
            user_id = int(callback_data.replace('admin_view_user_', ''))
            await self._display_user_reservations(update, context, user_id)
            return
        
        # Check if it's a reservation action callback
        if callback_data.startswith('res_action_'):
            await self._handle_reservation_action(update, context)
            return
        
        # Check if it's a modify option callback
        if callback_data.startswith('modify_date_') or callback_data.startswith('modify_time_') or callback_data.startswith('modify_courts_'):
            await self._handle_modify_option(update, context)
            return
        
        # Check if it's a court header callback (informational only)
        if callback_data.startswith('court_header_'):
            # These are just headers, no action needed
            try:
                await query.answer("Select a time slot below")
            except Exception as e:
                self.logger.warning(f"Failed to answer court header callback: {e}")
            return
        
        # Check if it's a noop callback (informational only)
        if callback_data == 'noop':
            # No operation needed
            try:
                await query.answer()
            except Exception as e:
                self.logger.warning(f"Failed to answer noop callback: {e}")
            return
        
        # Check if it's a phone digit callback
        if callback_data.startswith('phone_digit_') or callback_data in ['phone_delete', 'phone_done']:
            await self._handle_phone_keypad(update, context)
            return
        
        # Check if it's a name editing callback
        if callback_data.startswith('name_') or callback_data.startswith('letter_'):
            await self._handle_name_callbacks(update, context)
            return
        
        # Check if it's an email editing callback
        if callback_data.startswith('email_') or callback_data == 'email_confirm':
            await self._handle_email_callbacks(update, context)
            return
        
        # Route to appropriate handler
        handler = self.callback_map.get(callback_data, self._handle_unknown_menu)
        
        try:
            await handler(update, context)
        except Exception as e:
            await ErrorHandler.handle_telegram_error(update, context, e)
    
    async def _safe_answer_callback(self, query, text: str = None) -> None:
        """
        Safely answer a callback query with proper error handling
        
        Args:
            query: The callback query to answer
            text: Optional text to show to user
        """
        try:
            if text:
                await query.answer(text)
            else:
                await query.answer()
        except Exception as e:
            # Log the error but don't raise - callback processing should continue
            self.logger.warning(f"Failed to answer callback query: {e}")
            # Common reasons: query too old, already answered, network timeout
    
    async def _handle_reserve_menu(self, update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
        """
        Handle Reserve Court menu option - show booking type selection
        
        Args:
            update: The telegram update containing the callback query
            context: The callback context
            
        Returns:
            None
        """
        # Debug: Log method entry with user context
        user_id = update.callback_query.from_user.id if update.callback_query and update.callback_query.from_user else "Unknown"
        self.logger.debug(f"_handle_reserve_menu: Method entry for user_id={user_id}")
        
        query = update.callback_query
        
        # Create 48h booking type selection keyboard
        keyboard = TelegramUI.create_48h_booking_type_keyboard()
        
        # Debug: Log pre-message sending
        self.logger.debug(f"_handle_reserve_menu: About to send booking type selection to user_id={user_id}")
        
        await query.edit_message_text(
            "🎾 Reserve Court\n\nChoose booking type:",
            reply_markup=keyboard
        )
    
    async def _handle_my_reservations_menu(self, update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
        """
        Handle My Reservations menu option - shows queued reservations as buttons
        
        Each reservation appears as a button that leads to a submenu with
        cancel/modify/back options
        
        Args:
            update: The telegram update containing the callback query
            context: The callback context
            
        Returns:
            None
        """
        query = update.callback_query
        user_id = query.from_user.id
        
        try:
            # Retrieve user's reservations from the queue
            user_reservations = self.reservation_queue.get_user_reservations(user_id)
            
            if not user_reservations:
                await query.edit_message_text(
                    "📋 **Queued Reservations**\n\n"
                    "You don't have any queued reservations.\n\n"
                    "Use '🎾 Reserve Court' → '📅 Reserve after 48h' to queue a booking!",
                    parse_mode='Markdown',
                    reply_markup=TelegramUI.create_back_to_menu_keyboard()
                )
                return
            
            # Create keyboard with reservation buttons
            keyboard = []
            message = "📋 **Queued Reservations**\n\n"
            message += f"You have {len(user_reservations)} queued reservation(s).\n"
            message += "Click on a reservation to manage it:\n\n"
            
            # Sort reservations by date and time
            user_reservations.sort(key=lambda x: (x.get('target_date', ''), x.get('target_time', '')))
            
            for res in user_reservations:
                # Format reservation info for button
                date_str = res.get('target_date', 'Unknown')
                if date_str != 'Unknown':
                    try:
                        # Parse date and format as "Nov 4th 2025"
                        date_obj = datetime.strptime(date_str, '%Y-%m-%d')
                        day = date_obj.day
                        # Add ordinal suffix
                        if 10 <= day % 100 <= 20:
                            suffix = 'th'
                        else:
                            suffix = {1: 'st', 2: 'nd', 3: 'rd'}.get(day % 10, 'th')
                        date_str = date_obj.strftime(f'%b {day}{suffix} %Y')
                    except:
                        pass
                time_str = res.get('target_time', 'Unknown')
                courts = res.get('court_preferences', [])
                status = res.get('status', 'pending')
                
                # Create court string
                if courts:
                    if len(courts) == 3:
                        court_str = "All Courts"
                    else:
                        court_str = f"Court{'s' if len(courts) > 1 else ''} {', '.join(map(str, courts))}"
                else:
                    court_str = "No courts"
                
                # Status emoji
                status_emoji = {
                    'pending': '⏳',
                    'scheduled': '🔄',
                    'completed': '✅',
                    'failed': '❌'
                }.get(status, '❓')
                
                # Button text
                button_text = f"{status_emoji} {date_str} {time_str} - {court_str}"
                callback_data = f"manage_queue_{res['id']}"
                
                keyboard.append([InlineKeyboardButton(button_text, callback_data=callback_data)])
            
            # Add back to menu button
            keyboard.append([InlineKeyboardButton("⬅️ Back to Menu", callback_data='back_to_menu')])
            
            reply_markup = InlineKeyboardMarkup(keyboard)
            
            await query.edit_message_text(
                message,
                parse_mode='Markdown',
                reply_markup=reply_markup
            )
            
        except Exception as e:
            if not PRODUCTION_MODE:
                self.logger.error(f"Error in _handle_my_reservations_menu: {e}", exc_info=True)
            else:
                self.logger.error(f"Error in _handle_my_reservations_menu: {e}")
            await ErrorHandler.handle_booking_error(update, context, 'system_error', 
                                                   'Failed to retrieve reservations')
    
    async def _handle_profile_menu(self, update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
        """
        Handle Profile menu option
        
        Displays user's profile information including personal details and preferences
        
        Args:
            update: The telegram update containing the callback query
            context: The callback context
            
        Returns:
            None
        """
        query = update.callback_query
        user_id = query.from_user.id
        
        try:
            # Get user profile data using UserManager
            user_profile = self._get_user_profile_data(user_id, query.from_user)
            
            # Check if user is hardcoded
            from lvbot.infrastructure.constants import HARDCODED_VIP_USERS, HARDCODED_ADMIN_USERS
            is_hardcoded = user_id in HARDCODED_VIP_USERS or user_id in HARDCODED_ADMIN_USERS
            
            # Format profile using TelegramUI
            message = TelegramUI.format_user_profile_message(user_profile, is_hardcoded)
            
            # Create profile keyboard with Edit button
            reply_markup = TelegramUI.create_profile_keyboard()
            
            await query.edit_message_text(
                message,
                parse_mode='Markdown',
                reply_markup=reply_markup
            )
            
        except Exception as e:
            await ErrorHandler.handle_booking_error(update, context, 'system_error', 
                                                   'Failed to retrieve user profile')
    
    def _get_user_profile_data(self, user_id: int, telegram_user) -> Dict[str, Any]:
        """
        Get user profile data using UserManager with automatic user creation for new users
        
        Args:
            user_id: Telegram user ID
            telegram_user: Telegram user object with basic info
            
        Returns:
            Dict containing user profile data
        """
        # Try to retrieve existing user profile
        user_profile = self.user_manager.get_user(user_id)
        
        # Get basic info from Telegram user object
        first_name = telegram_user.first_name or "Unknown"
        last_name = telegram_user.last_name or ""
        username = telegram_user.username
        
        # Count user's reservations from queue (always get current count)
        user_reservations = self.reservation_queue.get_user_reservations(user_id)
        total_reservations = len(user_reservations)
        
        if user_profile is None:
            # New user - create basic profile with default values
            from datetime import datetime
            user_profile = {
                'user_id': user_id,
                'first_name': first_name,
                'last_name': last_name,
                'telegram_username': username,
                'phone': None,  # Not set initially
                'email': None,  # Not set initially
                'court_preference': [],  # No preferences initially
                'is_active': False,  # Requires authorization
                'is_admin': False,
                'created_at': datetime.now().isoformat(),
                'last_login': datetime.now().isoformat()
            }
            
            # Save the new user profile
            self.user_manager.save_user(user_profile)
            self.logger.info(f"Created new user profile for user_id: {user_id}")
        
        # Always update total_reservations with current count
        user_profile['total_reservations'] = total_reservations
        
        return user_profile
    
    async def _handle_edit_profile(self, update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
        """
        Handle Edit Profile menu - shows options to edit profile fields
        """
        query = update.callback_query
        
        try:
            message = "✏️ **Edit Profile**\n\nSelect what you want to edit:"
            reply_markup = TelegramUI.create_edit_profile_keyboard()
            
            await query.edit_message_text(
                message,
                parse_mode='Markdown',
                reply_markup=reply_markup
            )
        except Exception as e:
            await ErrorHandler.handle_booking_error(update, context, 'system_error', 
                                                   'Failed to show edit menu')
    
    async def _handle_edit_name(self, update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
        """
        Handle Edit Name - show name type selection
        """
        query = update.callback_query
        user_id = query.from_user.id
        
        try:
            # Clear any previous name building state
            context.user_data.pop('name_input', None)
            context.user_data.pop('editing_name_field', None)
            
            # Get current name
            user_profile = self.user_manager.get_user(user_id)
            first_name = user_profile.get('first_name', '') if user_profile else ''
            last_name = user_profile.get('last_name', '') if user_profile else ''
            
            message = ("👤 **Edit Name**\n\n"
                      f"First Name: {first_name if first_name else 'Not set'}\n"
                      f"Last Name: {last_name if last_name else 'Not set'}\n\n"
                      "What would you like to do?")
            
            reply_markup = TelegramUI.create_name_type_keyboard()
            
            await query.edit_message_text(
                message,
                parse_mode='Markdown',
                reply_markup=reply_markup
            )
        except Exception as e:
            await ErrorHandler.handle_booking_error(update, context, 'system_error', 
                                                   'Failed to show name edit')
    
    async def _handle_edit_first_name(self, update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
        """
        Handle Edit First Name - show letter keyboard
        """
        query = update.callback_query
        user_id = query.from_user.id
        
        try:
            # Initialize name input
            context.user_data['name_input'] = ''
            context.user_data['editing_name_field'] = 'first_name'
            
            message = ("👤 **Edit First Name**\n\n"
                      "First Name: \\_\n\n"
                      "Use the keyboard below:")
            
            reply_markup = TelegramUI.create_letter_keyboard()
            
            await query.edit_message_text(
                message,
                parse_mode='Markdown',
                reply_markup=reply_markup
            )
        except Exception as e:
            if not PRODUCTION_MODE:
                self.logger.error(f"Error in _handle_edit_first_name: {e}", exc_info=True)
            else:
                self.logger.error(f"Error in _handle_edit_first_name: {e}")
            await ErrorHandler.handle_booking_error(update, context, 'system_error', 
                                                   'Failed to show first name edit')
    
    async def _handle_edit_last_name(self, update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
        """
        Handle Edit Last Name - show letter keyboard
        """
        query = update.callback_query
        user_id = query.from_user.id
        
        try:
            # Initialize name input
            context.user_data['name_input'] = ''
            context.user_data['editing_name_field'] = 'last_name'
            
            message = ("👥 **Edit Last Name**\n\n"
                      "Last Name: \\_\n\n"
                      "Use the keyboard below:")
            
            reply_markup = TelegramUI.create_letter_keyboard()
            
            await query.edit_message_text(
                message,
                parse_mode='Markdown',
                reply_markup=reply_markup
            )
        except Exception as e:
            await ErrorHandler.handle_booking_error(update, context, 'system_error', 
                                                   'Failed to show last name edit')
    
    async def _handle_edit_phone(self, update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
        """
        Handle Edit Phone - show numeric keypad for phone input
        """
        query = update.callback_query
        user_id = query.from_user.id
        
        try:
            # Initialize phone input state
            context.user_data['editing_field'] = 'phone'
            context.user_data['phone_input'] = ''
            
            # Get current phone if exists
            user_profile = self.user_manager.get_user(user_id)
            current_phone = user_profile.get('phone', '') if user_profile else ''
            
            message = ("📱 **Edit Phone Number**\n\n"
                      f"Current: (+502) {current_phone if current_phone else 'Not set'}\n\n"
                      "(+502) ________\n\n"
                      "Use the keypad below to enter your 8-digit phone number:")
            
            reply_markup = TelegramUI.create_phone_keypad()
            
            await query.edit_message_text(
                message,
                parse_mode='Markdown',
                reply_markup=reply_markup
            )
        except Exception as e:
            await ErrorHandler.handle_booking_error(update, context, 'system_error', 
                                                   'Failed to start phone edit')
    
    async def _handle_edit_email(self, update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
        """
        Handle Edit Email - show email character keyboard
        """
        query = update.callback_query
        user_id = query.from_user.id
        
        try:
            # Initialize email input
            context.user_data['email_input'] = ''
            
            # Get current email
            user_profile = self.user_manager.get_user(user_id)
            current_email = user_profile.get('email', '') if user_profile else ''
            
            message = ("📧 **Edit Email**\n\n"
                      f"Current: {current_email if current_email else 'Not set'}\n\n"
                      "Email: \\_\n\n"
                      "Use the keyboard below:")
            
            reply_markup = TelegramUI.create_email_char_keyboard()
            
            await query.edit_message_text(
                message,
                parse_mode='Markdown',
                reply_markup=reply_markup
            )
        except Exception as e:
            await ErrorHandler.handle_booking_error(update, context, 'system_error', 
                                                   'Failed to show email edit')
    
    async def _handle_cancel_edit(self, update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
        """
        Handle cancel edit - return to profile view
        """
        query = update.callback_query
        
        try:
            # Clear editing state
            context.user_data.pop('editing_field', None)
            context.user_data.pop('phone_input', None)
            
            # Return to profile menu
            await self._handle_profile_menu(update, context)
        except Exception as e:
            await ErrorHandler.handle_booking_error(update, context, 'system_error', 
                                                   'Failed to cancel edit')
    
    async def _handle_phone_keypad(self, update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
        """
        Handle phone keypad input
        """
        query = update.callback_query
        user_id = query.from_user.id
        callback_data = query.data
        
        try:
            # Ensure we're in phone editing mode
            if context.user_data.get('editing_field') != 'phone':
                await query.answer("❌ Not in phone editing mode")
                return
            
            # Get current phone input
            phone_input = context.user_data.get('phone_input', '')
            
            if callback_data.startswith('phone_digit_'):
                # Add digit to phone
                digit = callback_data.replace('phone_digit_', '')
                if len(phone_input) < 8:
                    phone_input += digit
                else:
                    await query.answer("❌ Phone number must be 8 digits")
                    return
                    
            elif callback_data == 'phone_delete':
                # Delete last digit
                if phone_input:
                    phone_input = phone_input[:-1]
                    
            elif callback_data == 'phone_done':
                # Validate and save phone
                if len(phone_input) != 8:
                    await query.answer("❌ Phone number must be exactly 8 digits")
                    return
                
                # Save phone number
                user_profile = self.user_manager.get_user(user_id)
                if not user_profile:
                    user_profile = {'user_id': user_id}
                
                user_profile['phone'] = phone_input
                self.user_manager.save_user(user_profile)
                
                # Clear editing state
                context.user_data.pop('editing_field', None)
                context.user_data.pop('phone_input', None)
                
                # Show success and return to profile
                await query.answer("✅ Phone number updated!")
                await self._handle_profile_menu(update, context)
                return
            
            # Update phone input in context
            context.user_data['phone_input'] = phone_input
            
            # Format display with underscores for remaining digits
            display_phone = phone_input + '_' * (8 - len(phone_input))
            
            # Update message with current input
            message = ("📱 **Edit Phone Number**\n\n"
                      f"(+502) {display_phone}\n\n"
                      "Use the keypad below to enter your 8-digit phone number:")
            
            reply_markup = TelegramUI.create_phone_keypad()
            
            try:
                await query.edit_message_text(
                    message,
                    parse_mode='Markdown',
                    reply_markup=reply_markup
                )
            except Exception as e:
                # If edit fails (e.g., message didn't change), just answer the callback
                self.logger.debug(f"Edit message failed (normal if content unchanged): {e}")
            
            # Answer callback to remove loading state
            await query.answer()
            
        except Exception as e:
            self.logger.error(f"Error handling phone keypad: {e}")
            await ErrorHandler.handle_booking_error(update, context, 'system_error', 
                                                   'Failed to process phone input')
    
    async def _handle_name_callbacks(self, update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
        """
        Handle all name-related callbacks
        """
        query = update.callback_query
        user_id = query.from_user.id
        callback_data = query.data
        
        try:
            if callback_data == 'name_use_telegram':
                # Use Telegram name
                first_name = query.from_user.first_name or ""
                last_name = query.from_user.last_name or ""
                
                if not first_name:
                    await query.answer("❌ No Telegram name found")
                    return
                
                # Save name
                user_profile = self.user_manager.get_user(user_id) or {'user_id': user_id}
                user_profile['first_name'] = first_name
                user_profile['last_name'] = last_name
                self.user_manager.save_user(user_profile)
                
                await query.answer("✅ Name updated from Telegram!")
                await self._handle_edit_name(update, context)
                
            elif callback_data.startswith('letter_'):
                # Handle letter input
                await self._handle_letter_input(update, context)
                return  # Don't answer again, handled in letter input
                
            await query.answer()
            
        except Exception as e:
            self.logger.error(f"Error handling name callback: {e}")
            await ErrorHandler.handle_booking_error(update, context, 'system_error', 
                                                   'Failed to process name edit')
    
    async def _handle_letter_input(self, update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
        """
        Handle letter-by-letter name input
        """
        query = update.callback_query
        user_id = query.from_user.id
        callback_data = query.data
        
        name_input = context.user_data.get('name_input', '')
        editing_field = context.user_data.get('editing_name_field', 'first_name')
        
        if callback_data == 'letter_delete':
            if name_input:
                name_input = name_input[:-1]
            
        elif callback_data == 'letter_done':
            if not name_input:
                await query.answer("❌ Please enter a name")
                return
            
            # Save to database
            user_profile = self.user_manager.get_user(user_id) or {'user_id': user_id}
            user_profile[editing_field] = name_input
            self.user_manager.save_user(user_profile)
            
            # Clear state
            context.user_data.pop('name_input', None)
            context.user_data.pop('editing_name_field', None)
            
            await query.answer(f"✅ {editing_field.replace('_', ' ').title()} updated!")
            await self._handle_edit_name(update, context)
            return
            
        else:
            # Add letter
            if callback_data == 'letter_apostrophe':
                letter = "'"
            else:
                letter = callback_data.replace('letter_', '')
            
            if len(name_input) < 20:  # Limit name length
                name_input += letter
            else:
                await query.answer("❌ Name too long")
                return
        
        # Update display
        context.user_data['name_input'] = name_input
        
        field_display = "First Name" if editing_field == 'first_name' else "Last Name"
        emoji = "👤" if editing_field == 'first_name' else "👥"
        
        message = (f"{emoji} **Edit {field_display}**\n\n"
                  f"{field_display}: {name_input}\\_\n\n"
                  "Use the keyboard below:")
        
        reply_markup = TelegramUI.create_letter_keyboard()
        await query.edit_message_text(message, parse_mode='Markdown', reply_markup=reply_markup)
        await query.answer()
    
    async def _handle_email_callbacks(self, update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
        """
        Handle all email-related callbacks
        """
        query = update.callback_query
        user_id = query.from_user.id
        callback_data = query.data
        
        try:
            email_input = context.user_data.get('email_input', '')
            
            if callback_data.startswith('email_char_'):
                # Handle character input
                char = callback_data.replace('email_char_', '')
                if len(email_input) < 50:
                    email_input += char
                    context.user_data['email_input'] = email_input
                else:
                    await query.answer("❌ Email too long")
                    return
                
            elif callback_data == 'email_delete':
                if email_input:
                    context.user_data['email_input'] = email_input[:-1]
                    email_input = context.user_data['email_input']
                        
            elif callback_data == 'email_done':
                # Check if email has @
                if '@' not in email_input:
                    await query.answer("❌ Email must contain @")
                    return
                
                # Show confirmation
                message = (f"📧 **Confirm Email**\n\n"
                          f"Email: {email_input}\n\n"
                          "Is this correct?")
                
                reply_markup = TelegramUI.create_email_confirm_keyboard(email_input)
                await query.edit_message_text(message, parse_mode='Markdown', reply_markup=reply_markup)
                return
                
            elif callback_data == 'email_confirm':
                # Save confirmed email
                email = context.user_data.get('email_input', '')
                if not email:
                    await query.answer("❌ No email to save")
                    return
                
                user_profile = self.user_manager.get_user(user_id) or {'user_id': user_id}
                user_profile['email'] = email.lower()
                self.user_manager.save_user(user_profile)
                
                # Clear state
                context.user_data.pop('email_input', None)
                
                await query.answer("✅ Email updated!")
                await self._handle_profile_menu(update, context)
                return
            
            # Update display
            message = (f"📧 **Edit Email**\n\n"
                      f"Email: {email_input}\\_\n\n"
                      "Use the keyboard below:")
            
            reply_markup = TelegramUI.create_email_char_keyboard()
            await query.edit_message_text(message, parse_mode='Markdown', reply_markup=reply_markup)
            await query.answer()
            
        except Exception as e:
            self.logger.error(f"Error handling email callback: {e}")
            await ErrorHandler.handle_booking_error(update, context, 'system_error', 
                                                   'Failed to process email edit')
    
    async def _handle_performance_menu(self, update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
        """
        Handle Performance menu option
        
        Args:
            update: The telegram update containing the callback query
            context: The callback context
            
        Returns:
            None
        """
        query = update.callback_query
        reply_markup = TelegramUI.create_back_to_menu_keyboard()
        
        await query.edit_message_text(
            "📊 Performance\n\n"
            "This feature is under development.\n\n"
            "Soon you'll be able to view:\n"
            "• Your booking success rate\n"
            "• Average response time\n"
            "• Most played courts and times\n"
            "• Weekly/monthly statistics\n"
            "• Comparison with other users\n\n"
            "Coming soon!",
            reply_markup=reply_markup
        )
    
    async def _handle_reservations_menu(self, update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
        """
        Handle Reservations menu option - show all user reservations
        
        Shows both queued and confirmed reservations with management options
        For admins, shows option to view all users' reservations
        
        Args:
            update: The telegram update containing the callback query
            context: The callback context
            
        Returns:
            None
        """
        query = update.callback_query
        user_id = query.from_user.id
        
        try:
            # Check if user is admin
            is_admin = self.user_manager.is_admin(user_id)
            
            if is_admin:
                # Show admin options menu
                keyboard = [
                    [InlineKeyboardButton("📋 My Reservations", callback_data='admin_view_my_reservations')],
                    [InlineKeyboardButton("👥 View by User", callback_data='admin_view_users_list')],
                    [InlineKeyboardButton("📊 All Reservations", callback_data='admin_view_all_reservations')],
                    [InlineKeyboardButton("⬅️ Back", callback_data='back_to_menu')]
                ]
                
                await query.edit_message_text(
                    "👮 **Admin Reservations Menu**\n\n"
                    "Select which reservations to view:",
                    parse_mode='Markdown',
                    reply_markup=InlineKeyboardMarkup(keyboard)
                )
                return
            # Get all reservations for the user
            all_reservations = []
            
            # 1. Get queued reservations
            queued = self.reservation_queue.get_user_reservations(user_id)
            for res in queued:
                res['source'] = 'queue'
                all_reservations.append(res)
            
            # 2. Get completed/immediate reservations from tracker
            if hasattr(self, 'reservation_tracker'):
                active_reservations = self.reservation_tracker.get_user_active_reservations(user_id)
                for res in active_reservations:
                    res['source'] = 'tracker'
                    all_reservations.append(res)
            
            if not all_reservations:
                await query.edit_message_text(
                    "📅 **My Reservations**\n\n"
                    "You don't have any active reservations.\n\n"
                    "Use '🎾 Reserve Court' to make a booking!",
                    parse_mode='Markdown',
                    reply_markup=TelegramUI.create_back_to_menu_keyboard()
                )
                return
            
            # Sort by date and time
            all_reservations.sort(key=lambda x: (x.get('target_date', x.get('date', '')), 
                                                x.get('target_time', x.get('time', ''))))
            
            # Create reservation list with management buttons
            keyboard = []
            message = "📅 **My Reservations**\n\n"
            
            for i, res in enumerate(all_reservations):
                # Format reservation info
                date_str = res.get('target_date', res.get('date', 'Unknown'))
                time_str = res.get('target_time', res.get('time', 'Unknown'))
                court_info = res.get('court_preferences', res.get('court', 'TBD'))
                
                if isinstance(court_info, list):
                    court_str = f"Courts {', '.join(map(str, court_info))}"
                else:
                    court_str = f"Court {court_info}"
                
                status = res.get('status', 'pending')
                status_emoji = {
                    'pending': '⏳',
                    'confirmed': '✅',
                    'active': '✅',
                    'completed': '✅',
                    'failed': '❌',
                    'cancelled': '🚫'
                }.get(status, '❓')
                
                message += f"{i+1}. {status_emoji} **{date_str} at {time_str}**\n"
                message += f"   {court_str}\n"
                
                # Add management button for each reservation
                button_text = f"Manage #{i+1}"
                callback_data = f"manage_res_{res['id']}"
                keyboard.append([InlineKeyboardButton(button_text, callback_data=callback_data)])
            
            # Add back button
            keyboard.append([InlineKeyboardButton("⬅️ Back to Menu", callback_data='back_to_menu')])
            
            reply_markup = InlineKeyboardMarkup(keyboard)
            
            await query.edit_message_text(
                message,
                parse_mode='Markdown',
                reply_markup=reply_markup
            )
            
        except Exception as e:
            self.logger.error(f"Error in reservations menu: {e}")
            await query.edit_message_text(
                "❌ Error loading reservations. Please try again.",
                reply_markup=TelegramUI.create_back_to_menu_keyboard()
            )
    
    async def _handle_help_menu(self, update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
        """
        Handle Help menu option
        
        Args:
            update: The telegram update containing the callback query
            context: The callback context
            
        Returns:
            None
        """
        query = update.callback_query
        reply_markup = TelegramUI.create_back_to_menu_keyboard()
        
        await query.edit_message_text(
            "💡 **Help - LVBot Tennis Court Assistant**\n\n"
            "🎾 **Welcome to LVBot!**\n\n"
            "LVBot is your automated tennis court booking assistant for Club La Villa. "
            "We help you secure court reservations with intelligent monitoring and "
            "automated booking capabilities.\n\n"
            "**🚀 Key Features:**\n"
            "• Real-time court availability checking\n"
            "• Smart reservation queue management\n"
            "• 48-hour advance booking window\n"
            "• Automated booking execution\n"
            "• Personal reservation tracking\n\n"
            "**📱 Available Commands:**\n"
            "• `/start` - Show the main menu\n"
            "• `/check_courts` - Quick availability check\n\n"
            "**📋 How to Use:**\n"
            "1️⃣ **Reserve Court** - Check real-time availability\n"
            "2️⃣ **My Reservations** - View your bookings\n"
            "3️⃣ **Queue Booking** - Schedule future bookings (coming soon)\n"
            "4️⃣ **Settings** - Customize preferences (coming soon)\n\n"
            "**⚠️ Important Notes:**\n"
            "• Courts open for booking exactly 48 hours in advance\n"
            "• All availability is checked in real-time\n"
            "• Queue system executes bookings automatically\n"
            "• Keep your profile updated for smooth bookings\n\n"
            "**🆘 Need Support?**\n"
            "Contact the admin team for assistance!",
            parse_mode='Markdown',
            reply_markup=reply_markup
        )
    
    async def _handle_about_menu(self, update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
        """
        Handle About menu option
        
        Shows information about LVBot, its features, and technical details
        
        Args:
            update: The telegram update containing the callback query
            context: The callback context
            
        Returns:
            None
        """
        query = update.callback_query
        reply_markup = TelegramUI.create_back_to_menu_keyboard()
        
        await query.edit_message_text(
            "ℹ️ **About LVBot**\n\n"
            "🎾 **LVBot - Tennis Court Booking Assistant**\n\n"
            "LVBot is an intelligent automation system designed to streamline "
            "tennis court reservations at Club La Villa. Built with advanced "
            "browser automation and real-time monitoring capabilities.\n\n"
            "**🔧 Technical Features:**\n"
            "• Playwright-powered browser automation\n"
            "• Async/await architecture for performance\n"
            "• Multi-browser parallel processing\n"
            "• Smart refresh strategies\n"
            "• Persistent reservation queue\n\n"
            "**📊 System Stats:**\n"
            "• 48-hour booking window monitoring\n"
            "• Real-time availability detection\n"
            "• Automated queue processing\n"
            "• Error handling and recovery\n\n"
            "**👥 Development:**\n"
            "Built for tennis enthusiasts at Club La Villa\n"
            "Continuously improving with user feedback\n\n"
            "**📅 Version:** Phase 1 - Core Functionality\n"
            "**🏗️ Architecture:** Modular Python/Telegram Bot\n\n"
            "Questions or suggestions? Contact the development team!",
            parse_mode='Markdown',
            reply_markup=reply_markup
        )
    
    async def _handle_admin_menu(self, update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
        """
        Handle Admin menu option with authorization check
        
        Verifies user has admin privileges before displaying admin panel.
        Logs unauthorized access attempts for security monitoring.
        
        Args:
            update: The telegram update containing the callback query
            context: The callback context
            
        Returns:
            None
        """
        query = update.callback_query
        user_id = query.from_user.id
        
        try:
            # Authorization check - retrieve user profile
            user_profile = self.user_manager.get_user(user_id)
            
            # Check if user exists and has admin privileges
            if user_profile is None or not user_profile.get('is_admin', False):
                # Log unauthorized access attempt
                self.logger.warning(f"Unauthorized admin access attempt by user_id: {user_id}")
                
                # Send unauthorized message
                reply_markup = TelegramUI.create_back_to_menu_keyboard()
                await query.edit_message_text(
                    "🔐 **Access Denied**\n\n"
                    "You are not authorized to access the Admin Panel.\n\n"
                    "Admin privileges are restricted to authorized personnel only. "
                    "If you believe this is an error, please contact the system administrator.",
                    parse_mode='Markdown',
                    reply_markup=reply_markup
                )
                return
            
            # User is authorized - display admin menu
            self.logger.info(f"Admin access granted to user_id: {user_id}")
            
            # Get pending user count for display (placeholder - implement when user approval system exists)
            pending_count = 0  # TODO: Implement pending user count when approval system is added
            
            # Create admin menu keyboard
            reply_markup = TelegramUI.create_admin_menu_keyboard(pending_count)
            
            # Display admin panel
            await query.edit_message_text(
                "👮 **Admin Panel**\n\n"
                "🔧 **System Management Dashboard**\n\n"
                "Welcome to the LVBot administration interface. "
                "Use the options below to manage users, monitor system performance, "
                "and configure bot settings.\n\n"
                "⚠️ **Notice**: All admin actions are logged for security purposes.",
                parse_mode='Markdown',
                reply_markup=reply_markup
            )
            
        except Exception as e:
            await ErrorHandler.handle_booking_error(update, context, 'system_error', 
                                                   'Error accessing admin panel')
    
    async def _handle_queue_booking_menu(self, update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
        """
        Handle Queue Booking menu option
        
        Shows date selection for queued reservation booking
        
        Args:
            update: The telegram update containing the callback query
            context: The callback context
            
        Returns:
            None
        """
        query = update.callback_query
        
        # Safely answer the callback query
        try:
            await query.answer()
        except Exception as e:
            self.logger.warning(f"Failed to answer queue booking menu callback: {e}")
        
        # Set state for queue booking flow
        context.user_data['current_flow'] = 'queue_booking'
        
        # For queue booking, only show dates that have slots beyond 48 hours
        dates = []
        today = date.today()
        
        # Import court hours from constants and timezone
        from lvbot.infrastructure.constants import COURT_HOURS, get_court_hours
        import pytz
        
        # Use Mexico City timezone for accurate calculations
        mexico_tz = pytz.timezone('America/Mexico_City')
        current_time = datetime.now(mexico_tz)
        
        self.logger.info(f"""QUEUE BOOKING DATE FILTERING START
        Current time (Mexico): {current_time}
        Current date: {today}
        48-hour threshold: {current_time + timedelta(hours=48)}
        Checking {self.QUEUE_BOOKING_WINDOW_DAYS} days ahead
        """)
        
        for i in range(self.QUEUE_BOOKING_WINDOW_DAYS):
            check_date = today + timedelta(days=i)
            
            # Check if any time slot on this date is beyond 48 hours
            has_available_slots = False
            first_available_slot = None
            slots_checked = 0
            
            for hour_str in get_court_hours(check_date):
                hour, minute = map(int, hour_str.split(':'))
                # Create timezone-aware datetime for Mexico City
                slot_datetime_naive = datetime.combine(check_date, datetime.min.time().replace(hour=hour, minute=minute))
                slot_datetime = mexico_tz.localize(slot_datetime_naive)
                
                # Calculate hours until slot
                time_diff = slot_datetime - current_time
                hours_until_slot = time_diff.total_seconds() / 3600
                slots_checked += 1
                
                if hours_until_slot > 48:
                    has_available_slots = True
                    if not first_available_slot:
                        first_available_slot = f"{hour_str} ({hours_until_slot:.1f}h away)"
                    break
            
            # Log detailed info for this date
            self.logger.info(f"""Date check: {check_date.strftime('%A, %B %d, %Y')}
            - Slots checked: {slots_checked}/{len(get_court_hours(check_date))}
            - Has slots > 48h: {has_available_slots}
            - First available: {first_available_slot or 'None'}
            """)
            
            # Only add dates that have available slots
            if has_available_slots:
                # Format label based on position
                if check_date == today:
                    label = f"Today ({check_date.strftime('%b %d')})"
                elif check_date == today + timedelta(days=1):
                    label = f"Tomorrow ({check_date.strftime('%b %d')})"
                else:
                    label = check_date.strftime("%a, %b %d")
                dates.append((check_date, label))
                self.logger.info(f"✅ Added to menu: {label}")
        
        # Check if we have any available dates
        if not dates:
            # No dates available - all slots are within 48 hours
            self.logger.info("❌ NO DATES AVAILABLE - All slots within 48 hours")
            reply_markup = TelegramUI.create_back_to_menu_keyboard()
            await query.edit_message_text(
                "⏰ Queue Booking\n\n"
                "❌ No dates available for queue booking.\n\n"
                "All available time slots are within the 48-hour booking window. "
                "Please use the 'Check Availability' option for immediate bookings.",
                reply_markup=reply_markup
            )
            return
        
        # Log what we're showing to the user
        self.logger.info(f"""QUEUE BOOKING MENU - Showing dates to user:
        Total dates: {len(dates)}
        Dates shown: {[label for _, label in dates]}
        """)
        
        # Create date selection keyboard
        keyboard = TelegramUI.create_date_selection_keyboard(dates)
        
        await query.edit_message_text(
            "⏰ Queue Booking\n\n"
            "📅 Select a date for your queued reservation:\n\n"
            "ℹ️ Note: Only time slots more than 48 hours away will be shown.",
            reply_markup=keyboard
        )
    
    async def _handle_queue_booking_date_selection(self, update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
        """
        Handle date selection for queue booking flow
        
        Processes the selected date and prompts user for time selection
        
        Args:
            update: The telegram update containing the callback query
            context: The callback context
            
        Returns:
            None
        """
        query = update.callback_query
        
        # Safely answer the callback query
        try:
            await query.answer()
        except Exception as e:
            self.logger.warning(f"Failed to answer date selection callback: {e}")
            
        callback_data = query.data
        
        # Parse date from callback data using helper function
        selected_date = DateTimeHelpers.parse_callback_date(callback_data)
        if selected_date is None:
            date_str = callback_data.replace('date_', '') if callback_data.startswith('date_') else callback_data
            self.logger.error(f"Invalid date format in queue booking callback: {date_str}")
            await query.edit_message_text(
                f"❌ Invalid date format received: {date_str}. Please try again."
            )
            return
        
        # Store selected date in user context
        context.user_data['queue_booking_date'] = selected_date
        
        # Use centralized court hours from constants
        all_court_hours = get_court_hours(selected_date)
        
        # Filter out time slots that are within 48 hours
        import pytz
        mexico_tz = pytz.timezone('America/Mexico_City')
        current_time = datetime.now(mexico_tz)
        available_hours = []
        
        self.logger.info(f"""QUEUE TIME SLOT FILTERING
        Selected date: {selected_date}
        Current time (Mexico): {current_time}
        Checking {len(all_court_hours)} time slots
        """)
        
        for hour_str in all_court_hours:
            # Create datetime for this slot
            hour, minute = map(int, hour_str.split(':'))
            slot_datetime_naive = datetime.combine(selected_date, datetime.min.time().replace(hour=hour, minute=minute))
            slot_datetime = mexico_tz.localize(slot_datetime_naive)
            
            # Check if more than 48 hours away
            time_diff = slot_datetime - current_time
            hours_until_slot = time_diff.total_seconds() / 3600
            
            if hours_until_slot > 48:
                available_hours.append(hour_str)
                self.logger.info(f"✅ {hour_str} - {hours_until_slot:.1f}h away - AVAILABLE")
            else:
                self.logger.info(f"❌ {hour_str} - {hours_until_slot:.1f}h away - TOO SOON")
        
        # Check if we have any available time slots
        if not available_hours:
            self.logger.info("❌ NO TIME SLOTS AVAILABLE on this date")
            await query.edit_message_text(
                f"⚠️ **No time slots available**\n\n"
                f"📅 Date: {selected_date.strftime('%A, %B %d, %Y')}\n\n"
                f"All time slots on this date are within 48 hours.\n"
                f"Please select a later date for queue booking.",
                parse_mode='Markdown',
                reply_markup=InlineKeyboardMarkup([[
                    InlineKeyboardButton("🔙 Back to Dates", callback_data="queue_booking")
                ]])
            )
            return
        
        # Log what time slots we're showing
        self.logger.info(f"""QUEUE TIME SLOTS - Showing to user:
        Date: {selected_date.strftime('%A, %B %d, %Y')}
        Available slots: {len(available_hours)}
        Times: {available_hours}
        """)
        
        # Create time selection keyboard for queue booking flow
        reply_markup = TelegramUI.create_time_selection_keyboard(
            available_times=available_hours,
            selected_date=selected_date.strftime('%Y-%m-%d'),
            flow_type='queue_booking'
        )
        
        # Show time selection interface
        await query.edit_message_text(
            f"⏰ **Queue Booking**\n\n"
            f"📅 Selected Date: {selected_date.strftime('%A, %B %d, %Y')}\n\n"
            f"⏱️ Select a time for your queued reservation:\n"
            f"ℹ️ {len(available_hours)} time slots available (48+ hours away)",
            parse_mode='Markdown',
            reply_markup=reply_markup
        )
    
    async def _show_queue_time_selection(self, update: Update, context: ContextTypes.DEFAULT_TYPE, selected_date: date) -> None:
        """
        Show time selection for queue booking with 48h filtering (used in test mode)
        
        Args:
            update: Telegram update object
            context: Callback context
            selected_date: The selected date object
        """
        query = update.callback_query
        
        # Use centralized court hours from constants
        all_court_hours = get_court_hours(selected_date)
        
        # In test mode, allow all hours (skip 48h filtering for testing)
        from lvbot.infrastructure.constants import TEST_MODE_ENABLED, TEST_MODE_ALLOW_WITHIN_48H
        
        if TEST_MODE_ENABLED and TEST_MODE_ALLOW_WITHIN_48H:
            # Test mode: show all available hours
            available_hours = all_court_hours
            self.logger.info(f"🧪 TEST MODE: Showing all {len(available_hours)} time slots for {selected_date}")
        else:
            # Normal mode: filter out times within 48 hours
            import pytz
            mexico_tz = pytz.timezone('America/Mexico_City')
            current_time = datetime.now(mexico_tz)
            available_hours = []
            
            for hour_str in all_court_hours:
                hour, minute = map(int, hour_str.split(':'))
                slot_datetime_naive = datetime.combine(selected_date, datetime.min.time().replace(hour=hour, minute=minute))
                slot_datetime = mexico_tz.localize(slot_datetime_naive)
                time_diff = slot_datetime - current_time
                hours_until_slot = time_diff.total_seconds() / 3600
                
                if hours_until_slot > 48:
                    available_hours.append(hour_str)
        
        # Check if we have any available time slots
        if not available_hours:
            await query.edit_message_text(
                f"⚠️ **No time slots available**\n\n"
                f"📅 Date: {selected_date.strftime('%A, %B %d, %Y')}\n\n"
                f"All time slots on this date are within 48 hours.\n"
                f"Please select a later date for queue booking.",
                parse_mode='Markdown',
                reply_markup=InlineKeyboardMarkup([[
                    InlineKeyboardButton("🔙 Back to Dates", callback_data="queue_booking")
                ]])
            )
            return
        
        # Create time selection keyboard for queue booking flow
        reply_markup = TelegramUI.create_time_selection_keyboard(
            available_times=available_hours,
            selected_date=selected_date.strftime('%Y-%m-%d'),
            flow_type='queue_booking'
        )
        
        # Show time selection interface
        await query.edit_message_text(
            f"⏰ **Queue Booking**\n\n"
            f"📅 Selected Date: {selected_date.strftime('%A, %B %d, %Y')}\n\n"
            f"⏱️ Select a time for your queued reservation:\n"
            f"ℹ️ {len(available_hours)} time slots available",
            parse_mode='Markdown',
            reply_markup=reply_markup
        )
    
    async def _handle_queue_booking_time_selection(self, update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
        """
        Handle time selection for queue booking flow
        
        Processes the selected time and prompts user for court selection
        
        Args:
            update: The telegram update containing the callback query
            context: The callback context
            
        Returns:
            None
        """
        query = update.callback_query
        
        # Safely answer the callback query
        try:
            await query.answer()
        except Exception as e:
            self.logger.warning(f"Failed to answer time selection callback: {e}")
            
        callback_data = query.data
        
        # Parse time from callback data (format: queue_time_YYYY-MM-DD_HH:MM)
        try:
            parts = callback_data.replace('queue_time_', '').split('_')
            if len(parts) != 2:
                raise ValueError("Invalid callback format")
            
            callback_date_str, selected_time = parts
            # Validate callback date matches expected format
            callback_date = datetime.strptime(callback_date_str, '%Y-%m-%d').date()
        except (ValueError, IndexError) as e:
            self.logger.error(f"Invalid queue time callback format: {callback_data}")
            await query.edit_message_text(
                f"❌ Invalid time selection format received: {callback_data}. Please try again."
            )
            return
        
        # Check if this is a modification flow
        modifying_id = context.user_data.get('modifying_reservation_id')
        modifying_option = context.user_data.get('modifying_option')
        
        if modifying_id and modifying_option == 'time':
            # Update the reservation time
            reservation = self.reservation_queue.get_reservation(modifying_id)
            if reservation:
                reservation['target_time'] = selected_time
                self.reservation_queue.update_reservation(modifying_id, reservation)
                
                # Clear modification context
                context.user_data.pop('modifying_reservation_id', None)
                context.user_data.pop('modifying_option', None)
                
                # Show success message
                await query.edit_message_text(
                    f"✅ **Time Updated!**\n\n"
                    f"Your reservation time has been changed to {selected_time}.",
                    parse_mode='Markdown',
                    reply_markup=InlineKeyboardMarkup([
                        [InlineKeyboardButton("📋 View Reservation", callback_data=f"manage_queue_{modifying_id}")],
                        [InlineKeyboardButton("🏠 Main Menu", callback_data='back_to_menu')]
                    ])
                )
                return
        
        # Store selected time in user context
        context.user_data['queue_booking_time'] = selected_time
        
        # Use stored date as primary source (callback date for validation only)
        selected_date = context.user_data.get('queue_booking_date')
        if selected_date is None:
            self.logger.error("Missing queue_booking_date in user context")
            await query.edit_message_text(
                "❌ Session expired. Please start the booking process again."
            )
            return
        
        # Validate callback date matches stored date
        if selected_date != callback_date:
            self.logger.warning(f"Date mismatch: stored={selected_date}, callback={callback_date}")
            await ErrorHandler.handle_booking_error(update, context, 'invalid_date', 
                                                   'Date mismatch between stored and callback data. Please restart the booking process.')
            return
        
        # Create court selection keyboard using class constant
        reply_markup = TelegramUI.create_queue_court_selection_keyboard(self.AVAILABLE_COURTS)
        
        # Show court selection interface
        await query.edit_message_text(
            f"⏰ **Queue Booking**\n\n"
            f"📅 Date: {selected_date.strftime('%A, %B %d, %Y')}\n"
            f"⏱️ Time: {selected_time}\n\n"
            f"🎾 Select your preferred court(s) for the reservation:",
            parse_mode='Markdown',
            reply_markup=reply_markup
        )
    
    async def _handle_queue_booking_court_selection(self, update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
        """
        Handle court selection for queue booking flow
        
        Processes the selected court(s) and presents final confirmation
        
        Args:
            update: The telegram update containing the callback query
            context: The callback context
            
        Returns:
            None
        """
        query = update.callback_query
        
        # Safely answer the callback query
        try:
            await query.answer()
        except Exception as e:
            self.logger.warning(f"Failed to answer court selection callback: {e}")
            
        callback_data = query.data
        
        # Parse court selection from callback data
        if callback_data == 'queue_court_all':
            selected_courts = self.AVAILABLE_COURTS.copy()
        elif callback_data.startswith('queue_court_'):
            try:
                court_number = int(callback_data.replace('queue_court_', ''))
                if court_number in self.AVAILABLE_COURTS:
                    selected_courts = [court_number]
                else:
                    raise ValueError(f"Invalid court number: {court_number}")
            except ValueError as e:
                self.logger.error(f"Invalid queue court callback: {callback_data}")
                await query.edit_message_text(
                    f"❌ Invalid court selection received: {callback_data}. Please try again."
                )
                return
        else:
            self.logger.error(f"Unrecognized queue court callback: {callback_data}")
            await query.edit_message_text(
                "❌ Invalid court selection. Please try again."
            )
            return
        
        # Check if this is a modification flow
        modifying_id = context.user_data.get('modifying_reservation_id')
        modifying_option = context.user_data.get('modifying_option')
        
        if modifying_id and modifying_option == 'courts':
            # Update the reservation courts
            reservation = self.reservation_queue.get_reservation(modifying_id)
            if reservation:
                reservation['court_preferences'] = selected_courts
                self.reservation_queue.update_reservation(modifying_id, reservation)
                
                # Clear modification context
                context.user_data.pop('modifying_reservation_id', None)
                context.user_data.pop('modifying_option', None)
                
                # Format courts text
                if len(selected_courts) == len(self.AVAILABLE_COURTS):
                    courts_text = "All Courts"
                else:
                    courts_text = ', '.join([f"Court {court}" for court in sorted(selected_courts)])
                
                # Show success message
                await query.edit_message_text(
                    f"✅ **Courts Updated!**\n\n"
                    f"Your court preference has been changed to: {courts_text}",
                    parse_mode='Markdown',
                    reply_markup=InlineKeyboardMarkup([
                        [InlineKeyboardButton("📋 View Reservation", callback_data=f"manage_queue_{modifying_id}")],
                        [InlineKeyboardButton("🏠 Main Menu", callback_data='back_to_menu')]
                    ])
                )
                return
        
        # Store selected courts in user context
        context.user_data['queue_booking_courts'] = selected_courts
        
        # Retrieve stored booking details
        selected_date = context.user_data.get('queue_booking_date')
        selected_time = context.user_data.get('queue_booking_time')
        
        if not selected_date or not selected_time:
            self.logger.error("Missing booking details in user context")
            await query.edit_message_text(
                "❌ Session expired. Please start the booking process again."
            )
            return
        
        # Format court list for display
        if len(selected_courts) == len(self.AVAILABLE_COURTS):
            courts_text = "All Courts"
        else:
            courts_text = ', '.join([f"Court {court}" for court in sorted(selected_courts)])
        
        # Store complete reservation details for final confirmation
        # Aligned with FEATURE_SPECS.md Queue Entry Structure
        context.user_data['queue_booking_summary'] = {
            'user_id': query.from_user.id,
            'target_date': selected_date.strftime('%Y-%m-%d'),
            'target_time': selected_time,
            'court_preferences': selected_courts,
            'created_at': datetime.now().isoformat()
        }
        
        # Create confirmation keyboard
        reply_markup = TelegramUI.create_queue_confirmation_keyboard()
        
        # Show final confirmation
        await query.edit_message_text(
            f"⏰ **Queue Booking Confirmation**\n\n"
            f"📅 Date: {selected_date.strftime('%A, %B %d, %Y')}\n"
            f"⏱️ Time: {selected_time}\n"
            f"🎾 Courts: {courts_text}\n\n"
            f"🤖 This reservation will be queued and automatically booked when the booking window opens.\n\n"
            f"**Confirm to add this reservation to your queue?**",
            parse_mode='Markdown',
            reply_markup=reply_markup
        )
    
    async def _handle_queue_booking_confirm(self, update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
        """
        Handle confirmation of queue booking reservation
        
        Adds the reservation to the queue and provides success feedback
        
        Args:
            update: The telegram update containing the callback query
            context: The callback context
            
        Returns:
            None
        """
        query = update.callback_query
        
        # Safely answer the callback query
        try:
            await query.answer()
        except Exception as e:
            self.logger.warning(f"Failed to answer booking confirmation callback: {e}")
        
        # Retrieve the complete booking summary
        booking_summary = context.user_data.get('queue_booking_summary')
        if not booking_summary:
            self.logger.error("Missing queue_booking_summary in user context")
            await query.edit_message_text(
                "❌ Session expired. Please start the booking process again."
            )
            return
        
        try:
            # Add reservation to the queue
            reservation_id = self.reservation_queue.add_reservation(booking_summary)
            
            # Format court list for display
            courts = booking_summary['court_preferences']
            if len(courts) == len(self.AVAILABLE_COURTS):
                courts_text = "All Courts"
            else:
                courts_text = ', '.join([f"Court {court}" for court in sorted(courts)])
            
            # Clear queue booking state from context
            self._clear_queue_booking_state(context)
            
            # Create back to menu keyboard
            reply_markup = TelegramUI.create_back_to_menu_keyboard()
            
            # Parse date from string format for display
            target_date = datetime.strptime(booking_summary['target_date'], '%Y-%m-%d').date()
            
            # Import test mode constants
            from lvbot.infrastructure.constants import TEST_MODE_ENABLED, TEST_MODE_TRIGGER_DELAY_MINUTES
            
            # Build success message
            success_message = (
                f"✅ **Reservation Added to Queue!**\n\n"
                f"📅 Date: {target_date.strftime('%A, %B %d, %Y')}\n"
                f"⏱️ Time: {booking_summary['target_time']}\n"
                f"🎾 Courts: {courts_text}\n\n"
                f"🤖 **Queue ID:** {reservation_id[:8]}...\n\n"
            )
            
            if TEST_MODE_ENABLED:
                success_message += (
                    f"🧪 **TEST MODE ACTIVE**\n"
                    f"This reservation will be executed in {TEST_MODE_TRIGGER_DELAY_MINUTES} minutes!\n\n"
                )
            else:
                success_message += (
                    f"Your reservation has been successfully added to the queue. "
                    f"The bot will automatically attempt to book this court when the booking window opens.\n\n"
                )
            
            success_message += f"You can view your queued reservations anytime using the **'My Reservations'** option."
            
            # Show success message
            await query.edit_message_text(
                success_message,
                parse_mode='Markdown',
                reply_markup=reply_markup
            )
            
        except ValueError as e:
            # Handle duplicate reservation error
            self.logger.warning(f"Duplicate reservation attempt: {e}")
            
            # Create back to menu keyboard
            reply_markup = TelegramUI.create_back_to_menu_keyboard()
            
            await query.edit_message_text(
                f"⚠️ **Duplicate Reservation**\n\n"
                f"{str(e)}\n\n"
                f"You can only have one reservation per time slot. "
                f"Please check your existing reservations or choose a different time.",
                parse_mode='Markdown',
                reply_markup=reply_markup
            )
            
            # Clear queue booking state
            self._clear_queue_booking_state(context)
            
        except Exception as e:
            await ErrorHandler.handle_booking_error(update, context, 'booking_failed', 
                                                   'Failed to add reservation to queue')
    
    async def _handle_queue_booking_cancel(self, update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
        """
        Handle cancellation of queue booking reservation
        
        Cancels the booking process and cleans up state
        
        Args:
            update: The telegram update containing the callback query
            context: The callback context
            
        Returns:
            None
        """
        query = update.callback_query
        
        # Safely answer the callback query
        try:
            await query.answer()
        except Exception as e:
            self.logger.warning(f"Failed to answer booking cancellation callback: {e}")
        
        # Clear queue booking state from context
        self._clear_queue_booking_state(context)
        
        # Create back to menu keyboard
        reply_markup = TelegramUI.create_back_to_menu_keyboard()
        
        # Show cancellation message
        await query.edit_message_text(
            "❌ **Queue Booking Cancelled**\n\n"
            "Your reservation request has been cancelled. "
            "No changes have been made to your queue.\n\n"
            "You can start a new booking anytime using the main menu.",
            parse_mode='Markdown',
            reply_markup=reply_markup
        )
    
    async def _handle_back_to_queue_courts(self, update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
        """
        Handle going back to court selection from confirmation screen
        
        Returns user to the court selection step of queue booking
        
        Args:
            update: The telegram update containing the callback query
            context: The callback context
            
        Returns:
            None
        """
        query = update.callback_query
        
        # Safely answer the callback query
        await self._safe_answer_callback(query)
        
        # Retrieve stored booking details
        selected_date = context.user_data.get('queue_booking_date')
        selected_time = context.user_data.get('queue_booking_time')
        
        if not selected_date or not selected_time:
            self.logger.error("Missing booking details when going back to court selection")
            await query.edit_message_text(
                "❌ Session expired. Please start the booking process again.",
                reply_markup=TelegramUI.create_back_to_menu_keyboard()
            )
            return
        
        # Create court selection keyboard
        reply_markup = TelegramUI.create_queue_court_selection_keyboard(self.AVAILABLE_COURTS)
        
        # Show court selection interface again
        await query.edit_message_text(
            f"⏰ **Queue Booking**\n\n"
            f"📅 Date: {selected_date.strftime('%A, %B %d, %Y')}\n"
            f"⏱️ Time: {selected_time}\n\n"
            f"🎾 Select your preferred court(s) for the reservation:",
            parse_mode='Markdown',
            reply_markup=reply_markup
        )
    
    def _clear_queue_booking_state(self, context: ContextTypes.DEFAULT_TYPE) -> None:
        """
        Clear all queue booking related data from user context
        
        Removes queue booking flow state to reset the user session
        
        Args:
            context: The callback context containing user data
        """
        # Clear queue booking specific state
        self._clear_user_flow_state(context, 'queue_booking')
    
    def _clear_user_flow_state(self, context: ContextTypes.DEFAULT_TYPE, flow_prefix: str) -> None:
        """
        Generic method to clear user flow state from context
        
        Removes all keys starting with flow_prefix and common flow keys
        
        Args:
            context: The callback context containing user data
            flow_prefix: The prefix of the flow to clear (e.g., 'queue_booking')
        """
        # Define flow-specific keys based on prefix
        flow_keys = [
            f'{flow_prefix}_date',
            f'{flow_prefix}_time', 
            f'{flow_prefix}_courts',
            f'{flow_prefix}_summary',
            'current_flow'  # Common to all flows
        ]
        
        for key in flow_keys:
            context.user_data.pop(key, None)
    
    async def _handle_back_to_menu(self, update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
        """
        Handle back to menu navigation
        
        Shows the main menu again using TelegramUI
        
        Args:
            update: The telegram update containing the callback query
            context: The callback context
            
        Returns:
            None
        """
        query = update.callback_query
        user_id = query.from_user.id
        is_admin = self.user_manager.is_admin(user_id)
        
        # Get user tier
        tier = self.user_manager.get_user_tier(user_id)
        tier_badge = TelegramUI.format_user_tier_badge(tier.name)
        
        # Use the existing main menu from TelegramUI
        reply_markup = TelegramUI.create_main_menu_keyboard(is_admin=is_admin)
        
        await query.edit_message_text(
            f"🎾 Welcome to LVBot! {tier_badge}\n\nChoose an option:",
            reply_markup=reply_markup
        )
    
    async def _handle_48h_immediate_booking(self, update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
        """
        Handle immediate booking (within 48h) - goes straight to availability check
        
        Args:
            update: The telegram update containing the callback query
            context: The callback context
            
        Returns:
            None
        """
        query = update.callback_query
        user_id = query.from_user.id
        
        self.logger.info(f"User {user_id} selected immediate 48h booking")
        
        # Set state for availability checking flow
        context.user_data['current_flow'] = 'availability_check'
        
        # Show loading message
        await query.edit_message_text("🔍 Checking court availability for the next 48 hours...")
        
        try:
            # Check if browser pool is available first
            if not hasattr(self.availability_checker, 'browser_pool') or not self.availability_checker.browser_pool:
                await query.edit_message_text(
                    "⚠️ **Court Availability System Temporarily Unavailable**\n\n"
                    "The court booking system is currently experiencing connectivity issues. "
                    "This usually resolves within a few minutes.\n\n"
                    "Please try again in a few moments.",
                    reply_markup=TelegramUI.create_back_to_menu_keyboard(),
                    parse_mode='Markdown'
                )
                return
            
            # Check availability for all courts using V3 method
            # This returns: {court: {date: [times]}}
            availability_results = await self.availability_checker.check_availability()
            
            # Process results to get combined availability matrix
            if availability_results:
                # Convert V3 format to matrix format expected by UI
                # V3 format: {1: {"2025-07-30": ["10:00"], "2025-07-31": ["09:00"]}, ...}
                # Matrix format: {"2025-07-30": {1: ["10:00"], 2: ["11:00"]}, ...}
                complete_matrix = {}
                
                for court_num, dates_data in availability_results.items():
                    # Skip courts with errors
                    if isinstance(dates_data, dict) and "error" in dates_data:
                        self.logger.warning(f"Court {court_num} had error: {dates_data['error']}")
                        continue
                    
                    # Process each date for this court
                    for date_str, times in dates_data.items():
                        if date_str not in complete_matrix:
                            complete_matrix[date_str] = {}
                        complete_matrix[date_str][court_num] = times
                
                if complete_matrix:
                    # Determine available dates and default date from the complete matrix
                    available_dates = sorted(complete_matrix.keys())
                    
                    # Start with today if it has availability, otherwise tomorrow
                    today = date.today()
                    today_str = today.strftime('%Y-%m-%d')
                    tomorrow_str = (today + timedelta(days=1)).strftime('%Y-%m-%d')
                    
                    if today_str in available_dates and any(complete_matrix[today_str].values()):
                        default_date = today
                        default_date_str = today_str
                    elif tomorrow_str in available_dates:
                        default_date = today + timedelta(days=1)
                        default_date_str = tomorrow_str
                    else:
                        default_date = datetime.strptime(available_dates[0], '%Y-%m-%d').date()
                        default_date_str = available_dates[0]
                    
                    # Get times for the default date only
                    default_date_times = complete_matrix.get(default_date_str, {})
                    total_slots = sum(len(times) for times in default_date_times.values())
                    
                    # Store complete matrix in context for day cycling
                    context.user_data['complete_matrix'] = complete_matrix
                    context.user_data['available_dates'] = available_dates
                    
                    # LOG: What will be shown to user
                    self.logger.info(f"👤 USER DISPLAY - Showing availability to user {user_id}")
                    self.logger.info(f"📅 Default date: {default_date} ({default_date.strftime('%A, %B %d')})")
                    self.logger.info(f"💎 Available dates in matrix: {len(available_dates)} - {available_dates}")
                    self.logger.info(f"📊 Default date availability:")
                    for court, times in default_date_times.items():
                        self.logger.info(f"   🎾 Court {court}: {len(times)} slots - {times}")
                    
                    # Create interactive booking keyboard with matrix layout
                    keyboard = TelegramUI.create_court_availability_keyboard(
                        default_date_times, 
                        default_date_str,
                        layout_type="matrix",
                        available_dates=available_dates
                    )
                    
                    message = TelegramUI.format_interactive_availability_message(
                        default_date_times,
                        default_date,
                        total_slots,
                        layout_type="matrix"
                    )
                    
                    await query.edit_message_text(
                        message,
                        reply_markup=keyboard,
                        parse_mode='Markdown'
                    )
                else:
                    # No availability
                    keyboard = TelegramUI.create_back_to_menu_keyboard()
                    await query.edit_message_text(
                        "😔 No courts available in the next 48 hours.\n\n"
                        "💡 Try checking again later or use 'Reserve after 48h' to book further in advance.",
                        reply_markup=keyboard
                    )
            else:
                raise Exception("Failed to check availability")
                
        except Exception as e:
            self.logger.error(f"Error in immediate booking handler: {e}")
            keyboard = TelegramUI.create_back_to_menu_keyboard()
            await query.edit_message_text(
                "❌ Sorry, there was an error checking availability.\n"
                "Please try again later.",
                reply_markup=keyboard
            )
    
    async def _handle_48h_future_booking(self, update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
        """
        Handle future booking (after 48h) - show year selection
        
        Args:
            update: The telegram update containing the callback query
            context: The callback context
            
        Returns:
            None
        """
        query = update.callback_query
        user_id = query.from_user.id
        
        self.logger.info(f"User {user_id} selected future booking (after 48h)")
        
        # Set state for queue booking flow
        context.user_data['current_flow'] = 'queue_booking'
        
        # Create year selection keyboard
        keyboard = TelegramUI.create_year_selection_keyboard()
        
        await query.edit_message_text(
            "📅 Reserve Court (Future Booking)\n\n"
            "Select the year for your reservation:",
            reply_markup=keyboard
        )
    
    async def _handle_date_selection(self, update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
        """
        Handle date selection callbacks
        
        Args:
            update: The telegram update containing the callback query
            context: The callback context
            
        Returns:
            None
        """
        query = update.callback_query
        callback_data = query.data
        
        # Parse date from callback data using helper function
        selected_date = DateTimeHelpers.parse_callback_date(callback_data)
        if selected_date is None:
            date_str = callback_data.replace('date_', '') if callback_data.startswith('date_') else callback_data
            self.logger.error(f"Invalid date format in availability callback: {date_str}")
            await query.edit_message_text(
                f"❌ Invalid date format received: {date_str}. Please try again."
            )
            return
        
        # Show loading message
        await query.edit_message_text("🔍 Checking court availability, please wait...")
        
        try:
            # Check if browser pool is available
            if not hasattr(self.availability_checker, 'browser_pool') or not self.availability_checker.browser_pool:
                await query.edit_message_text(
                    "⚠️ **Court Availability System Temporarily Unavailable**\n\n"
                    "The court booking system is currently experiencing connectivity issues. "
                    "This usually resolves within a few minutes.\n\n"
                    "Please try again in a few moments.",
                    reply_markup=TelegramUI.create_back_to_menu_keyboard(),
                    parse_mode='Markdown'
                )
                return
            
            # Check all courts using V3 method
            results = await self.availability_checker.check_availability()
            
            # Find times for the selected date
            selected_date_str = selected_date.strftime('%Y-%m-%d')
            formatted_times = {}
            
            for court_num, dates_data in results.items():
                # Skip courts with errors
                if isinstance(dates_data, dict) and "error" in dates_data:
                    continue
                
                # Get times for the selected date
                if selected_date_str in dates_data:
                    times = dates_data[selected_date_str]
                    if times:
                        formatted_times[court_num] = times
            
            # Check if any slots are available
            if formatted_times:
                # Generate available dates from all courts' data
                available_dates = set()
                for court_num, dates_data in results.items():
                    if isinstance(dates_data, dict) and "error" not in dates_data:
                        available_dates.update(dates_data.keys())
                
                available_dates = sorted(list(available_dates))
                
                # Use new interactive UI for available slots with matrix layout
                message = TelegramUI.format_interactive_availability_message(
                    formatted_times,
                    selected_date,
                    layout_type="matrix"
                )
                
                # Create interactive keyboard with matrix layout
                reply_markup = TelegramUI.create_court_availability_keyboard(
                    formatted_times,
                    selected_date.strftime('%Y-%m-%d'),
                    layout_type="matrix",
                    available_dates=available_dates
                )
            else:
                # Use standard message format for no availability
                message = TelegramUI.format_availability_message(
                    {},  # Empty dict
                    selected_date,
                    show_summary=True
                )
                
                # Just back button for no availability
                reply_markup = TelegramUI.create_back_to_menu_keyboard()
            
            # Send results
            await query.edit_message_text(
                message,
                parse_mode='Markdown',
                reply_markup=reply_markup
            )
            
        except Exception as e:
            self.logger.error(f"Exception in date selection: {e}")
            await ErrorHandler.handle_booking_error(update, context, 'system_error', 
                                                   'Failed to check court availability')
    
    async def _handle_year_selection(self, update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
        """
        Handle year selection for future booking
        
        Args:
            update: The telegram update containing the callback query
            context: The callback context
            
        Returns:
            None
        """
        query = update.callback_query
        callback_data = query.data
        
        # Extract year from callback data
        year = int(callback_data.split('_')[1])
        
        # Store selected year in context
        context.user_data['selected_year'] = year
        
        # Create month selection keyboard
        keyboard = TelegramUI.create_month_selection_keyboard(year)
        
        await query.edit_message_text(
            f"📅 Reserve Court - {year}\n\n"
            "Select the month for your reservation:",
            reply_markup=keyboard
        )
    
    async def _handle_month_selection(self, update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
        """
        Handle month selection for future booking
        
        Args:
            update: The telegram update containing the callback query
            context: The callback context
            
        Returns:
            None
        """
        query = update.callback_query
        callback_data = query.data
        
        # Extract year and month from callback data (format: month_YYYY_MM)
        parts = callback_data.split('_')
        year = int(parts[1])
        month = int(parts[2])
        
        # Store selected month in context
        context.user_data['selected_month'] = month
        
        # Log what month was selected
        self.logger.info(f"""FUTURE BOOKING MONTH SELECTION
        User: {query.from_user.id}
        Selected: {year}-{month:02d}
        Current flow: {context.user_data.get('current_flow', 'unknown')}
        """)
        
        # Create day selection calendar keyboard
        # For queue booking flow, pass the flow type to enable filtering
        flow_type = context.user_data.get('current_flow', 'immediate')
        keyboard = TelegramUI.create_day_selection_keyboard(year, month, flow_type=flow_type)
        
        await query.edit_message_text(
            f"📅 Reserve Court\n\n"
            "Select the date for your reservation:",
            reply_markup=keyboard
        )
    
    async def _handle_future_date_selection(self, update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
        """
        Handle future date selection - route to queue booking flow
        
        Args:
            update: The telegram update containing the callback query
            context: The callback context
            
        Returns:
            None
        """
        query = update.callback_query
        callback_data = query.data
        
        # Extract date from callback data (format: future_date_YYYY-MM-DD)
        date_str = callback_data.replace('future_date_', '')
        
        try:
            # Parse the date
            selected_date = datetime.strptime(date_str, '%Y-%m-%d').date()
            
            # Check if this is a modification flow
            modifying_id = context.user_data.get('modifying_reservation_id')
            modifying_option = context.user_data.get('modifying_option')
            
            if modifying_id and modifying_option == 'date':
                # Update the reservation date
                reservation = self.reservation_queue.get_reservation(modifying_id)
                if reservation:
                    reservation['target_date'] = selected_date.strftime('%Y-%m-%d')
                    self.reservation_queue.update_reservation(modifying_id, reservation)
                    
                    # Clear modification context
                    context.user_data.pop('modifying_reservation_id', None)
                    context.user_data.pop('modifying_option', None)
                    
                    # Format date for display
                    day = selected_date.day
                    if 10 <= day % 100 <= 20:
                        suffix = 'th'
                    else:
                        suffix = {1: 'st', 2: 'nd', 3: 'rd'}.get(day % 10, 'th')
                    date_str_formatted = selected_date.strftime(f'%B {day}{suffix}, %Y')
                    
                    # Show success message
                    await query.edit_message_text(
                        f"✅ **Date Updated!**\n\n"
                        f"Your reservation date has been changed to {date_str_formatted}.",
                        parse_mode='Markdown',
                        reply_markup=InlineKeyboardMarkup([
                            [InlineKeyboardButton("📋 View Reservation", callback_data=f"manage_queue_{modifying_id}")],
                            [InlineKeyboardButton("🏠 Main Menu", callback_data='back_to_menu')]
                        ])
                    )
                    return
            
            # Check if date is more than 48h in future
            from lvbot.infrastructure.constants import TEST_MODE_ENABLED, TEST_MODE_ALLOW_WITHIN_48H
            today = date.today()
            days_ahead = (selected_date - today).days
            
            if days_ahead < 2 and not (TEST_MODE_ENABLED and TEST_MODE_ALLOW_WITHIN_48H):
                # Date is within 48h, suggest immediate booking (unless in test mode)
                keyboard = InlineKeyboardMarkup([
                    [InlineKeyboardButton("🏃‍♂️ Use Immediate Booking", callback_data='reserve_48h_immediate')],
                    [InlineKeyboardButton("⬅️ Back", callback_data='back_to_booking_type')]
                ])
                
                await query.edit_message_text(
                    "⚠️ This date is within the next 48 hours.\n\n"
                    "Please use 'Reserve within 48h' for immediate booking.",
                    reply_markup=keyboard
                )
                return
            
            # Store selected date and route to queue booking flow
            context.user_data['selected_date'] = selected_date
            context.user_data['queue_booking_date'] = selected_date  # Store with expected key name
            context.user_data['current_flow'] = 'queue_booking'
            
            # Format date for display
            date_label = DateTimeHelpers.get_day_label(selected_date)
            
            # Use centralized court hours from constants
            all_time_slots = get_court_hours(selected_date)
            
            # Calculate which times are available (must be 48+ hours from now)
            import pytz
            tz = pytz.timezone('America/Mexico_City')
            now = datetime.now(tz)
            available_time_slots = []
            
            for time_str in all_time_slots:
                # Create datetime for this slot
                hour, minute = map(int, time_str.split(':'))
                slot_datetime = datetime.combine(selected_date, datetime.min.time().replace(hour=hour, minute=minute))
                slot_datetime = tz.localize(slot_datetime)
                
                # Check if it's at least 48 hours from now
                hours_until = (slot_datetime - now).total_seconds() / 3600
                if hours_until >= 48:
                    available_time_slots.append(time_str)
            
            # If no times available on this date, show error
            if not available_time_slots:
                await query.edit_message_text(
                    f"❌ No available times on {date_label}\n\n"
                    f"All time slots are within the 48-hour booking window.\n"
                    f"Please select a different date.",
                    reply_markup=TelegramUI.create_back_to_menu_keyboard()
                )
                return
            
            # Show time selection for queue booking
            keyboard = TelegramUI.create_time_selection_keyboard(
                available_time_slots, 
                selected_date.strftime('%Y-%m-%d'),
                flow_type='queue_booking'
            )
            
            await query.edit_message_text(
                f"⏰ Queue Booking - {date_label}\n\n"
                f"Select your preferred time:\n"
                f"(You'll be notified when booking opens)",
                reply_markup=keyboard
            )
            
        except Exception as e:
            self.logger.error(f"Error parsing future date: {e}")
            keyboard = TelegramUI.create_back_to_menu_keyboard()
            await query.edit_message_text(
                "❌ Invalid date selection. Please try again.",
                reply_markup=keyboard
            )
    
    async def _handle_blocked_date_selection(self, update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
        """
        Handle selection of blocked dates (within 48h) - redirect to immediate booking
        
        Args:
            update: The telegram update containing the callback query
            context: The callback context
            
        Returns:
            None
        """
        query = update.callback_query
        callback_data = query.data
        
        # Extract date from callback data (format: blocked_date_YYYY-MM-DD)
        date_str = callback_data.replace('blocked_date_', '')
        
        try:
            # Parse the date
            selected_date = datetime.strptime(date_str, '%Y-%m-%d').date()
            
            # Check if test mode allows within 48h booking
            from lvbot.infrastructure.constants import TEST_MODE_ENABLED, TEST_MODE_ALLOW_WITHIN_48H
            
            if TEST_MODE_ENABLED and TEST_MODE_ALLOW_WITHIN_48H:
                # In test mode, allow queue booking for within 48h dates
                self.logger.info(f"""BLOCKED DATE CLICKED (TEST MODE)
                User: {query.from_user.id}
                Date: {selected_date}
                Action: Allowing queue booking in test mode
                """)
                
                # Answer the callback
                await query.answer(
                    "🧪 Test mode: Proceeding with queue booking for within 48h date",
                    show_alert=True
                )
                
                # Store the selected date and continue with queue booking flow
                context.user_data['selected_date'] = date_str
                context.user_data['current_flow'] = 'queue_booking'
                
                # Store the parsed date and continue with queue booking flow
                context.user_data['queue_booking_date'] = selected_date
                
                # Show time selection for this date (copy logic from _handle_queue_booking_date_selection)
                await self._show_queue_time_selection(update, context, selected_date)
                
            else:
                # Normal mode - redirect to immediate booking
                self.logger.info(f"""BLOCKED DATE CLICKED
                User: {query.from_user.id}
                Date: {selected_date}
                Action: Redirecting to immediate booking
                """)
                
                # Answer the callback to show user feedback
                await query.answer(
                    "⚠️ This date is within 48 hours. Redirecting to immediate booking...",
                    show_alert=True
                )
                
                # Clear any queue booking state
                context.user_data.pop('current_flow', None)
                context.user_data.pop('selected_month', None)
                
                # Redirect to immediate booking menu
                await self._handle_48h_immediate_booking(update, context)
            
        except Exception as e:
            self.logger.error(f"Error handling blocked date: {e}")
            await query.answer("❌ Error processing date selection")
    
    async def _handle_back_to_month(self, update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
        """
        Handle navigation back to month selection
        
        Args:
            update: The telegram update containing the callback query
            context: The callback context
            
        Returns:
            None
        """
        query = update.callback_query
        callback_data = query.data
        
        # Extract year from callback data (format: back_to_month_YYYY)
        year = int(callback_data.split('_')[-1])
        
        # Create month selection keyboard
        keyboard = TelegramUI.create_month_selection_keyboard(year)
        
        await query.edit_message_text(
            f"📅 Reserve Court - {year}\n\n"
            "Select the month for your reservation:",
            reply_markup=keyboard
        )
    
    async def _handle_day_cycling(self, update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
        """
        Handle day cycling callback from matrix layout
        
        Args:
            update: The telegram update containing the callback query
            context: The callback context
            
        Returns:
            None
        """
        query = update.callback_query
        callback_data = query.data
        
        # Extract new date from callback data (format: cycle_day_YYYY-MM-DD)
        new_date_str = callback_data.replace('cycle_day_', '')
        
        try:
            # Parse the new date
            new_date = datetime.strptime(new_date_str, '%Y-%m-%d').date()
            
            # LOG: Day cycling action
            user_id = query.from_user.id
            self.logger.info(f"🔄 DAY CYCLING - User {user_id} switching to {new_date} ({new_date.strftime('%A, %B %d')})")
            
            # NEW ARCHITECTURE: Use pre-loaded matrix for instant day cycling
            complete_matrix = context.user_data.get('complete_matrix', {})
            available_dates = context.user_data.get('available_dates', [])
            
            if not complete_matrix:
                self.logger.warning("No pre-loaded matrix found - fetching real-time availability")
                await query.edit_message_text("🔄 Loading availability...")
                
                # Fetch fresh availability using V3 checker
                availability_results = await self.availability_checker.check_availability()
                
                # Convert V3 format to matrix format
                complete_matrix = {}
                for court_num, dates_data in availability_results.items():
                    if isinstance(dates_data, dict) and "error" in dates_data:
                        continue
                    for date_str, times in dates_data.items():
                        if date_str not in complete_matrix:
                            complete_matrix[date_str] = {}
                        complete_matrix[date_str][court_num] = times
                
                if not complete_matrix:
                    await query.edit_message_text(
                        "⚠️ **Unable to load court availability**\n\n"
                        "Please try again in a moment.",
                        reply_markup=TelegramUI.create_back_to_menu_keyboard(),
                        parse_mode='Markdown'
                    )
                    return
                
                # Update context with new matrix
                context.user_data['complete_matrix'] = complete_matrix
                available_dates = sorted(complete_matrix.keys())
                context.user_data['available_dates'] = available_dates
            
            # Get availability for the selected date from pre-loaded matrix
            selected_date_times = complete_matrix.get(new_date_str, {})
            
            # V3 returns just times (e.g., "10:00"), not time ranges
            # No need to add hour ranges anymore
            formatted_times = selected_date_times
            
            if formatted_times:
                # LOG: What will be displayed after day cycling
                total_slots = sum(len(slots) for slots in formatted_times.values())
                self.logger.info(f"📊 DAY CYCLING RESULT - Showing {total_slots} slots for {new_date}:")
                for court, times in formatted_times.items():
                    self.logger.info(f"   🎾 Court {court}: {len(times)} slots - {times}")
                
                # Create matrix layout with new date
                message = TelegramUI.format_interactive_availability_message(
                    formatted_times,
                    new_date,
                    layout_type="matrix"
                )
                
                reply_markup = TelegramUI.create_court_availability_keyboard(
                    formatted_times,
                    new_date_str,
                    layout_type="matrix",
                    available_dates=available_dates
                )
            else:
                # No availability for new date
                message = f"😔 No courts available for {TelegramUI._get_day_label_for_date(new_date_str)}"
                reply_markup = TelegramUI.create_back_to_menu_keyboard()
            
            await query.edit_message_text(
                message,
                reply_markup=reply_markup,
                parse_mode='Markdown'
            )
            
        except ValueError as e:
            self.logger.error(f"Invalid date in day cycling callback: {new_date_str}")
            await query.edit_message_text(
                "❌ Invalid date. Please try again.",
                reply_markup=TelegramUI.create_back_to_menu_keyboard()
            )
        except Exception as e:
            self.logger.error(f"Error in day cycling: {e}")
            await ErrorHandler.handle_booking_error(update, context, 'system_error', 
                                                   'Failed to cycle to new day')
    
    async def _extract_availability_for_date_cached(self, target_date: date) -> Dict[int, List]:
        """
        DEPRECATED: This method is no longer used with AvailabilityCheckerV3.
        V3 provides pre-loaded matrix data that doesn't require page extraction.
        
        Extract availability for a specific date without refreshing pages.
        Used for day cycling to avoid unnecessary page refreshes.
        
        Args:
            target_date: Date to extract availability for
            
        Returns:
            Dictionary mapping court numbers to lists of TimeSlots
        """
        import asyncio
        
        try:
            # Extract from all courts without refresh
            tasks = []
            for court in self.availability_checker.pool.courts:
                task = self._extract_court_times_for_date_cached(court, target_date)
                tasks.append(task)
            
            results = await asyncio.gather(*tasks, return_exceptions=True)
            
            # Process results and handle exceptions
            final_results = {}
            for court, result in zip(self.availability_checker.pool.courts, results):
                if isinstance(result, Exception):
                    self.logger.warning(f"Court {court} extraction failed during day cycling: {result}")
                    final_results[court] = []
                else:
                    final_results[court] = result or []
            
            return final_results
            
        except Exception as e:
            self.logger.error(f"Error in cached availability extraction: {e}")
            return {}
    
    async def _extract_court_times_for_date_cached(self, court_num: int, target_date: date) -> List:
        """
        DEPRECATED: This method is no longer used with AvailabilityCheckerV3.
        """
        """
        Extract times for specific court and date without page refresh
        
        Args:
            court_num: Court number
            target_date: Target date
            
        Returns:
            List of TimeSlots for the date
        """
        try:
            # Get browser page for this court (should already be loaded)
            page = await self.availability_checker.pool.get_page(court_num)
            if not page:
                self.logger.warning(f"No page available for court {court_num}")
                return []
            
            # FIXED: Use date-specific extraction instead of generic extraction
            from lvbot.automation.availability.time_order_extraction import AcuityTimeParser
            from lvbot.automation.forms.acuity_page_validator import AcuityPageValidator
            
            # Get the appropriate frame for extraction
            frame = await AcuityPageValidator._get_extraction_frame(page)
            if not frame:
                self.logger.warning(f"Court {court_num}: No extraction frame available")
                return []
            
            # Extract times using new time-order parser and filter for target date
            parser = AcuityTimeParser()
            times_by_day = await parser.extract_times_by_day(frame)
            target_date_str = target_date.strftime('%Y-%m-%d')
            
            if target_date_str in times_by_day:
                available_times = times_by_day[target_date_str]
                self.logger.info(f"Court {court_num}: Found {len(available_times)} times for {target_date}: {available_times}")
            else:
                available_times = []
                self.logger.warning(f"Court {court_num}: No times found for specific date {target_date}")
            
            # Convert to TimeSlot objects
            from lvbot.models.time_slot import TimeSlot
            time_slots = []
            for time_str in available_times:
                try:
                    time_slots.append(TimeSlot(
                        start_time=time_str,
                        end_time=self.availability_checker._add_hour(time_str),
                        court_number=court_num,
                        is_available=True,
                        reservation_link=""
                    ))
                except Exception as e:
                    self.logger.warning(f"Failed to create TimeSlot for {time_str}: {e}")
                    continue
            
            return time_slots
            
        except Exception as e:
            self.logger.warning(f"Court {court_num} cached extraction failed: {e}")
            return []
    
    async def _build_complete_matrix_for_all_days(self) -> Dict[str, Dict[int, List[str]]]:
        """
        DEPRECATED: This method is no longer used with AvailabilityCheckerV3.
        V3's check_availability() method provides this data directly.
        
        Build complete matrix for all available days across all courts.
        This is the NEW ARCHITECTURE that pre-loads all data once.
        
        Returns:
            Dict mapping date strings to court availability:
            {
                '2025-07-21': {1: ['09:00', '10:00'], 3: ['20:15']},
                '2025-07-22': {1: ['09:00'], 2: ['10:00'], 3: ['11:00']},
                '2025-07-23': {3: ['09:00', '10:00', '11:00']}
            }
        """
        import asyncio
        from lvbot.automation.availability.time_order_extraction import AcuityTimeParser
        from lvbot.automation.forms.acuity_page_validator import AcuityPageValidator
        
        try:
            self.logger.info("🏗️ MATRIX BUILDER - Building complete matrix for all available days")
            
            # Extract times by day for all courts in parallel
            tasks = []
            for court in self.availability_checker.pool.courts:
                task = self._extract_all_days_for_court(court)
                tasks.append(task)
            
            results = await asyncio.gather(*tasks, return_exceptions=True)
            
            # Merge results into complete matrix
            complete_matrix = {}
            
            for court, result in zip(self.availability_checker.pool.courts, results):
                if isinstance(result, Exception):
                    self.logger.warning(f"Court {court} all-days extraction failed: {result}")
                    continue
                
                # result is a dict like {'2025-07-21': ['20:15'], '2025-07-22': ['09:00', '10:00']}
                for date_str, times in result.items():
                    if date_str not in complete_matrix:
                        complete_matrix[date_str] = {}
                    complete_matrix[date_str][court] = times
            
            # LOG: Complete matrix summary
            self.logger.info(f"🏗️ MATRIX BUILDER - Complete matrix built for {len(complete_matrix)} days:")
            for date_str in sorted(complete_matrix.keys()):
                day_data = complete_matrix[date_str]
                total_slots = sum(len(times) for times in day_data.values())
                self.logger.info(f"   📅 {date_str}: {total_slots} total slots across {len(day_data)} courts")
                for court, times in day_data.items():
                    self.logger.info(f"      🎾 Court {court}: {len(times)} slots - {times}")
            
            return complete_matrix
            
        except Exception as e:
            self.logger.error(f"Failed to build complete matrix: {e}")
            return {}
    
    async def _extract_all_days_for_court(self, court_num: int) -> Dict[str, List[str]]:
        """
        DEPRECATED: This method is no longer used with AvailabilityCheckerV3.
        """
        """
        Extract times for all available days for a specific court.
        
        Args:
            court_num: Court number
            
        Returns:
            Dict mapping date strings to time lists: {'2025-07-21': ['20:15'], '2025-07-22': ['09:00']}
        """
        try:
            # Get browser page for this court
            page = await self.availability_checker.pool.get_page(court_num)
            if not page:
                self.logger.warning(f"No page available for court {court_num}")
                return {}
            
            from lvbot.automation.availability.time_order_extraction import AcuityTimeParser
            from lvbot.automation.forms.acuity_page_validator import AcuityPageValidator
            
            # Get the appropriate frame for extraction
            frame = await AcuityPageValidator._get_extraction_frame(page)
            if not frame:
                self.logger.warning(f"Court {court_num}: No extraction frame available")
                return {}
            
            # Extract ALL times by day using the new time-order parser
            parser = AcuityTimeParser()
            times_by_day = await parser.extract_times_by_day(frame)
            
            self.logger.info(f"Court {court_num}: Extracted times for {len(times_by_day)} days: {times_by_day}")
            return times_by_day
            
        except Exception as e:
            self.logger.warning(f"Court {court_num} all-days extraction failed: {e}")
            return {}
    
    async def _handle_manage_reservation(self, update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
        """
        Handle individual reservation management
        
        Shows details and actions for a specific reservation
        
        Args:
            update: The telegram update containing the callback query
            context: The callback context
        """
        query = update.callback_query
        user_id = query.from_user.id
        
        # Extract reservation ID from callback data
        reservation_id = query.data.replace('manage_res_', '')
        
        try:
            # Find the reservation
            reservation = None
            
            # Check in queue first
            queued = self.reservation_queue.get_user_reservations(user_id)
            for res in queued:
                if res.get('id') == reservation_id:
                    reservation = res
                    reservation['source'] = 'queue'
                    break
            
            # Check in tracker if not found
            if not reservation and hasattr(self, 'reservation_tracker'):
                reservation = self.reservation_tracker.get_reservation(reservation_id)
                if reservation:
                    reservation['source'] = 'tracker'
            
            if not reservation:
                await query.edit_message_text(
                    "❌ Reservation not found.\n\nIt may have been cancelled or expired.",
                    reply_markup=TelegramUI.create_back_to_menu_keyboard()
                )
                return
            
            # Format reservation details
            date_str = reservation.get('target_date', reservation.get('date', 'Unknown'))
            time_str = reservation.get('target_time', reservation.get('time', 'Unknown'))
            court_info = reservation.get('court_preferences', reservation.get('court', 'TBD'))
            status = reservation.get('status', 'pending')
            
            if isinstance(court_info, list):
                court_str = f"Courts {', '.join(map(str, court_info))}"
            else:
                court_str = f"Court {court_info}"
            
            message = f"📋 **Reservation Details**\n\n"
            message += f"📅 Date: {date_str}\n"
            message += f"⏰ Time: {time_str}\n"
            message += f"🎾 {court_str}\n"
            message += f"📊 Status: {status.capitalize()}\n"
            
            # Add confirmation ID if available
            if reservation.get('confirmation_id'):
                message += f"🔖 Confirmation: {reservation['confirmation_id']}\n"
            
            # Create action buttons based on reservation type and status
            keyboard = []
            
            if status in ['pending', 'scheduled']:
                # Can cancel queued reservations
                keyboard.append([
                    InlineKeyboardButton("❌ Cancel Reservation", 
                                       callback_data=f"res_action_cancel_{reservation_id}")
                ])
            elif status in ['confirmed', 'active', 'completed']:
                # Can cancel or modify confirmed reservations
                if reservation.get('can_cancel', True):
                    keyboard.append([
                        InlineKeyboardButton("❌ Cancel Reservation", 
                                           callback_data=f"res_action_cancel_{reservation_id}")
                    ])
                if reservation.get('can_modify', False):
                    keyboard.append([
                        InlineKeyboardButton("✏️ Modify Reservation", 
                                           callback_data=f"res_action_modify_{reservation_id}")
                    ])
            
            # Add share button
            keyboard.append([
                InlineKeyboardButton("📤 Share Details", 
                                   callback_data=f"res_action_share_{reservation_id}")
            ])
            
            # Back buttons
            keyboard.append([
                InlineKeyboardButton("⬅️ Back to Reservations", callback_data='menu_reservations'),
                InlineKeyboardButton("🏠 Main Menu", callback_data='back_to_menu')
            ])
            
            reply_markup = InlineKeyboardMarkup(keyboard)
            
            await query.edit_message_text(
                message,
                parse_mode='Markdown',
                reply_markup=reply_markup
            )
            
        except Exception as e:
            self.logger.error(f"Error managing reservation: {e}")
            await query.edit_message_text(
                "❌ Error loading reservation details.",
                reply_markup=TelegramUI.create_back_to_menu_keyboard()
            )
    
    async def _handle_manage_queue_reservation(self, update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
        """
        Handle management of a specific queued reservation
        
        Args:
            update: The telegram update
            context: The callback context
        """
        query = update.callback_query
        await self._safe_answer_callback(query)
        
        # Extract reservation ID from callback data
        reservation_id = query.data.replace('manage_queue_', '')
        
        try:
            # Get the specific queued reservation
            reservation = self.reservation_queue.get_reservation(reservation_id)
            
            if not reservation:
                await query.edit_message_text(
                    "❌ Reservation not found.",
                    reply_markup=TelegramUI.create_back_to_menu_keyboard()
                )
                return
            
            # Format reservation details
            target_date = datetime.strptime(reservation['target_date'], '%Y-%m-%d')
            day = target_date.day
            # Add ordinal suffix
            if 10 <= day % 100 <= 20:
                suffix = 'th'
            else:
                suffix = {1: 'st', 2: 'nd', 3: 'rd'}.get(day % 10, 'th')
            date_str = target_date.strftime(f'%B {day}{suffix}, %Y')
            time_str = reservation['target_time']
            
            # Format courts
            courts = reservation.get('court_preferences', [])
            if isinstance(courts, list):
                court_str = f"Courts: {', '.join(map(str, courts))}"
            else:
                court_str = f"Court: {courts}"
            
            # Check test mode
            from lvbot.infrastructure.constants import TEST_MODE_ENABLED, TEST_MODE_TRIGGER_DELAY_MINUTES
            
            # Get scheduled execution time if available
            scheduled_time_str = ""
            if 'scheduled_execution' in reservation:
                try:
                    scheduled_time = datetime.fromisoformat(reservation['scheduled_execution'])
                    scheduled_time_str = f"\n⏱️ *Scheduled Execution:* {scheduled_time.strftime('%Y-%m-%d %H:%M:%S %Z')}"
                except:
                    pass
            
            # Create detailed message
            message = f"""🎾 *Queued Reservation Details*

📅 *Date:* {date_str}
⏰ *Time:* {time_str}
🏃 *{court_str}*
⏳ *Status:* {reservation.get('status', 'pending').capitalize()}

*Created:* {reservation.get('created_at', 'Unknown')}{scheduled_time_str}

"""
            
            if TEST_MODE_ENABLED:
                message += f"🧪 *TEST MODE:* Will execute in {TEST_MODE_TRIGGER_DELAY_MINUTES} minutes after creation\n"
            else:
                message += "This reservation will be automatically booked when the 48-hour booking window opens.\n"
            
            # Create action buttons
            keyboard = [
                [InlineKeyboardButton("❌ Cancel Reservation", 
                                    callback_data=f"res_action_cancel_{reservation_id}")],
                [InlineKeyboardButton("✏️ Modify Reservation", 
                                    callback_data=f"res_action_modify_{reservation_id}")],
                [InlineKeyboardButton("📤 Share Details", 
                                    callback_data=f"res_action_share_{reservation_id}")],
                [InlineKeyboardButton("⬅️ Back to Reservations", callback_data='menu_reservations')],
                [InlineKeyboardButton("🏠 Main Menu", callback_data='back_to_menu')]
            ]
            
            reply_markup = InlineKeyboardMarkup(keyboard)
            
            await query.edit_message_text(
                message,
                parse_mode='Markdown',
                reply_markup=reply_markup
            )
            
        except Exception as e:
            self.logger.error(f"Error managing queued reservation: {e}")
            await query.edit_message_text(
                "❌ Error loading reservation details.",
                reply_markup=TelegramUI.create_back_to_menu_keyboard()
            )
    
    async def _handle_reservation_action(self, update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
        """
        Handle reservation actions (cancel, modify, share)
        
        Args:
            update: The telegram update containing the callback query
            context: The callback context
        """
        query = update.callback_query
        user_id = query.from_user.id
        callback_data = query.data
        
        try:
            # Parse action and reservation ID
            parts = callback_data.split('_')
            action = parts[2]  # cancel, modify, or share
            reservation_id = '_'.join(parts[3:])  # Handle IDs with underscores
            
            if action == 'cancel':
                await self._handle_cancel_reservation(update, context, reservation_id)
            elif action == 'modify':
                await self._handle_modify_reservation(update, context, reservation_id)
            elif action == 'share':
                await self._handle_share_reservation(update, context, reservation_id)
            else:
                self.logger.warning(f"Unknown reservation action: {action}")
                await query.answer("Unknown action")
                
        except Exception as e:
            self.logger.error(f"Error handling reservation action: {e}")
            await query.answer("Error processing action")
    
    async def _handle_cancel_reservation(self, update: Update, context: ContextTypes.DEFAULT_TYPE, 
                                        reservation_id: str) -> None:
        """Cancel a reservation"""
        query = update.callback_query
        user_id = query.from_user.id
        
        try:
            # Find and cancel the reservation
            cancelled = False
            
            # Try queue first
            reservation = self.reservation_queue.get_reservation(reservation_id)
            if reservation and reservation.get('user_id') == user_id:
                cancelled = self.reservation_queue.remove_reservation(reservation_id)
                
            # Try tracker if not in queue
            if not cancelled and hasattr(self, 'reservation_tracker'):
                reservation = self.reservation_tracker.get_reservation(reservation_id)
                if reservation and reservation.get('user_id') == user_id:
                    cancelled = self.reservation_tracker.cancel_reservation(reservation_id)
            
            if cancelled:
                await query.edit_message_text(
                    "✅ **Reservation Cancelled**\n\n"
                    "Your reservation has been cancelled successfully.",
                    parse_mode='Markdown',
                    reply_markup=InlineKeyboardMarkup([
                        [InlineKeyboardButton("📅 View Reservations", callback_data='menu_reservations')],
                        [InlineKeyboardButton("🏠 Main Menu", callback_data='back_to_menu')]
                    ])
                )
            else:
                await query.answer("Could not cancel reservation")
                
        except Exception as e:
            self.logger.error(f"Error cancelling reservation: {e}")
            await query.answer("Error cancelling reservation")
    
    async def _handle_modify_reservation(self, update: Update, context: ContextTypes.DEFAULT_TYPE, 
                                       reservation_id: str) -> None:
        """Modify a reservation"""
        query = update.callback_query
        user_id = query.from_user.id
        
        # Find the reservation
        reservation = None
        is_queued = False
        
        # Check queue first
        res = self.reservation_queue.get_reservation(reservation_id)
        if res and res.get('user_id') == user_id:
            reservation = res
            is_queued = True
            
        # Check tracker if not in queue
        if not reservation and hasattr(self, 'reservation_tracker'):
            res = self.reservation_tracker.get_reservation(reservation_id)
            if res and res.get('user_id') == user_id:
                reservation = res
        
        if not reservation:
            await query.answer("Reservation not found")
            return
        
        # For queued reservations, allow modification
        if is_queued:
            # Store reservation ID in context for modification flow
            context.user_data['modifying_reservation_id'] = reservation_id
            
            # Show modification options
            keyboard = [
                [InlineKeyboardButton("📅 Change Date", callback_data=f"modify_date_{reservation_id}")],
                [InlineKeyboardButton("⏰ Change Time", callback_data=f"modify_time_{reservation_id}")],
                [InlineKeyboardButton("🏃 Change Courts", callback_data=f"modify_courts_{reservation_id}")],
                [InlineKeyboardButton("⬅️ Back", callback_data=f"manage_queue_{reservation_id}")],
                [InlineKeyboardButton("🏠 Main Menu", callback_data='back_to_menu')]
            ]
            
            await query.edit_message_text(
                "✏️ **Modify Reservation**\n\n"
                "What would you like to change?",
                parse_mode='Markdown',
                reply_markup=InlineKeyboardMarkup(keyboard)
            )
        else:
            # For immediate/completed reservations, show coming soon
            await query.edit_message_text(
                "✏️ **Modify Reservation**\n\n"
                "Modification of confirmed bookings is coming soon!\n\n"
                "For now, you can cancel this reservation and create a new one.",
                parse_mode='Markdown',
                reply_markup=InlineKeyboardMarkup([
                    [InlineKeyboardButton("❌ Cancel Reservation", 
                                        callback_data=f"res_action_cancel_{reservation_id}")],
                    [InlineKeyboardButton("⬅️ Back", callback_data=f"manage_queue_{reservation_id}")],
                    [InlineKeyboardButton("🏠 Main Menu", callback_data='back_to_menu')]
                ])
            )
    
    async def _handle_share_reservation(self, update: Update, context: ContextTypes.DEFAULT_TYPE, 
                                      reservation_id: str) -> None:
        """Share reservation details"""
        query = update.callback_query
        user_id = query.from_user.id
        
        try:
            # Find the reservation
            reservation = None
            
            # Check queue
            res = self.reservation_queue.get_reservation(reservation_id)
            if res and res.get('user_id') == user_id:
                reservation = res
                
            # Check tracker
            if not reservation and hasattr(self, 'reservation_tracker'):
                res = self.reservation_tracker.get_reservation(reservation_id)
                if res and res.get('user_id') == user_id:
                    reservation = res
            
            if reservation:
                # Format shareable message
                date_str = reservation.get('target_date', reservation.get('date', 'Unknown'))
                time_str = reservation.get('target_time', reservation.get('time', 'Unknown'))
                court_info = reservation.get('court_preferences', reservation.get('court', 'TBD'))
                
                if isinstance(court_info, list):
                    court_str = f"Courts {', '.join(map(str, court_info))}"
                else:
                    court_str = f"Court {court_info}"
                
                share_text = f"🎾 Tennis Reservation\n"
                share_text += f"📅 {date_str} at {time_str}\n"
                share_text += f"📍 Club La Villa - {court_str}\n"
                
                # Send as a new message that can be forwarded with back button
                keyboard = [[InlineKeyboardButton("⬅️ Back to reservation", 
                                                 callback_data=f"manage_queue_{reservation_id}")]]
                
                await context.bot.send_message(
                    chat_id=user_id,
                    text=share_text,
                    reply_markup=InlineKeyboardMarkup(keyboard)
                )
                
                await query.answer("📤 Reservation details sent! You can forward the message.")
            else:
                await query.answer("Reservation not found")
                
        except Exception as e:
            self.logger.error(f"Error sharing reservation: {e}")
            await query.answer("Error sharing reservation")
    
    async def _handle_modify_option(self, update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
        """Handle modification options for queued reservations"""
        query = update.callback_query
        await self._safe_answer_callback(query)
        callback_data = query.data
        
        # Extract option and reservation ID
        if callback_data.startswith('modify_date_'):
            option = 'date'
            reservation_id = callback_data.replace('modify_date_', '')
        elif callback_data.startswith('modify_time_'):
            option = 'time'
            reservation_id = callback_data.replace('modify_time_', '')
        elif callback_data.startswith('modify_courts_'):
            option = 'courts'
            reservation_id = callback_data.replace('modify_courts_', '')
        else:
            return
        
        # Store modification context
        context.user_data['modifying_reservation_id'] = reservation_id
        context.user_data['modifying_option'] = option
        
        # Get the reservation
        reservation = self.reservation_queue.get_reservation(reservation_id)
        if not reservation:
            await query.answer("Reservation not found")
            return
        
        if option == 'date':
            # Show year selection for date modification
            keyboard = TelegramUI.create_year_selection_keyboard()
            await query.edit_message_text(
                "📅 **Select New Year**\n\n"
                "Choose the year for your reservation:",
                parse_mode='Markdown',
                reply_markup=keyboard
            )
        elif option == 'time':
            # Show time selection
            keyboard = TelegramUI.create_time_selection_keyboard_simple(reservation.date)
            await query.edit_message_text(
                "⏰ **Select New Time**\n\n"
                "Choose your preferred time:",
                parse_mode='Markdown',
                reply_markup=keyboard
            )
        elif option == 'courts':
            # Show court selection
            keyboard = TelegramUI.create_court_selection_keyboard()
            await query.edit_message_text(
                "🏃 **Select New Courts**\n\n"
                "Choose your court preferences:",
                parse_mode='Markdown',
                reply_markup=keyboard
            )
    
    async def _handle_time_modification(self, update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
        """Handle time modification from the modify menu"""
        query = update.callback_query
        await self._safe_answer_callback(query)
        
        # Extract time from callback
        time_str = query.data.replace('queue_time_modify_', '')
        
        # Get the reservation being modified
        modifying_id = context.user_data.get('modifying_reservation_id')
        if not modifying_id:
            await query.answer("Session expired. Please try again.")
            return
        
        # Update the reservation
        reservation = self.reservation_queue.get_reservation(modifying_id)
        if reservation:
            reservation['target_time'] = time_str
            self.reservation_queue.update_reservation(modifying_id, reservation)
            
            # Clear modification context
            context.user_data.pop('modifying_reservation_id', None)
            context.user_data.pop('modifying_option', None)
            
            # Show success message
            await query.edit_message_text(
                f"✅ **Time Updated!**\n\n"
                f"Your reservation time has been changed to {time_str}.",
                parse_mode='Markdown',
                reply_markup=InlineKeyboardMarkup([
                    [InlineKeyboardButton("📋 View Reservation", callback_data=f"manage_queue_{modifying_id}")],
                    [InlineKeyboardButton("🏠 Main Menu", callback_data='back_to_menu')]
                ])
            )
    
    async def _handle_unknown_menu(self, update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
        """
        Handle unknown callback data
        
        Logs the unknown callback and shows an error message
        
        Args:
            update: The telegram update containing the callback query
            context: The callback context
            
        Returns:
            None
        """
        query = update.callback_query
        self.logger.warning(f"Unknown callback data: {query.data}")
        await query.edit_message_text(
            "❓ Unknown option\n\nPlease use the menu buttons or /start to begin again."
        )
    
    async def _handle_admin_my_reservations(self, update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
        """
        Admin view of their own reservations
        
        Reuses the existing user reservations display logic
        """
        # Simply show the regular user view for the admin's own reservations
        await self._display_user_reservations(update, context, update.callback_query.from_user.id)
    
    async def _handle_admin_users_list(self, update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
        """
        Show list of users for admin to select from
        """
        query = update.callback_query
        
        try:
            # Get all users
            all_users = self.user_manager.get_all_users()
            
            if not all_users:
                await query.edit_message_text(
                    "👥 **Users List**\n\n"
                    "No users found in the system.",
                    parse_mode='Markdown',
                    reply_markup=TelegramUI.create_back_to_menu_keyboard()
                )
                return
            
            # Create buttons for each user
            keyboard = []
            for user_id, user_data in all_users.items():
                user_name = f"{user_data.get('first_name', '')} {user_data.get('last_name', '')}".strip()
                if not user_name:
                    user_name = f"User {user_id}"
                
                # Add admin badge if user is admin
                if user_data.get('is_admin', False):
                    user_name += " 👮"
                
                keyboard.append([
                    InlineKeyboardButton(
                        user_name,
                        callback_data=f"admin_view_user_{user_id}"
                    )
                ])
            
            # Add back button
            keyboard.append([InlineKeyboardButton("⬅️ Back", callback_data='menu_reservations')])
            
            await query.edit_message_text(
                "👥 **Select User**\n\n"
                "Choose a user to view their reservations:",
                parse_mode='Markdown',
                reply_markup=InlineKeyboardMarkup(keyboard)
            )
            
        except Exception as e:
            self.logger.error(f"Error showing users list: {e}")
            await query.edit_message_text(
                "❌ Error loading users list.",
                reply_markup=TelegramUI.create_back_to_menu_keyboard()
            )
    
    async def _handle_admin_all_reservations(self, update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
        """
        Show all reservations from all users
        """
        query = update.callback_query
        
        try:
            all_reservations = []
            
            # Get all users
            all_users = self.user_manager.get_all_users()
            
            # Collect reservations from all users
            for user_id in all_users.keys():
                # Get queued reservations
                queued = self.reservation_queue.get_user_reservations(user_id)
                for res in queued:
                    res['source'] = 'queue'
                    res['user_name'] = self._get_user_name(user_id)
                    all_reservations.append(res)
                
                # Get active reservations
                if hasattr(self, 'reservation_tracker'):
                    active = self.reservation_tracker.get_user_active_reservations(user_id)
                    for res in active:
                        res['source'] = 'tracker'
                        res['user_name'] = self._get_user_name(user_id)
                        all_reservations.append(res)
            
            if not all_reservations:
                await query.edit_message_text(
                    "📊 **All Reservations**\n\n"
                    "No active reservations found in the system.",
                    parse_mode='Markdown',
                    reply_markup=InlineKeyboardMarkup([
                        [InlineKeyboardButton("⬅️ Back", callback_data='menu_reservations')],
                        [InlineKeyboardButton("🏠 Main Menu", callback_data='back_to_menu')]
                    ])
                )
                return
            
            # Sort by date and time
            all_reservations.sort(key=lambda x: (
                x.get('target_date', x.get('date', '')), 
                x.get('target_time', x.get('time', ''))
            ))
            
            # Display reservations
            await self._display_all_reservations(query, all_reservations)
            
        except Exception as e:
            self.logger.error(f"Error showing all reservations: {e}")
            await query.edit_message_text(
                "❌ Error loading reservations.",
                reply_markup=TelegramUI.create_back_to_menu_keyboard()
            )
    
    async def _display_user_reservations(self, update: Update, context: ContextTypes.DEFAULT_TYPE, 
                                       target_user_id: int) -> None:
        """
        Display reservations for a specific user (reusable method)
        
        Args:
            update: The telegram update
            context: The callback context
            target_user_id: The user whose reservations to display
        """
        query = update.callback_query
        
        try:
            # Get all reservations for the user
            all_reservations = []
            
            # Get queued reservations
            queued = self.reservation_queue.get_user_reservations(target_user_id)
            for res in queued:
                res['source'] = 'queue'
                all_reservations.append(res)
            
            # Get active reservations
            if hasattr(self, 'reservation_tracker'):
                active = self.reservation_tracker.get_user_active_reservations(target_user_id)
                for res in active:
                    res['source'] = 'tracker'
                    all_reservations.append(res)
            
            if not all_reservations:
                user_name = self._get_user_name(target_user_id)
                await query.edit_message_text(
                    f"📅 **Reservations for {user_name}**\n\n"
                    f"No active reservations found.",
                    parse_mode='Markdown',
                    reply_markup=InlineKeyboardMarkup([
                        [InlineKeyboardButton("⬅️ Back", callback_data='admin_view_users_list')],
                        [InlineKeyboardButton("🏠 Main Menu", callback_data='back_to_menu')]
                    ])
                )
                return
            
            # Sort and display
            all_reservations.sort(key=lambda x: (
                x.get('target_date', x.get('date', '')), 
                x.get('target_time', x.get('time', ''))
            ))
            
            # Create buttons for each reservation
            keyboard = []
            user_name = self._get_user_name(target_user_id)
            message = f"📅 **Reservations for {user_name}**\n\n"
            
            for i, res in enumerate(all_reservations):
                # Format reservation info
                date_obj = DateTimeHelpers.parse_date_string(
                    res.get('target_date', res.get('date', ''))
                )
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
                court_info = res.get('court_preferences', res.get('court', 'TBD'))
                
                if isinstance(court_info, list):
                    court_str = ', '.join([f"C{c}" for c in court_info])
                else:
                    court_str = f"C{court_info}"
                
                status = res.get('status', 'pending')
                status_emoji = "✅" if status == 'confirmed' else "⏳"
                
                button_text = f"{status_emoji} {date_str} {time_str} - {court_str}"
                res_id = res.get('id', f"{res.get('date')}_{res.get('time')}")
                
                keyboard.append([
                    InlineKeyboardButton(
                        button_text,
                        callback_data=f"manage_queue_{res_id}"
                    )
                ])
            
            # Add navigation buttons
            keyboard.extend([
                [InlineKeyboardButton("⬅️ Back", callback_data='admin_view_users_list')],
                [InlineKeyboardButton("🏠 Main Menu", callback_data='back_to_menu')]
            ])
            
            await query.edit_message_text(
                message,
                parse_mode='Markdown',
                reply_markup=InlineKeyboardMarkup(keyboard)
            )
            
        except Exception as e:
            self.logger.error(f"Error displaying user reservations: {e}")
            await query.edit_message_text(
                "❌ Error loading reservations.",
                reply_markup=TelegramUI.create_back_to_menu_keyboard()
            )
    
    async def _display_all_reservations(self, query, all_reservations: List[Dict[str, Any]]) -> None:
        """
        Display all reservations from all users
        
        Args:
            query: The callback query
            all_reservations: List of all reservations with user info
        """
        # Group by date for better organization
        reservations_by_date = {}
        for res in all_reservations:
            date_key = res.get('target_date', res.get('date', 'Unknown'))
            if date_key not in reservations_by_date:
                reservations_by_date[date_key] = []
            reservations_by_date[date_key].append(res)
        
        # Create message
        message = "📊 **All Reservations**\n\n"
        keyboard = []
        
        for date_str in sorted(reservations_by_date.keys()):
            # Format date with ordinal suffix
            try:
                date_obj = DateTimeHelpers.parse_date_string(date_str)
                if date_obj:
                    day = date_obj.day
                    if 10 <= day % 100 <= 20:
                        suffix = 'th'
                    else:
                        suffix = {1: 'st', 2: 'nd', 3: 'rd'}.get(day % 10, 'th')
                    formatted_date = date_obj.strftime(f'%b {day}{suffix} %Y')
                else:
                    formatted_date = date_str
            except:
                formatted_date = date_str
            
            message += f"**{formatted_date}**\n"
            
            for res in reservations_by_date[date_str]:
                time_str = res.get('target_time', res.get('time', 'Unknown'))
                court_info = res.get('court_preferences', res.get('court', 'TBD'))
                user_name = res.get('user_name', 'Unknown')
                
                if isinstance(court_info, list):
                    court_str = ', '.join([f"C{c}" for c in court_info])
                else:
                    court_str = f"C{court_info}"
                
                status = res.get('status', 'pending')
                status_emoji = "✅" if status == 'confirmed' else "⏳"
                
                message += f"  {status_emoji} {time_str} - {court_str} - {user_name}\n"
            
            message += "\n"
        
        # Add navigation buttons
        keyboard = [
            [InlineKeyboardButton("⬅️ Back", callback_data='menu_reservations')],
            [InlineKeyboardButton("🏠 Main Menu", callback_data='back_to_menu')]
        ]
        
        await query.edit_message_text(
            message,
            parse_mode='Markdown',
            reply_markup=InlineKeyboardMarkup(keyboard)
        )
    
    def _get_user_name(self, user_id: int) -> str:
        """
        Get formatted user name from user ID
        
        Args:
            user_id: The user's Telegram ID
            
        Returns:
            Formatted user name or "User {id}" if not found
        """
        user_data = self.user_manager.get_user(user_id)
        if user_data:
            name = f"{user_data.get('first_name', '')} {user_data.get('last_name', '')}".strip()
            if name:
                return name
        return f"User {user_id}"
