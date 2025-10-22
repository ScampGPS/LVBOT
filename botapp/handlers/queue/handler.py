"""Queue booking and reservation management callbacks."""

from __future__ import annotations
from tracking import t

import os
from datetime import date, datetime, timedelta
from typing import Any, Dict, List, Sequence

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
from botapp.messages.message_handlers import MessageHandlers
from automation.availability import DateTimeHelpers
from infrastructure.settings import get_test_mode
from infrastructure.constants import get_court_hours

PRODUCTION_MODE = os.getenv("PRODUCTION_MODE", "false").lower() == "true"


class QueueHandler:
    QUEUE_BOOKING_WINDOW_DAYS = 7
    AVAILABLE_COURTS = [1, 2, 3]

    """Handles queue booking flows and reservation management."""

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

    async def _edit_callback_message(self, query, text: str, **kwargs) -> None:
        await MessageHandlers.edit_callback_message(
            query,
            text,
            logger=self.logger,
            **kwargs,
        )

    def _format_court_preferences(
        self,
        selected_courts: Sequence[int],
        all_courts: Sequence[int] | None = None,
    ) -> str:
        """Create a readable label for court selections."""

        courts = list(selected_courts)
        if not courts:
            return "No Courts Selected"

        reference = set(all_courts or self.AVAILABLE_COURTS)
        if set(courts) == reference:
            return "All Courts"

        return ", ".join(f"Court {court}" for court in sorted(courts))

    async def handle_queue_booking_menu(self, update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
        """
        Handle Queue Booking menu option

        Shows date selection for queued reservation booking

        Args:
            update: The telegram update containing the callback query
            context: The callback context

        Returns:
            None
        """
        t('botapp.handlers.callback_handlers.CallbackHandler._handle_queue_booking_menu')
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

        config = get_test_mode()
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

            has_available_slots = False
            first_available_slot = None
            slots_checked = 0

            if config.enabled and config.allow_within_48h:
                has_available_slots = True
                slots_checked = len(get_court_hours(check_date))
                first_available_slot = "Test mode"
            else:
                for hour_str in get_court_hours(check_date):
                    hour, minute = map(int, hour_str.split(':'))
                    slot_datetime_naive = datetime.combine(
                        check_date,
                        datetime.min.time().replace(hour=hour, minute=minute),
                    )
                    slot_datetime = mexico_tz.localize(slot_datetime_naive)

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
            await self._edit_callback_message(query,
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

        await self._edit_callback_message(query,
            "⏰ Queue Booking\n\n"
            "📅 Select a date for your queued reservation:\n\n"
            "ℹ️ Note: Only time slots more than 48 hours away will be shown.",
            reply_markup=keyboard
        )

    async def handle_my_reservations_menu(self, update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
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
        t('botapp.handlers.callback_handlers.CallbackHandler._handle_my_reservations_menu')
        query = update.callback_query
        user_id = query.from_user.id

        try:
            # Retrieve user's reservations from the queue
            user_reservations = self.deps.reservation_queue.get_user_reservations(user_id)

            if not user_reservations:
                await self._edit_callback_message(query,
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

            await self._edit_callback_message(query,
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

    async def handle_queue_booking_date_selection(self, update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
        """
        Handle date selection for queue booking flow

        Processes the selected date and prompts user for time selection

        Args:
            update: The telegram update containing the callback query
            context: The callback context

        Returns:
            None
        """
        t('botapp.handlers.callback_handlers.CallbackHandler._handle_queue_booking_date_selection')
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
            await self._edit_callback_message(query,
                f"❌ Invalid date format received: {date_str}. Please try again."
            )
            return

        # Store selected date in user context
        context.user_data['queue_booking_date'] = selected_date

        config = get_test_mode()

        # Use specialized path when test mode allows within 48 hours
        if config.enabled and config.allow_within_48h:
            await self._show_queue_time_selection(update, context, selected_date)
            return

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
            await self._edit_callback_message(query,
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
        await self._edit_callback_message(query,
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
        t('botapp.handlers.callback_handlers.CallbackHandler._show_queue_time_selection')
        query = update.callback_query

        # Use centralized court hours from constants
        all_court_hours = get_court_hours(selected_date)

        config = get_test_mode()

        if config.enabled and config.allow_within_48h:
            available_hours = list(all_court_hours)
            availability_note = f"ℹ️ {len(available_hours)} time slots available (test mode)"
            self.logger.info(
                "🧪 TEST MODE: Allowing all %s time slots for %s", len(available_hours), selected_date
            )
        else:
            import pytz

            mexico_tz = pytz.timezone('America/Mexico_City')
            current_time = datetime.now(mexico_tz)
            available_hours = []

            for hour_str in all_court_hours:
                hour, minute = map(int, hour_str.split(':'))
                slot_datetime_naive = datetime.combine(
                    selected_date,
                    datetime.min.time().replace(hour=hour, minute=minute),
                )
                slot_datetime = mexico_tz.localize(slot_datetime_naive)
                time_diff = slot_datetime - current_time
                hours_until_slot = time_diff.total_seconds() / 3600

                if hours_until_slot > 48:
                    available_hours.append(hour_str)

            availability_note = (
                f"ℹ️ {len(available_hours)} time slots available (48+ hours away)"
            )

        # Check if we have any available time slots
        if not available_hours:
            await self._edit_callback_message(query,
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
        await self._edit_callback_message(query,
            f"⏰ **Queue Booking**\n\n"
            f"📅 Selected Date: {selected_date.strftime('%A, %B %d, %Y')}\n\n"
            f"⏱️ Select a time for your queued reservation:\n"
            f"{availability_note}",
            parse_mode='Markdown',
            reply_markup=reply_markup
        )

    async def handle_queue_booking_time_selection(self, update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
        """
        Handle time selection for queue booking flow

        Processes the selected time and prompts user for court selection

        Args:
            update: The telegram update containing the callback query
            context: The callback context

        Returns:
            None
        """
        t('botapp.handlers.callback_handlers.CallbackHandler._handle_queue_booking_time_selection')
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
            await self._edit_callback_message(query,
                f"❌ Invalid time selection format received: {callback_data}. Please try again."
            )
            return

        # Check if this is a modification flow
        modifying_id = context.user_data.get('modifying_reservation_id')
        modifying_option = context.user_data.get('modifying_option')

        if modifying_id and modifying_option == 'time':
            # Update the reservation time
            reservation = self.deps.reservation_queue.get_reservation(modifying_id)
            if reservation:
                reservation['target_time'] = selected_time
                self.deps.reservation_queue.update_reservation(modifying_id, reservation)

                # Clear modification context
                context.user_data.pop('modifying_reservation_id', None)
                context.user_data.pop('modifying_option', None)

                # Show success message
                await self._edit_callback_message(query,
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
            await self._edit_callback_message(query,
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
        await self._edit_callback_message(query,
            f"⏰ **Queue Booking**\n\n"
            f"📅 Date: {selected_date.strftime('%A, %B %d, %Y')}\n"
            f"⏱️ Time: {selected_time}\n\n"
            f"🎾 Select your preferred court(s) for the reservation:",
            parse_mode='Markdown',
            reply_markup=reply_markup
        )

    async def handle_queue_booking_court_selection(self, update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
        """
        Handle court selection for queue booking flow

        Processes the selected court(s) and presents final confirmation

        Args:
            update: The telegram update containing the callback query
            context: The callback context

        Returns:
            None
        """
        t('botapp.handlers.callback_handlers.CallbackHandler._handle_queue_booking_court_selection')
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
                await self._edit_callback_message(query,
                    f"❌ Invalid court selection received: {callback_data}. Please try again."
                )
                return
        else:
            self.logger.error(f"Unrecognized queue court callback: {callback_data}")
            await self._edit_callback_message(query,
                "❌ Invalid court selection. Please try again."
            )
            return

        # Check if this is a modification flow
        modifying_id = context.user_data.get('modifying_reservation_id')
        modifying_option = context.user_data.get('modifying_option')

        if modifying_id and modifying_option == 'courts':
            # Update the reservation courts
            reservation = self.deps.reservation_queue.get_reservation(modifying_id)
            if reservation:
                reservation['court_preferences'] = selected_courts
                self.deps.reservation_queue.update_reservation(modifying_id, reservation)

                # Clear modification context
                context.user_data.pop('modifying_reservation_id', None)
                context.user_data.pop('modifying_option', None)

                # Format courts text
                courts_text = self._format_court_preferences(
                    selected_courts,
                    self.AVAILABLE_COURTS,
                )

                # Show success message
                await self._edit_callback_message(query,
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
        cleaned_courts = sorted(set(selected_courts))
        context.user_data['queue_booking_courts'] = cleaned_courts

        # Retrieve stored booking details
        selected_date = context.user_data.get('queue_booking_date')
        selected_time = context.user_data.get('queue_booking_time')

        if not selected_date or not selected_time:
            self.logger.error("Missing booking details in user context")
            await self._edit_callback_message(query,
                "❌ Session expired. Please start the booking process again."
            )
            return

        user_id = query.from_user.id
        user_profile = self.deps.user_manager.get_user(user_id)

        required_fields = ('first_name', 'last_name', 'email', 'phone')
        missing_fields: List[str] = []
        if not user_profile:
            missing_fields = list(required_fields)
        else:
            missing_fields = [field for field in required_fields if not user_profile.get(field)]

        if missing_fields:
            self.logger.warning(
                "User %s missing required fields for queued booking: %s",
                user_id,
                ', '.join(missing_fields),
            )
            reply_markup = TelegramUI.create_profile_keyboard()
            await self._edit_callback_message(query,
                "❌ **Profile Incomplete**\n\n"
                "Please update your profile before adding a reservation to the queue.\n"
                f"Missing fields: {', '.join(missing_fields)}",
                parse_mode='Markdown',
                reply_markup=reply_markup,
            )
            return

        # Store complete reservation details for final confirmation
        # Aligned with FEATURE_SPECS.md Queue Entry Structure
        context.user_data['queue_booking_summary'] = {
            'user_id': user_id,
            'first_name': user_profile.get('first_name'),
            'last_name': user_profile.get('last_name'),
            'email': user_profile.get('email'),
            'phone': user_profile.get('phone'),
            'tier': user_profile.get('tier_name') or user_profile.get('tier'),
            'target_date': selected_date.strftime('%Y-%m-%d'),
            'target_time': selected_time,
            'court_preferences': cleaned_courts,
            'created_at': datetime.now().isoformat(),
        }

        # Create confirmation keyboard
        reply_markup = TelegramUI.create_queue_confirmation_keyboard()

        # Show final confirmation
        courts_text = self._format_court_preferences(
            cleaned_courts,
            self.AVAILABLE_COURTS,
        )
        await self._edit_callback_message(query,
            f"⏰ **Queue Booking Confirmation**\n\n"
            f"📅 Date: {selected_date.strftime('%A, %B %d, %Y')}\n"
            f"⏱️ Time: {selected_time}\n"
            f"🎾 Courts: {courts_text}\n\n"
            f"🤖 This reservation will be queued and automatically booked when the booking window opens.\n\n"
            f"**Confirm to add this reservation to your queue?**",
            parse_mode='Markdown',
            reply_markup=reply_markup
        )

    async def handle_queue_booking_confirm(self, update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
        """
        Handle confirmation of queue booking reservation

        Adds the reservation to the queue and provides success feedback

        Args:
            update: The telegram update containing the callback query
            context: The callback context

        Returns:
            None
        """
        t('botapp.handlers.callback_handlers.CallbackHandler._handle_queue_booking_confirm')
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
            await self._edit_callback_message(query,
                "❌ Session expired. Please start the booking process again."
            )
            return

        config = get_test_mode()

        try:
            # Add reservation to the queue
            reservation_id = self.deps.reservation_queue.add_reservation(booking_summary)

            # Format court list for display
            courts_text = self._format_court_preferences(
                booking_summary['court_preferences'],
                self.AVAILABLE_COURTS,
            )

            # Clear queue booking state from context
            self.clear_queue_booking_state(context)

            # Create back to menu keyboard
            reply_markup = TelegramUI.create_back_to_menu_keyboard()

            success_message = format_queue_reservation_added(
                booking_summary,
                reservation_id,
                test_mode_config=config,
            )

            await self._edit_callback_message(query,
                success_message,
                parse_mode='Markdown',
                reply_markup=reply_markup
            )

        except ValueError as e:
            # Handle duplicate reservation error
            self.logger.warning(f"Duplicate reservation attempt: {e}")

            # Create back to menu keyboard
            reply_markup = TelegramUI.create_back_to_menu_keyboard()

            duplicate_message = format_duplicate_reservation_message(str(e))

            await self._edit_callback_message(query,
                duplicate_message,
                parse_mode='Markdown',
                reply_markup=reply_markup
            )

            # Clear queue booking state
            self.clear_queue_booking_state(context)

        except Exception as e:
            await ErrorHandler.handle_booking_error(update, context, 'booking_failed', 
                                                   'Failed to add reservation to queue')


    def clear_queue_booking_state(self, context: ContextTypes.DEFAULT_TYPE) -> None:
        """Remove queue-booking state from the user context."""

        session = get_session_state(context)
        session.queue = session.queue.__class__()
        for key in ['queue_booking_date', 'queue_booking_time', 'queue_booking_courts',
                     'queue_booking_summary', 'selected_date', 'selected_month', 'selected_year',
                     'complete_matrix', 'available_dates', 'modifying_reservation_id',
                     'modifying_option']:
            context.user_data.pop(key, None)

    def _clear_queue_booking_state(self, context: ContextTypes.DEFAULT_TYPE) -> None:
        """Backward-compatibility wrapper."""
        self.clear_queue_booking_state(context)

    async def handle_queue_booking_cancel(self, update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
        """
        Handle cancellation of queue booking reservation

        Cancels the booking process and cleans up state

        Args:
            update: The telegram update containing the callback query
            context: The callback context

        Returns:
            None
        """
        t('botapp.handlers.callback_handlers.CallbackHandler._handle_queue_booking_cancel')
        query = update.callback_query

        # Safely answer the callback query
        try:
            await query.answer()
        except Exception as e:
            self.logger.warning(f"Failed to answer booking cancellation callback: {e}")

        # Clear queue booking state from context
        self.clear_queue_booking_state(context)

        # Create back to menu keyboard
        reply_markup = TelegramUI.create_back_to_menu_keyboard()

        # Show cancellation message
        await self._edit_callback_message(query,
            "❌ **Queue Booking Cancelled**\n\n"
            "Your reservation request has been cancelled. "
            "No changes have been made to your queue.\n\n"
            "You can start a new booking anytime using the main menu.",
            parse_mode='Markdown',
            reply_markup=reply_markup
        )

    async def handle_back_to_queue_courts(self, update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
        """
        Handle going back to court selection from confirmation screen

        Returns user to the court selection step of queue booking

        Args:
            update: The telegram update containing the callback query
            context: The callback context

        Returns:
            None
        """
        t('botapp.handlers.callback_handlers.CallbackHandler._handle_back_to_queue_courts')
        query = update.callback_query

        # Safely answer the callback query
        await self._safe_answer_callback(query)

        # Retrieve stored booking details
        selected_date = context.user_data.get('queue_booking_date')
        selected_time = context.user_data.get('queue_booking_time')

        if not selected_date or not selected_time:
            self.logger.error("Missing booking details when going back to court selection")
            await self._edit_callback_message(query,
                "❌ Session expired. Please start the booking process again.",
                reply_markup=TelegramUI.create_back_to_menu_keyboard()
            )
            return

        # Create court selection keyboard
        reply_markup = TelegramUI.create_queue_court_selection_keyboard(self.AVAILABLE_COURTS)

        # Show court selection interface again
        await self._edit_callback_message(query,
            f"⏰ **Queue Booking**\n\n"
            f"📅 Date: {selected_date.strftime('%A, %B %d, %Y')}\n"
            f"⏱️ Time: {selected_time}\n\n"
            f"🎾 Select your preferred court(s) for the reservation:",
            parse_mode='Markdown',
            reply_markup=reply_markup
        )

    async def handle_manage_reservation(self, update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
        """
        Handle individual reservation management

        Shows details and actions for a specific reservation

        Args:
            update: The telegram update containing the callback query
            context: The callback context
        """
        t('botapp.handlers.callback_handlers.CallbackHandler._handle_manage_reservation')
        query = update.callback_query
        user_id = query.from_user.id

        # Extract reservation ID from callback data
        reservation_id = query.data.replace('manage_res_', '')

        try:
            # Find the reservation
            reservation = None

            # Check in queue first
            queued = self.deps.reservation_queue.get_user_reservations(user_id)
            for res in queued:
                if res.get('id') == reservation_id:
                    reservation = res
                    reservation['source'] = 'queue'
                    break

            # Check in tracker if not found
            if not reservation and hasattr(self, 'reservation_tracker'):
                reservation = self.deps.reservation_tracker.get_reservation(reservation_id)
                if reservation:
                    reservation['source'] = 'tracker'

            if not reservation:
                await self._edit_callback_message(query,
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

            await self._edit_callback_message(query,
                message,
                parse_mode='Markdown',
                reply_markup=reply_markup
            )

        except Exception as e:
            self.logger.error(f"Error managing reservation: {e}")
            await self._edit_callback_message(query,
                "❌ Error loading reservation details.",
                reply_markup=TelegramUI.create_back_to_menu_keyboard()
            )

    async def handle_manage_queue_reservation(self, update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
        """
        Handle management of a specific queued reservation

        Args:
            update: The telegram update
            context: The callback context
        """
        t('botapp.handlers.callback_handlers.CallbackHandler._handle_manage_queue_reservation')
        query = update.callback_query
        await self._safe_answer_callback(query)

        # Extract reservation ID from callback data
        reservation_id = query.data.replace('manage_queue_', '')

        try:
            # Get the specific queued reservation
            reservation = self.deps.reservation_queue.get_reservation(reservation_id)

            if not reservation:
                await self._edit_callback_message(query,
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

            config = get_test_mode()
            if config.enabled:
                message += (
                    f"🧪 *TEST MODE:* Will execute in {config.trigger_delay_minutes} minutes after creation\n"
                )
            else:
                message += (
                    "This reservation will be automatically booked when the 48-hour booking window opens.\n"
                )

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

            await self._edit_callback_message(query,
                message,
                parse_mode='Markdown',
                reply_markup=reply_markup
            )

        except Exception as e:
            self.logger.error(f"Error managing queued reservation: {e}")
            await self._edit_callback_message(query,
                "❌ Error loading reservation details.",
                reply_markup=TelegramUI.create_back_to_menu_keyboard()
            )

    async def handle_reservation_action(self, update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
        """
        Handle reservation actions (cancel, modify, share)

        Args:
            update: The telegram update containing the callback query
            context: The callback context
        """
        t('botapp.handlers.callback_handlers.CallbackHandler._handle_reservation_action')
        query = update.callback_query
        user_id = query.from_user.id
        callback_data = query.data

        try:
            # Parse action and reservation ID
            parts = callback_data.split('_')
            action = parts[2]  # cancel, modify, or share
            reservation_id = '_'.join(parts[3:])  # Handle IDs with underscores

            if action == 'cancel':
                await self.handle_cancel_reservation(update, context, reservation_id)
            elif action == 'modify':
                await self.handle_modify_reservation(update, context, reservation_id)
            elif action == 'share':
                await self.handle_share_reservation(update, context, reservation_id)
            else:
                self.logger.warning(f"Unknown reservation action: {action}")
                await query.answer("Unknown action")

        except Exception as e:
            self.logger.error(f"Error handling reservation action: {e}")
            await query.answer("Error processing action")

    async def handle_cancel_reservation(self, update: Update, context: ContextTypes.DEFAULT_TYPE, 
                                        reservation_id: str) -> None:
        """Cancel a reservation"""
        t('botapp.handlers.callback_handlers.CallbackHandler._handle_cancel_reservation')
        query = update.callback_query
        user_id = query.from_user.id

        try:
            # Find and cancel the reservation
            cancelled = False

            # Try queue first
            reservation = self.deps.reservation_queue.get_reservation(reservation_id)
            if reservation and reservation.get('user_id') == user_id:
                cancelled = self.deps.reservation_queue.remove_reservation(reservation_id)

            # Try tracker if not in queue
            if not cancelled and hasattr(self, 'reservation_tracker'):
                reservation = self.deps.reservation_tracker.get_reservation(reservation_id)
                if reservation and reservation.get('user_id') == user_id:
                    cancelled = self.deps.reservation_tracker.cancel_reservation(reservation_id)

            if cancelled:
                await self._edit_callback_message(query,
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

    async def handle_modify_reservation(self, update: Update, context: ContextTypes.DEFAULT_TYPE, 
                                       reservation_id: str) -> None:
        """Modify a reservation"""
        t('botapp.handlers.callback_handlers.CallbackHandler._handle_modify_reservation')
        query = update.callback_query
        user_id = query.from_user.id

        # Find the reservation
        reservation = None
        is_queued = False

        # Check queue first
        res = self.deps.reservation_queue.get_reservation(reservation_id)
        if res and res.get('user_id') == user_id:
            reservation = res
            is_queued = True

        # Check tracker if not in queue
        if not reservation and hasattr(self, 'reservation_tracker'):
            res = self.deps.reservation_tracker.get_reservation(reservation_id)
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

            await self._edit_callback_message(query,
                "✏️ **Modify Reservation**\n\n"
                "What would you like to change?",
                parse_mode='Markdown',
                reply_markup=InlineKeyboardMarkup(keyboard)
            )
        else:
            # For immediate/completed reservations, show coming soon
            await self._edit_callback_message(query,
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

    async def handle_share_reservation(self, update: Update, context: ContextTypes.DEFAULT_TYPE, 
                                      reservation_id: str) -> None:
        """Share reservation details"""
        t('botapp.handlers.callback_handlers.CallbackHandler._handle_share_reservation')
        query = update.callback_query
        user_id = query.from_user.id

        try:
            # Find the reservation
            reservation = None

            # Check queue
            res = self.deps.reservation_queue.get_reservation(reservation_id)
            if res and res.get('user_id') == user_id:
                reservation = res

            # Check tracker
            if not reservation and hasattr(self, 'reservation_tracker'):
                res = self.deps.reservation_tracker.get_reservation(reservation_id)
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

    async def handle_modify_option(self, update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
        """Handle modification options for queued reservations"""
        t('botapp.handlers.callback_handlers.CallbackHandler._handle_modify_option')
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
        reservation = self.deps.reservation_queue.get_reservation(reservation_id)
        if not reservation:
            await query.answer("Reservation not found")
            return

        if option == 'date':
            # Show year selection for date modification
            keyboard = TelegramUI.create_year_selection_keyboard()
            await self._edit_callback_message(query,
                "📅 **Select New Year**\n\n"
                "Choose the year for your reservation:",
                parse_mode='Markdown',
                reply_markup=keyboard
            )
        elif option == 'time':
            # Show time selection
            keyboard = TelegramUI.create_time_selection_keyboard_simple(reservation.date)
            await self._edit_callback_message(query,
                "⏰ **Select New Time**\n\n"
                "Choose your preferred time:",
                parse_mode='Markdown',
                reply_markup=keyboard
            )
        elif option == 'courts':
            # Show court selection
            keyboard = TelegramUI.create_court_selection_keyboard()
            await self._edit_callback_message(query,
                "🏃 **Select New Courts**\n\n"
                "Choose your court preferences:",
                parse_mode='Markdown',
                reply_markup=keyboard
            )

    async def handle_time_modification(self, update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
        """Handle time modification from the modify menu"""
        t('botapp.handlers.callback_handlers.CallbackHandler._handle_time_modification')
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
        reservation = self.deps.reservation_queue.get_reservation(modifying_id)
        if reservation:
            reservation['target_time'] = time_str
            self.deps.reservation_queue.update_reservation(modifying_id, reservation)

            # Clear modification context
            context.user_data.pop('modifying_reservation_id', None)
            context.user_data.pop('modifying_option', None)

            # Show success message
            await self._edit_callback_message(query,
                f"✅ **Time Updated!**\n\n"
                f"Your reservation time has been changed to {time_str}.",
                parse_mode='Markdown',
                reply_markup=InlineKeyboardMarkup([
                    [InlineKeyboardButton("📋 View Reservation", callback_data=f"manage_queue_{modifying_id}")],
                    [InlineKeyboardButton("🏠 Main Menu", callback_data='back_to_menu')]
                ])
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
        t('botapp.handlers.callback_handlers.CallbackHandler._display_user_reservations')
        query = update.callback_query

        try:
            # Get all reservations for the user
            all_reservations = []

            # Get queued reservations
            queued = self.deps.reservation_queue.get_user_reservations(target_user_id)
            for res in queued:
                res['source'] = 'queue'
                all_reservations.append(res)

            # Get active reservations
            if hasattr(self, 'reservation_tracker'):
                active = self.deps.reservation_tracker.get_user_active_reservations(target_user_id)
                for res in active:
                    res['source'] = 'tracker'
                    all_reservations.append(res)

            if not all_reservations:
                user_name = self._get_user_name(target_user_id)
                await self._edit_callback_message(query,
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

            await self._edit_callback_message(query,
                message,
                parse_mode='Markdown',
                reply_markup=InlineKeyboardMarkup(keyboard)
            )

        except Exception as e:
            self.logger.error(f"Error displaying user reservations: {e}")
            await self._edit_callback_message(query,
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
        t('botapp.handlers.callback_handlers.CallbackHandler._display_all_reservations')
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

        await self._edit_callback_message(query,
            message,
            parse_mode='Markdown',
            reply_markup=InlineKeyboardMarkup(keyboard)
        )
