"""
Telegram UI utility functions
Handles keyboard creation and message formatting
"""

from typing import List, Optional, Dict, Any
from telegram import InlineKeyboardButton, InlineKeyboardMarkup, ReplyKeyboardMarkup, KeyboardButton
from datetime import datetime
import math
from lvbot.infrastructure.constants import COURT_HOURS, get_court_hours


class TelegramUI:
    """Collection of Telegram UI helper functions"""
    
    @staticmethod
    def create_main_menu_keyboard(is_admin: bool = False, pending_count: int = 0) -> InlineKeyboardMarkup:
        """Create the main menu keyboard"""
        keyboard = [
            [
                InlineKeyboardButton("🎾 Reserve Court", callback_data='menu_reserve'),
                InlineKeyboardButton("📋 Queued Reservations", callback_data='menu_queued')
            ],
            [
                InlineKeyboardButton("👤 Profile", callback_data='menu_profile'),
                InlineKeyboardButton("📊 Performance", callback_data='menu_performance')
            ],
            [
                InlineKeyboardButton("📅 Reservations", callback_data='menu_reservations'),
                InlineKeyboardButton("💡 Help", callback_data='menu_help')
            ],
            [
                InlineKeyboardButton("ℹ️ About", callback_data='menu_about')
            ]
        ]
        
        if is_admin:
            admin_text = "👮 Admin Panel"
            if pending_count > 0:
                admin_text += f" ({pending_count} pending)"
            keyboard.append([InlineKeyboardButton(admin_text, callback_data='menu_admin')])
        
        return InlineKeyboardMarkup(keyboard)
    
    @staticmethod
    def create_court_selection_keyboard(available_courts: List[int]) -> ReplyKeyboardMarkup:
        """Create court selection keyboard"""
        keyboard = []
        
        # Add individual court buttons
        for i in range(0, len(available_courts), 3):
            row = [f"Court {court}" for court in available_courts[i:i+3]]
            keyboard.append(row)
        
        # Add special options
        keyboard.append(["All courts", "Cancel"])
        
        return ReplyKeyboardMarkup(keyboard, one_time_keyboard=True, resize_keyboard=True)
    
    @staticmethod
    def create_queue_court_selection_keyboard(available_courts: List[int]) -> InlineKeyboardMarkup:
        """Create inline court selection keyboard for queue booking flow"""
        keyboard = []
        
        # Add individual court buttons in rows of 3
        for i in range(0, len(available_courts), 3):
            row = []
            for court in available_courts[i:i+3]:
                row.append(InlineKeyboardButton(
                    f"Court {court}", 
                    callback_data=f'queue_court_{court}'
                ))
            keyboard.append(row)
        
        # Add special options
        keyboard.append([
            InlineKeyboardButton("All Courts", callback_data='queue_court_all')
        ])
        
        # Add back button
        keyboard.append([InlineKeyboardButton("🔙 Back", callback_data='back_to_queue_time')])
        
        return InlineKeyboardMarkup(keyboard)
    
    @staticmethod
    def create_yes_no_keyboard() -> ReplyKeyboardMarkup:
        """Create simple yes/no keyboard"""
        return ReplyKeyboardMarkup([["Yes", "No"]], one_time_keyboard=True, resize_keyboard=True)
    
    @staticmethod
    def create_cancel_keyboard() -> ReplyKeyboardMarkup:
        """Create keyboard with only cancel option"""
        return ReplyKeyboardMarkup([["Cancel"]], one_time_keyboard=True, resize_keyboard=True)
    
    @staticmethod
    def create_queue_confirmation_keyboard() -> InlineKeyboardMarkup:
        """Create inline confirmation keyboard for queue booking flow"""
        keyboard = [
            [
                InlineKeyboardButton("✅ Confirm", callback_data='queue_confirm'),
                InlineKeyboardButton("❌ Cancel", callback_data='queue_cancel')
            ],
            [
                InlineKeyboardButton("🔙 Back", callback_data='back_to_queue_courts')
            ]
        ]
        return InlineKeyboardMarkup(keyboard)
    
    @staticmethod
    def create_back_to_menu_keyboard() -> InlineKeyboardMarkup:
        """
        Create a standard 'Back to Menu' inline keyboard
        
        Returns:
            InlineKeyboardMarkup with single 'Back to Menu' button
        """
        keyboard = [[InlineKeyboardButton("🔙 Back to Menu", callback_data='back_to_menu')]]
        return InlineKeyboardMarkup(keyboard)
    
    @staticmethod
    def create_profile_keyboard() -> InlineKeyboardMarkup:
        """
        Create profile view keyboard with Edit and Back buttons
        
        Returns:
            InlineKeyboardMarkup with Edit Profile and Back to Menu buttons
        """
        keyboard = [
            [InlineKeyboardButton("✏️ Edit Profile", callback_data='edit_profile')],
            [InlineKeyboardButton("🔙 Back to Menu", callback_data='back_to_menu')]
        ]
        return InlineKeyboardMarkup(keyboard)
    
    @staticmethod
    def create_edit_profile_keyboard() -> InlineKeyboardMarkup:
        """
        Create edit profile menu keyboard
        
        Returns:
            InlineKeyboardMarkup with edit options for each field
        """
        keyboard = [
            [InlineKeyboardButton("👤 Edit Name", callback_data='edit_name')],
            [InlineKeyboardButton("📱 Edit Phone", callback_data='edit_phone')],
            [InlineKeyboardButton("📧 Edit Email", callback_data='edit_email')],
            [InlineKeyboardButton("🔙 Back to Profile", callback_data='menu_profile')]
        ]
        return InlineKeyboardMarkup(keyboard)
    
    @staticmethod
    def create_cancel_edit_keyboard() -> InlineKeyboardMarkup:
        """
        Create a cancel button for edit operations
        
        Returns:
            InlineKeyboardMarkup with cancel button
        """
        keyboard = [[InlineKeyboardButton("❌ Cancel", callback_data='cancel_edit')]]
        return InlineKeyboardMarkup(keyboard)
    
    @staticmethod
    def create_phone_keypad() -> InlineKeyboardMarkup:
        """
        Create numeric keypad for phone number input
        
        Returns:
            InlineKeyboardMarkup with numeric keypad
        """
        keyboard = [
            [
                InlineKeyboardButton("1", callback_data='phone_digit_1'),
                InlineKeyboardButton("2", callback_data='phone_digit_2'),
                InlineKeyboardButton("3", callback_data='phone_digit_3')
            ],
            [
                InlineKeyboardButton("4", callback_data='phone_digit_4'),
                InlineKeyboardButton("5", callback_data='phone_digit_5'),
                InlineKeyboardButton("6", callback_data='phone_digit_6')
            ],
            [
                InlineKeyboardButton("7", callback_data='phone_digit_7'),
                InlineKeyboardButton("8", callback_data='phone_digit_8'),
                InlineKeyboardButton("9", callback_data='phone_digit_9')
            ],
            [
                InlineKeyboardButton("⬅️ Delete", callback_data='phone_delete'),
                InlineKeyboardButton("0", callback_data='phone_digit_0'),
                InlineKeyboardButton("✅ Done", callback_data='phone_done')
            ],
            [
                InlineKeyboardButton("❌ Cancel", callback_data='cancel_edit')
            ]
        ]
        return InlineKeyboardMarkup(keyboard)
    
    @staticmethod
    def create_name_type_keyboard() -> InlineKeyboardMarkup:
        """
        Create keyboard to choose which name to edit
        
        Returns:
            InlineKeyboardMarkup with name type options
        """
        keyboard = [
            [InlineKeyboardButton("👤 Edit First Name", callback_data='edit_first_name')],
            [InlineKeyboardButton("👥 Edit Last Name", callback_data='edit_last_name')],
            [InlineKeyboardButton("📋 Use Telegram Name", callback_data='name_use_telegram')],
            [InlineKeyboardButton("🔙 Back", callback_data='edit_profile')]
        ]
        return InlineKeyboardMarkup(keyboard)
    
    @staticmethod
    def create_letter_keyboard() -> InlineKeyboardMarkup:
        """
        Create keyboard for letter-by-letter name input
        
        Returns:
            InlineKeyboardMarkup with alphabet
        """
        # Letters in rows - uppercase for names
        letters = [
            ["A", "B", "C", "D", "E", "F"],
            ["G", "H", "I", "J", "K", "L"],
            ["M", "N", "O", "P", "Q", "R"],
            ["S", "T", "U", "V", "W", "X"],
            ["Y", "Z", "-", "'"]
        ]
        
        keyboard = []
        for row in letters:
            kb_row = []
            for letter in row:
                # Special handling for apostrophe
                if letter == "'":
                    callback = 'letter_apostrophe'
                else:
                    callback = f'letter_{letter}'
                kb_row.append(InlineKeyboardButton(letter, callback_data=callback))
            keyboard.append(kb_row)
        
        # Add control buttons
        keyboard.append([
            InlineKeyboardButton("⬅️ Delete", callback_data='letter_delete'),
            InlineKeyboardButton("✅ Done", callback_data='letter_done')
        ])
        keyboard.append([
            InlineKeyboardButton("❌ Cancel", callback_data='cancel_edit')
        ])
        
        return InlineKeyboardMarkup(keyboard)
    
    @staticmethod
    def create_email_confirm_keyboard(email: str) -> InlineKeyboardMarkup:
        """
        Create keyboard to confirm email
        
        Returns:
            InlineKeyboardMarkup with confirm/retry options
        """
        keyboard = [
            [InlineKeyboardButton("✅ Yes, Save This Email", callback_data='email_confirm')],
            [InlineKeyboardButton("🔄 Try Again", callback_data='edit_email')],
            [InlineKeyboardButton("❌ Cancel", callback_data='cancel_edit')]
        ]
        return InlineKeyboardMarkup(keyboard)
    
    @staticmethod
    def create_email_char_keyboard() -> InlineKeyboardMarkup:
        """
        Create keyboard for email character input
        
        Returns:
            InlineKeyboardMarkup with email-safe characters
        """
        # Characters valid in email
        chars = [
            ["a", "b", "c", "d", "e", "f"],
            ["g", "h", "i", "j", "k", "l"],
            ["m", "n", "o", "p", "q", "r"],
            ["s", "t", "u", "v", "w", "x"],
            ["y", "z", "0", "1", "2", "3"],
            ["4", "5", "6", "7", "8", "9"],
            [".", "_", "-", "@"]
        ]
        
        keyboard = []
        for row in chars:
            kb_row = []
            for char in row:
                kb_row.append(InlineKeyboardButton(char, callback_data=f'email_char_{char}'))
            keyboard.append(kb_row)
        
        # Add control buttons
        keyboard.append([
            InlineKeyboardButton("⬅️ Delete", callback_data='email_delete'),
            InlineKeyboardButton("✅ Done", callback_data='email_done')
        ])
        keyboard.append([
            InlineKeyboardButton("❌ Cancel", callback_data='cancel_edit')
        ])
        
        return InlineKeyboardMarkup(keyboard)
    
    @staticmethod
    def create_48h_booking_type_keyboard() -> InlineKeyboardMarkup:
        """
        Create the 48h booking type selection keyboard
        Returns two options: immediate (within 48h) or future (after 48h)
        """
        from lvbot.infrastructure.constants import TEST_MODE_ENABLED
        
        # Build button text based on test mode
        future_text = "📅 Reserve after 48h"
        if TEST_MODE_ENABLED:
            future_text = "🧪 TEST: Queue Booking"
        
        keyboard = [
            [InlineKeyboardButton("🏃‍♂️ Reserve within 48h", callback_data='reserve_48h_immediate')],
            [InlineKeyboardButton(future_text, callback_data='reserve_48h_future')],
            [InlineKeyboardButton("⬅️ Back to Menu", callback_data='back_to_menu')]
        ]
        return InlineKeyboardMarkup(keyboard)
    
    @staticmethod
    def create_year_selection_keyboard() -> InlineKeyboardMarkup:
        """
        Create year selection keyboard for future bookings
        Shows current year and next year
        """
        current_year = datetime.now().year
        keyboard = [
            [InlineKeyboardButton(f"📅 {current_year}", callback_data=f'year_{current_year}')],
            [InlineKeyboardButton(f"📅 {current_year + 1}", callback_data=f'year_{current_year + 1}')],
            [InlineKeyboardButton("🔙 Back", callback_data='back_to_booking_type')]
        ]
        return InlineKeyboardMarkup(keyboard)
    
    @staticmethod
    def create_month_selection_keyboard(year: int) -> InlineKeyboardMarkup:
        """
        Create month selection keyboard for a given year
        Filters out past months for the current year
        Args:
            year: The selected year
        """
        months = [
            "January", "February", "March", "April",
            "May", "June", "July", "August",
            "September", "October", "November", "December"
        ]
        
        current_date = datetime.now()
        current_year = current_date.year
        current_month = current_date.month
        
        keyboard = []
        # Create 3x4 grid of months
        for i in range(0, 12, 3):
            row = []
            for j in range(3):
                if i + j < 12:
                    month_num = i + j + 1
                    month_name = months[i + j]
                    
                    # Skip past months for current year
                    if year == current_year and month_num < current_month:
                        continue
                    
                    row.append(InlineKeyboardButton(
                        f"{month_name[:3]}", 
                        callback_data=f'month_{year}_{month_num:02d}'
                    ))
            if row:  # Only add row if it has buttons
                keyboard.append(row)
        
        keyboard.append([InlineKeyboardButton(f"🔙 Back to Year", callback_data='back_to_year_selection')])
        return InlineKeyboardMarkup(keyboard)
    
    @staticmethod
    def create_day_selection_keyboard(year: int, month: int, flow_type: str = 'immediate') -> InlineKeyboardMarkup:
        """
        Create day selection calendar keyboard for a given year and month
        Filters out past days and days within 48 hours for queue bookings
        Args:
            year: The selected year
            month: The selected month (1-12)
            flow_type: 'immediate' or 'queue_booking' to determine filtering rules
        """
        import calendar
        from datetime import date, datetime, timedelta
        import pytz
        import logging
        
        logger = logging.getLogger('TelegramUI')
        
        # Get the calendar for the month
        cal = calendar.monthcalendar(year, month)
        month_name = calendar.month_name[month]
        
        today = date.today()
        
        # For queue bookings, we need timezone-aware checking
        if flow_type == 'queue_booking':
            from lvbot.infrastructure.constants import COURT_HOURS, get_court_hours
            mexico_tz = pytz.timezone('America/Mexico_City')
            current_time = datetime.now(mexico_tz)
            
            logger.info(f"""CALENDAR DAY FILTERING (Queue Booking)
            Year-Month: {year}-{month:02d}
            Current time (Mexico): {current_time}
            48h threshold: {current_time + timedelta(hours=48)}
            """)
        
        keyboard = []
        
        # Add month/year header
        keyboard.append([InlineKeyboardButton(f"📅 {month_name} {year}", callback_data="noop")])
        
        # Add day names header
        day_names = ["Mon", "Tue", "Wed", "Thu", "Fri", "Sat", "Sun"]
        keyboard.append([InlineKeyboardButton(day[:2], callback_data="noop") for day in day_names])
        
        # Track selectable dates for logging
        selectable_dates = []
        
        # Add calendar days
        for week in cal:
            row = []
            for day in week:
                if day == 0:
                    # Empty day
                    row.append(InlineKeyboardButton(" ", callback_data="noop"))
                else:
                    current_date = date(year, month, day)
                    
                    # Check if date has any bookable time slots
                    if current_date < today:
                        # Past dates - show as disabled
                        row.append(InlineKeyboardButton("❌", callback_data="noop"))
                    elif flow_type == 'queue_booking':
                        # For queue booking, check if ANY time slot on this date is beyond 48 hours
                        has_available_slot = False
                        
                        for hour_str in get_court_hours(current_date):
                            hour, minute = map(int, hour_str.split(':'))
                            slot_datetime_naive = datetime.combine(current_date, datetime.min.time().replace(hour=hour, minute=minute))
                            slot_datetime = mexico_tz.localize(slot_datetime_naive)
                            
                            time_diff = slot_datetime - current_time
                            hours_until_slot = time_diff.total_seconds() / 3600
                            
                            if hours_until_slot > 48:
                                has_available_slot = True
                                break
                        
                        if has_available_slot:
                            # Date has slots beyond 48h - make it selectable
                            selectable_dates.append(current_date.strftime('%Y-%m-%d'))
                            row.append(InlineKeyboardButton(
                                str(day),
                                callback_data=f'future_date_{year}-{month:02d}-{day:02d}'
                            ))
                        else:
                            # All slots within 48h - redirect to immediate booking
                            row.append(InlineKeyboardButton("🚫", callback_data=f"blocked_date_{year}-{month:02d}-{day:02d}"))
                    else:
                        # Immediate booking - allow all non-past dates
                        selectable_dates.append(current_date.strftime('%Y-%m-%d'))
                        row.append(InlineKeyboardButton(
                            str(day),
                            callback_data=f'future_date_{year}-{month:02d}-{day:02d}'
                        ))
            keyboard.append(row)
        
        if flow_type == 'queue_booking':
            logger.info(f"""CALENDAR DISPLAY - Queue Booking
            Selectable dates: {len(selectable_dates)}
            Dates: {selectable_dates}
            """)
        
        keyboard.append([InlineKeyboardButton(f"🔙 Back to Months", callback_data=f'back_to_month_{year}')])
        return InlineKeyboardMarkup(keyboard)
    
    @staticmethod
    def create_date_selection_keyboard(dates: List[tuple]) -> InlineKeyboardMarkup:
        """
        Create date selection keyboard
        Args:
            dates: List of (date_obj, label) tuples
        """
        keyboard = []
        for i in range(0, len(dates), 2):
            row = []
            for date_obj, label in dates[i:i+2]:
                date_str = date_obj.strftime('%Y-%m-%d')
                row.append(InlineKeyboardButton(label, callback_data=f'date_{date_str}'))
            keyboard.append(row)
        
        keyboard.append([InlineKeyboardButton("🔙 Back", callback_data='back_to_reserve')])
        return InlineKeyboardMarkup(keyboard)
    
    @staticmethod
    def create_time_selection_keyboard(available_times: List[str], selected_date: str, 
                                     flow_type: str = 'availability') -> InlineKeyboardMarkup:
        """Create time selection keyboard with flow-specific callbacks"""
        from datetime import datetime, date
        
        keyboard = []
        
        # Parse selected date for comparison
        try:
            selected_date_obj = datetime.strptime(selected_date, '%Y-%m-%d').date()
            is_today = selected_date_obj == date.today()
            current_time = datetime.now()
        except:
            is_today = False
            current_time = None
        
        # Group times in rows of 3
        filtered_times = []
        for time_str in available_times:
            # If booking for today, filter out past times
            if is_today and current_time:
                try:
                    hour, minute = map(int, time_str.split(':'))
                    if hour < current_time.hour or (hour == current_time.hour and minute <= current_time.minute):
                        continue  # Skip past times
                except:
                    pass
            filtered_times.append(time_str)
        
        for i in range(0, len(filtered_times), 3):
            row = []
            for time in filtered_times[i:i+3]:
                button_text = time
                # Use different callback prefix based on flow type
                callback_prefix = 'queue_time' if flow_type == 'queue_booking' else 'time'
                row.append(InlineKeyboardButton(
                    button_text, 
                    callback_data=f'{callback_prefix}_{selected_date}_{time}'
                ))
            keyboard.append(row)
        
        # Use appropriate back button based on flow type
        back_callback = 'back_to_queue_dates' if flow_type == 'queue_booking' else 'back_to_dates'
        keyboard.append([InlineKeyboardButton("🔙 Back", callback_data=back_callback)])
        return InlineKeyboardMarkup(keyboard)
    
    @staticmethod
    def create_time_selection_keyboard_simple(date=None) -> InlineKeyboardMarkup:
        """Create time selection keyboard for modify flow (no parameters)"""
        # Use centralized court hours from constants
        available_times = get_court_hours(date)
        
        keyboard = []
        # Group times in rows of 3
        for i in range(0, len(available_times), 3):
            row = []
            for time in available_times[i:i+3]:
                row.append(InlineKeyboardButton(
                    time, 
                    callback_data=f'queue_time_modify_{time}'
                ))
            keyboard.append(row)
        
        keyboard.append([InlineKeyboardButton("🔙 Back", callback_data='back_to_modify')])
        return InlineKeyboardMarkup(keyboard)
    
    @staticmethod
    def create_court_selection_keyboard() -> InlineKeyboardMarkup:
        """Create court selection keyboard for modify flow"""
        available_courts = [1, 2, 3]
        keyboard = []
        
        # Add individual court buttons in rows of 3
        for i in range(0, len(available_courts), 3):
            row = []
            for court in available_courts[i:i+3]:
                row.append(InlineKeyboardButton(
                    f"Court {court}", 
                    callback_data=f'queue_court_{court}'
                ))
            keyboard.append(row)
        
        # Add all courts option
        keyboard.append([
            InlineKeyboardButton("All Courts", callback_data='queue_court_all')
        ])
        
        # Add back button
        keyboard.append([InlineKeyboardButton("🔙 Back", callback_data='back_to_modify')])
        
        return InlineKeyboardMarkup(keyboard)
    
    @staticmethod
    def format_reservation_confirmation(reservation_details: Dict[str, Any]) -> str:
        """Format reservation confirmation message"""
        courts_text = ', '.join([f"Court {c}" for c in reservation_details['courts']])
        
        message = f"""✅ **Reservation Confirmed!**

📅 Date: {reservation_details['date']}
⏰ Time: {reservation_details['time']}
🎾 Courts: {courts_text}
👤 Name: {reservation_details.get('name', 'N/A')}
📱 Phone: {reservation_details.get('phone', 'N/A')}

Priority: {'High' if reservation_details.get('priority', 1) == 0 else 'Normal'}"""
        
        if 'confirmation_code' in reservation_details:
            message += f"\n🔑 Confirmation: {reservation_details['confirmation_code']}"
            
        return message
    
    @staticmethod
    def format_user_tier_badge(tier_name: str) -> str:
        """Format user tier into an emoji badge"""
        tier_badges = {
            'ADMIN': '👑',
            'VIP': '⭐',
            'REGULAR': '👤'
        }
        return tier_badges.get(tier_name, '👤')
    
    @staticmethod
    def format_reservations_list(reservations: List[Dict[str, Any]]) -> str:
        """
        Format a list of reservations into a user-friendly message
        
        Args:
            reservations: List of reservation dictionaries from ReservationQueue
            
        Returns:
            str: Formatted message string for display
        """
        if not reservations:
            return ("📋 **My Reservations**\n\n"
                   "You have no active reservations at the moment.\n\n"
                   "Use the 'Reserve Court' option to book a court!")
        
        message = "📋 **My Reservations**\n\n"
        
        # Group reservations by status
        pending = [r for r in reservations if r.get('status') == 'pending']
        scheduled = [r for r in reservations if r.get('status') == 'scheduled']
        confirmed = [r for r in reservations if r.get('status') == 'confirmed']
        waitlisted = [r for r in reservations if r.get('status') == 'waitlisted']
        failed = [r for r in reservations if r.get('status') == 'failed']
        
        # Show pending reservations
        if pending:
            message += "⏳ **Pending Reservations:**\n"
            for res in pending:
                courts_text = ', '.join([f"Court {c}" for c in res.get('courts', [])])
                message += (f"• {res.get('date')} at {res.get('time')}\n"
                           f"  🎾 {courts_text}\n"
                           f"  🆔 ID: {res.get('id', '')[:8]}...\n\n")
        
        # Show scheduled reservations
        if scheduled:
            message += "📅 **Scheduled for Booking:**\n"
            for res in scheduled:
                courts_text = ', '.join([f"Court {c}" for c in res.get('courts', [])])
                message += (f"• {res.get('date')} at {res.get('time')}\n"
                           f"  🎾 {courts_text}\n"
                           f"  🆔 ID: {res.get('id', '')[:8]}...\n\n")
        
        # Show confirmed reservations
        if confirmed:
            message += "✅ **Confirmed Reservations:**\n"
            for res in confirmed:
                courts_text = ', '.join([f"Court {c}" for c in res.get('courts', [])])
                message += (f"• {res.get('date')} at {res.get('time')}\n"
                           f"  🎾 {courts_text}\n"
                           f"  🔑 Code: {res.get('confirmation_code', 'N/A')}\n"
                           f"  🆔 ID: {res.get('id', '')[:8]}...\n\n")
        
        # Show waitlisted reservations
        if waitlisted:
            message += "📋 **Waitlisted Reservations:**\n"
            for res in waitlisted:
                courts_text = ', '.join([f"Court {c}" for c in res.get('courts', [])])
                position = res.get('waitlist_position', 'N/A')
                message += (f"• {res.get('date')} at {res.get('time')}\n"
                           f"  🎾 {courts_text}\n"
                           f"  📊 Position: #{position}\n"
                           f"  🆔 ID: {res.get('id', '')[:8]}...\n\n")
        
        # Show failed reservations (if any recent ones)
        if failed:
            message += "❌ **Recent Failed Attempts:**\n"
            for res in failed[:3]:  # Show only last 3 failed
                courts_text = ', '.join([f"Court {c}" for c in res.get('courts', [])])
                message += (f"• {res.get('date')} at {res.get('time')}\n"
                           f"  🎾 {courts_text}\n"
                           f"  📝 Reason: {res.get('failure_reason', 'Unknown')}\n\n")
        
        message += f"Total: {len(reservations)} reservation(s)"
        return message
    
    @staticmethod
    def format_error_message(error_type: str, details: Optional[str] = None) -> str:
        """Format standardized error messages"""
        error_messages = {
            'unauthorized': "🔐 You are not authorized to use this bot.\nPlease send /start to request access.",
            'invalid_date': "❌ Invalid date selected. Please choose a valid date.",
            'invalid_time': "❌ Invalid time selected. Please choose from available times.",
            'invalid_court': "❌ Invalid court selection. Please choose valid courts.",
            'no_availability': "😔 No courts available at this time. Please try another time slot.",
            'booking_failed': "❌ Booking failed. Please try again later.",
            'profile_incomplete': "❌ Please complete your profile first using /profile command.",
            'outside_window': "⏰ This time slot is outside the 48-hour booking window.",
            'already_booked': "🚫 You already have a reservation at this time.",
            'system_error': "❌ System error occurred. Please contact admin."
        }
        
        message = error_messages.get(error_type, "❌ An error occurred.")
        if details:
            message += f"\n\nDetails: {details}"
            
        return message
    
    @staticmethod
    def format_availability_message(available_times: Dict[int, List[str]], 
                                  date: datetime, 
                                  show_summary: bool = True) -> str:
        """Format court availability message"""
        date_str = date.strftime('%A, %B %d')
        message = f"🎾 **Court Availability**\n📅 {date_str}\n\n"
        
        if not available_times:
            message += "No courts available for this date."
            return message
        
        # Group by time
        times_by_slot = {}
        for court, times in available_times.items():
            for time in times:
                if time not in times_by_slot:
                    times_by_slot[time] = []
                times_by_slot[time].append(court)
        
        # Sort times
        sorted_times = sorted(times_by_slot.keys())
        
        if show_summary:
            message += f"⏰ Available slots: {len(sorted_times)}\n"
            message += f"🎾 Courts with availability: {len(available_times)}\n\n"
        
        # Format times
        for time in sorted_times:
            courts = sorted(times_by_slot[time])
            courts_str = ', '.join([f"C{c}" for c in courts])
            message += f"• {time} - Courts: {courts_str}\n"
        
        return message
    
    @staticmethod
    def format_user_profile_message(user_data: Dict[str, Any], is_hardcoded: bool = False) -> str:
        """Format user profile display"""
        status_emoji = "✅" if user_data.get('is_active', True) else "🔴"
        
        # Format phone with (+502) prefix if set
        phone = user_data.get('phone', 'Not set')
        if phone and phone != 'Not set':
            phone = f"(+502) {phone}"
        
        message = f"""{status_emoji} **User Profile**

👤 Name: {user_data.get('first_name', '')} {user_data.get('last_name', '')}
📱 Phone: {phone}
📧 Email: {user_data.get('email', 'Not set')}
🎾 Court Preference: {', '.join([f"Court {c}" for c in user_data.get('court_preference', [])])}
📊 Total Reservations: {user_data.get('total_reservations', 0)}"""
        
        if user_data.get('telegram_username'):
            message += f"\n💬 Telegram: @{user_data['telegram_username']}"
            
        if is_hardcoded:
            message += "\n\n⚡ *Premium User (Hardcoded)*"
            
        if user_data.get('is_vip'):
            message += "\n\n⭐ *VIP User* (Priority booking)"
            
        if user_data.get('is_admin'):
            message += "\n\n👮 *Administrator*"
            
        return message
    
    @staticmethod
    def format_queue_status_message(queue_items: List[Dict[str, Any]], timezone_str: str) -> str:
        """Format queue status message"""
        if not queue_items:
            return "📋 No queued reservations."
        
        message = f"📋 **Queued Reservations ({len(queue_items)})**\n\n"
        
        for idx, item in enumerate(queue_items, 1):
            courts = ', '.join([f"C{c}" for c in item['courts']])
            message += f"{idx}. {item['date']} at {item['time']}\n"
            message += f"   Courts: {courts}\n"
            message += f"   Status: {item['status']}\n"
            
            if item.get('attempts', 0) > 0:
                message += f"   Attempts: {item['attempts']}\n"
                
            message += "\n"
        
        return message
    
    @staticmethod
    def create_pagination_keyboard(current_page: int, total_pages: int, 
                                 callback_prefix: str) -> List[InlineKeyboardButton]:
        """Create pagination buttons for multi-page displays"""
        buttons = []
        
        if current_page > 0:
            buttons.append(InlineKeyboardButton("⬅️ Previous", 
                                              callback_data=f"{callback_prefix}_page_{current_page-1}"))
        
        buttons.append(InlineKeyboardButton(f"{current_page+1}/{total_pages}", 
                                           callback_data=f"{callback_prefix}_current"))
        
        if current_page < total_pages - 1:
            buttons.append(InlineKeyboardButton("➡️ Next", 
                                              callback_data=f"{callback_prefix}_page_{current_page+1}"))
        
        return buttons
    
    @staticmethod
    def format_loading_message(action: str = "Processing") -> str:
        """Format a loading message"""
        return f"⏳ {action}..."
    
    @staticmethod
    def create_admin_menu_keyboard(pending_count: int = 0) -> InlineKeyboardMarkup:
        """Create admin menu keyboard"""
        keyboard = [
            [
                InlineKeyboardButton(f"🆕 Pending ({pending_count})", callback_data='admin_pending'),
                InlineKeyboardButton("👥 All Users", callback_data='admin_users')
            ],
            [
                InlineKeyboardButton("📊 Stats", callback_data='admin_stats'),
                InlineKeyboardButton("⚙️ Settings", callback_data='admin_settings')
            ],
            [
                InlineKeyboardButton("🔍 Search User", callback_data='admin_search'),
                InlineKeyboardButton("📢 Broadcast", callback_data='admin_broadcast')
            ],
            [InlineKeyboardButton("🔙 Back to Menu", callback_data='back_to_menu')]
        ]
        return InlineKeyboardMarkup(keyboard)
    
    @staticmethod
    def create_court_availability_keyboard(available_times: Dict[int, List[str]], 
                                         selected_date: str,
                                         layout_type: str = "vertical",
                                         available_dates: Optional[List[str]] = None) -> InlineKeyboardMarkup:
        """
        Create interactive court availability keyboard for immediate booking
        
        Args:
            available_times: Dict mapping court number to list of available time strings
            selected_date: Selected date string in YYYY-MM-DD format
            layout_type: Layout style - "vertical" (current) or "matrix" (new grid format)
            available_dates: Optional list of available dates for day cycling (matrix layout only)
            
        Returns:
            InlineKeyboardMarkup with time buttons grouped by court (vertical) or time slots (matrix)
        """
        if layout_type == "matrix":
            # Matrix layout: times as rows, courts as columns with day cycling
            return TelegramUI._create_matrix_layout_keyboard(available_times, selected_date, available_dates)
        else:
            # Default vertical layout (current implementation)
            return TelegramUI._create_vertical_layout_keyboard(available_times, selected_date)
    
    @staticmethod
    def _create_vertical_layout_keyboard(available_times: Dict[int, List[str]], 
                                       selected_date: str) -> InlineKeyboardMarkup:
        """
        Create vertical layout keyboard (current implementation)
        
        Args:
            available_times: Dict mapping court number to list of available time strings
            selected_date: Selected date string in YYYY-MM-DD format
            
        Returns:
            InlineKeyboardMarkup with vertical court layout
        """
        keyboard = []
        
        # Sort courts
        sorted_courts = sorted(available_times.keys())
        
        # Create a grid of times by court
        max_times_per_row = 3
        
        for court_num in sorted_courts:
            times = available_times[court_num]
            if not times:
                continue
                
            # Add court header row
            keyboard.append([InlineKeyboardButton(
                f"🎾 Court {court_num}",
                callback_data=f"court_header_{court_num}"
            )])
            
            # Add times in rows
            for i in range(0, len(times), max_times_per_row):
                row = []
                for time in times[i:i+max_times_per_row]:
                    # Extract just the start time if it's a range
                    display_time = time.split(' - ')[0] if ' - ' in time else time
                    row.append(InlineKeyboardButton(
                        display_time,
                        callback_data=f"book_now_{selected_date}_{court_num}_{display_time}"
                    ))
                keyboard.append(row)
        
        # Add back button
        keyboard.append([InlineKeyboardButton("🔙 Back to Menu", callback_data='back_to_menu')])
        
        return InlineKeyboardMarkup(keyboard)
    
    @staticmethod
    def _create_matrix_layout_keyboard(available_times: Dict[int, List[str]], 
                                     selected_date: str,
                                     available_dates: Optional[List[str]] = None) -> InlineKeyboardMarkup:
        """
        Create matrix layout keyboard (new grid format)
        Times as rows, courts as columns. Only shows time rows with at least 1 available court.
        
        Args:
            available_times: Dict mapping court number to list of available time strings
            selected_date: Selected date string in YYYY-MM-DD format
            available_dates: Optional list of available dates for day cycling
            
        Returns:
            InlineKeyboardMarkup with matrix layout
        """
        import logging
        logger = logging.getLogger(__name__)
        
        # LOG: What data we received
        logger.info(f"🎯 TELEGRAM DISPLAY - Creating matrix for date: {selected_date}")
        logger.info(f"📊 Available times by court: {available_times}")
        
        keyboard = []
        
        # Build time matrix and filter empty rows
        time_matrix = TelegramUI._build_time_matrix(available_times)
        filtered_matrix = TelegramUI._filter_empty_time_rows(time_matrix)
        
        # LOG: What matrix was built
        logger.info(f"🔢 Time matrix built: {time_matrix}")
        logger.info(f"📋 Filtered matrix (shown to user): {filtered_matrix}")
        
        if not filtered_matrix:
            # No availability - just show back button
            keyboard.append([InlineKeyboardButton("🔙 Back to Menu", callback_data='back_to_menu')])
            return InlineKeyboardMarkup(keyboard)
        
        # Get ALL courts (1, 2, 3) regardless of availability  
        all_courts = [1, 2, 3]
        
        # Add day cycling button if multiple dates available
        if available_dates and len(available_dates) > 1:
            day_label = TelegramUI._get_day_label_for_date(selected_date)
            next_date = TelegramUI._get_next_day(selected_date, available_dates)
            keyboard.append([InlineKeyboardButton(
                f"📅 {day_label} (tap to cycle)",
                callback_data=f"cycle_day_{next_date}"
            )])
        
        # Add court header row (non-functional buttons)
        court_header_row = []
        for court_num in all_courts:
            court_header_row.append(InlineKeyboardButton(
                f"🎾 Court {court_num}",
                callback_data=f"court_header_{court_num}"
            ))
        keyboard.append(court_header_row)
        
        # LOG: Show what will be displayed to user in matrix format
        logger.info(f"🎾 MATRIX DISPLAY for {selected_date}:")
        logger.info(f"📋 Headers: {[f'Court {c}' for c in all_courts]}")
        
        for time_slot in sorted(filtered_matrix.keys()):
            court_status = []
            for court_num in all_courts:
                is_available = filtered_matrix[time_slot].get(court_num, False)
                status = "✅" if is_available else "❌"
                court_status.append(f"C{court_num}:{status}")
            logger.info(f"⏰ {time_slot} | {' '.join(court_status)}")
        
        # Add matrix rows (time slots)
        keyboard.extend(TelegramUI._create_matrix_keyboard_rows(filtered_matrix, selected_date, all_courts))
        
        # Add back button
        keyboard.append([InlineKeyboardButton("🔙 Back to Menu", callback_data='back_to_menu')])
        
        return InlineKeyboardMarkup(keyboard)
    
    @staticmethod
    def _build_time_matrix(available_times: Dict[int, List[str]]) -> Dict[str, Dict[int, bool]]:
        """
        Build time matrix mapping time slots to court availability
        
        Args:
            available_times: Dict mapping court number to list of available time strings
            
        Returns:
            Dict mapping time slot to dict of court availability (court_num -> bool)
        """
        time_matrix = {}
        
        # Collect all unique times
        all_times = set()
        for times in available_times.values():
            for time in times:
                # Extract just the start time if it's a range
                display_time = time.split(' - ')[0] if ' - ' in time else time
                all_times.add(display_time)
        
        # Build matrix for each time slot - ALWAYS include courts 1, 2, 3
        all_courts = [1, 2, 3]  # Always show all 3 courts even if they have no availability
        for time_slot in all_times:
            time_matrix[time_slot] = {}
            for court_num in all_courts:
                # Check if this court has this time slot available
                court_times = available_times.get(court_num, [])  # Empty list if court not in available_times
                is_available = any(
                    time_slot == (time.split(' - ')[0] if ' - ' in time else time)
                    for time in court_times
                )
                time_matrix[time_slot][court_num] = is_available
        
        return time_matrix
    
    @staticmethod
    def _filter_empty_time_rows(time_matrix: Dict[str, Dict[int, bool]]) -> Dict[str, Dict[int, bool]]:
        """
        Filter out time rows where no courts are available
        
        Args:
            time_matrix: Time matrix from _build_time_matrix
            
        Returns:
            Filtered time matrix with only rows that have at least 1 available court
        """
        filtered_matrix = {}
        
        for time_slot, court_availability in time_matrix.items():
            # Check if any court is available for this time slot
            if any(court_availability.values()):
                filtered_matrix[time_slot] = court_availability
        
        return filtered_matrix
    
    @staticmethod
    def _create_matrix_keyboard_rows(time_matrix: Dict[str, Dict[int, bool]], 
                                   selected_date: str, 
                                   all_courts: List[int]) -> List[List]:
        """
        Create keyboard rows from filtered time matrix
        
        Args:
            time_matrix: Filtered time matrix with only available time slots
            selected_date: Selected date string in YYYY-MM-DD format
            all_courts: List of all court numbers in sorted order
            
        Returns:
            List of keyboard rows for the matrix layout
        """
        keyboard_rows = []
        
        # Sort time slots for consistent display
        sorted_times = sorted(time_matrix.keys(), key=lambda t: (
            int(t.split(':')[0]),  # Hour
            int(t.split(':')[1])   # Minute
        ))
        
        for time_slot in sorted_times:
            court_availability = time_matrix[time_slot]
            time_row = []
            
            for court_num in all_courts:
                if court_availability.get(court_num, False):
                    # Court available - clickable button
                    time_row.append(InlineKeyboardButton(
                        time_slot,
                        callback_data=f"book_now_{selected_date}_{court_num}_{time_slot}"
                    ))
                else:
                    # Court not available - show dash
                    time_row.append(InlineKeyboardButton(
                        "-",
                        callback_data=f"unavailable_{court_num}_{time_slot}"
                    ))
            
            keyboard_rows.append(time_row)
        
        return keyboard_rows
    
    @staticmethod
    def _get_day_label_for_date(date_str: str) -> str:
        """
        Get day label for a date string (Today, Tomorrow, or day name)
        
        Args:
            date_str: Date string in YYYY-MM-DD format
            
        Returns:
            Day label string
        """
        from datetime import datetime, timedelta
        
        try:
            target_date = datetime.strptime(date_str, '%Y-%m-%d').date()
            today = datetime.now().date()
            
            if target_date == today:
                return "Today"
            elif target_date == today + timedelta(days=1):
                return "Tomorrow"
            else:
                return target_date.strftime('%A')  # Day name (Monday, Tuesday, etc.)
        except ValueError:
            return "Selected Day"
    
    @staticmethod
    def _get_next_day(current_date: str, available_dates: List[str]) -> str:
        """
        Get next available date for intelligent day cycling
        
        Handles edge cases:
        - Single day: returns same day
        - End of list: cycles back to first day
        - Date not in list: returns first available date
        
        Args:
            current_date: Current date string in YYYY-MM-DD format
            available_dates: List of available date strings
            
        Returns:
            Next available date string
        """
        if not available_dates:
            return current_date
        
        if len(available_dates) == 1:
            # Only one day available - no cycling needed
            return available_dates[0]
        
        try:
            current_index = available_dates.index(current_date)
            # Get next index with wrap-around
            next_index = (current_index + 1) % len(available_dates)
            return available_dates[next_index]
        except ValueError:
            # Current date not in available dates - return first available
            return available_dates[0]
    
    @staticmethod
    def format_interactive_availability_message(available_times: Dict[int, List[str]], 
                                              date: datetime,
                                              total_slots: int = None,
                                              layout_type: str = "vertical") -> str:
        """
        Format court availability message for interactive booking UI
        
        Args:
            available_times: Dict mapping court number to list of available time strings
            date: The date being displayed
            total_slots: Optional total number of available slots
            layout_type: Layout style - "vertical" or "matrix" affects message format
            
        Returns:
            Formatted message string matching the UI design
        """
        date_str = date.strftime('%A, %B %d')
        
        # Calculate total slots if not provided
        if total_slots is None:
            total_slots = sum(len(times) for times in available_times.values())
        
        # Determine day label (Today, Tomorrow, or day name)
        from datetime import timedelta
        today = datetime.now().date()
        
        # Handle both datetime and date objects
        if hasattr(date, 'date'):
            # It's a datetime object
            date_obj = date.date()
        else:
            # It's already a date object
            date_obj = date
            
        if date_obj == today:
            day_label = "Today"
        elif date_obj == today + timedelta(days=1):
            day_label = "Tomorrow"
        else:
            day_label = date_obj.strftime('%A')
        
        if layout_type == "matrix":
            # Matrix layout message format
            message = (
                f"🎾 **Online Court Availability**\n\n"
                f"Select a time to reserve:\n\n"
                f"📅 **{day_label} - {total_slots} slots available**"
            )
        else:
            # Vertical layout message format (current)
            message = (
                f"🎾 **Online Court Availability**\n\n"
                f"Select a time to reserve:\n\n"
                f"📅 **{day_label} - {total_slots} slots available**"
            )
        
        return message