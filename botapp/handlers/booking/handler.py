"""Booking-related callback handlers."""

from __future__ import annotations
from tracking import t

from datetime import date, datetime, timedelta
from typing import Any, Dict

from telegram import InlineKeyboardButton, InlineKeyboardMarkup, Update
from telegram.ext import ContextTypes

from botapp.handlers.dependencies import CallbackDependencies
from botapp.handlers.state import get_session_state, reset_flow
from botapp.ui.telegram_ui import TelegramUI
from botapp.error_handler import ErrorHandler
from automation.availability import DateTimeHelpers
from infrastructure.settings import get_test_mode
from infrastructure.constants import get_court_hours
from botapp.handlers.booking.ui_factory import BookingUIFactory
from botapp.handlers.queue.live_availability import fetch_live_time_slots
import pytz


class BookingHandler:
    BOOKING_WINDOW_DAYS = 2
    AVAILABLE_COURTS = [1, 2, 3]

    def __init__(self, deps: CallbackDependencies) -> None:
        self.deps = deps
        self.logger = deps.logger
        self.ui_factory = BookingUIFactory()

    async def handle_reserve_menu(self, update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
        """
        Handle Reserve Court menu option - show booking type selection

        Args:
            update: The telegram update containing the callback query
            context: The callback context

        Returns:
            None
        """
        t('botapp.handlers.callback_handlers.CallbackHandler._handle_reserve_menu')
        # Debug: Log method entry with user context
        user_id = update.callback_query.from_user.id if update.callback_query and update.callback_query.from_user else "Unknown"
        self.logger.debug(f"_handle_reserve_menu: Method entry for user_id={user_id}")

        query = update.callback_query
        view = self.ui_factory.booking_type_selection()

        # Debug: Log pre-message sending
        self.logger.debug(f"_handle_reserve_menu: About to send booking type selection to user_id={user_id}")

        await query.edit_message_text(view.text, reply_markup=view.reply_markup)

    async def handle_performance_menu(self, update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
        """
        Handle Performance menu option

        Args:
            update: The telegram update containing the callback query
            context: The callback context

        Returns:
            None
        """
        t('botapp.handlers.callback_handlers.CallbackHandler._handle_performance_menu')
        query = update.callback_query
        view = self.ui_factory.performance_menu()

        await query.edit_message_text(view.text, reply_markup=view.reply_markup)

    async def handle_reservations_menu(self, update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
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
        t('botapp.handlers.callback_handlers.CallbackHandler._handle_reservations_menu')
        query = update.callback_query
        user_id = query.from_user.id

        try:
            # Check if user is admin
            is_admin = self.deps.user_manager.is_admin(user_id)

            if is_admin:
                # Show admin options menu
                admin_view = self.ui_factory.admin_reservations_menu()

                await query.edit_message_text(
                    admin_view.text,
                    parse_mode='Markdown',
                    reply_markup=admin_view.reply_markup,
                )
                return
            # Get all reservations for the user
            all_reservations = []

            # 1. Get queued reservations
            queued = self.deps.reservation_queue.get_user_reservations(user_id)
            for res in queued:
                res['source'] = 'queue'
                all_reservations.append(res)

            # 2. Get completed/immediate reservations from tracker
            if hasattr(self, 'reservation_tracker'):
                active_reservations = self.deps.reservation_tracker.get_user_active_reservations(user_id)
                for res in active_reservations:
                    res['source'] = 'tracker'
                    all_reservations.append(res)

            if not all_reservations:
                view = self.ui_factory.empty_reservations_view()
                await query.edit_message_text(
                    view.text,
                    parse_mode='Markdown',
                    reply_markup=view.reply_markup,
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

    def _help_sections(self) -> list[tuple[str, str]]:
        return [
            (
                "🎾 **Welcome to LVBot!**",
                "LVBot is your automated tennis court booking assistant for Club La Villa. "
                "We help you secure court reservations with intelligent monitoring and "
                "automated booking capabilities.",
            ),
            (
                "**🚀 Key Features:**",
                "\n".join(
                    [
                        "• Real-time court availability checking",
                        "• Smart reservation queue management",
                        "• 48-hour advance booking window",
                        "• Automated booking execution",
                        "• Personal reservation tracking",
                    ]
                ),
            ),
            (
                "**📱 Available Commands:**",
                "\n".join(
                    [
                        "• `/start` - Show the main menu",
                        "• `/check_courts` - Quick availability check",
                    ]
                ),
            ),
            (
                "**📋 How to Use:**",
                "\n".join(
                    [
                        "1️⃣ **Reserve Court** - Check real-time availability",
                        "2️⃣ **My Reservations** - View your bookings",
                        "3️⃣ **Queue Booking** - Schedule future bookings (coming soon)",
                        "4️⃣ **Settings** - Customize preferences (coming soon)",
                    ]
                ),
            ),
            (
                "**⚠️ Important Notes:**",
                "\n".join(
                    [
                        "• Courts open for booking exactly 48 hours in advance",
                        "• Availability is checked in real-time",
                        "• Queue system executes bookings automatically",
                        "• Keep your profile updated for smooth bookings",
                    ]
                ),
            ),
            (
                "**🆘 Need Support?**",
                "Contact the admin team for assistance!",
            ),
        ]

    def _about_sections(self) -> list[tuple[str, str]]:
        return [
            (
                "🎾 **LVBot - Tennis Court Booking Assistant**",
                "LVBot streamlines tennis court reservations at Club La Villa using "
                "browser automation and real-time monitoring.",
            ),
            (
                "**🔧 Technical Features:**",
                "\n".join(
                    [
                        "• Playwright-powered browser automation",
                        "• Async/await architecture for performance",
                        "• Multi-browser parallel processing",
                        "• Smart refresh strategies",
                        "• Persistent reservation queue",
                    ]
                ),
            ),
            (
                "**📊 System Stats:**",
                "\n".join(
                    [
                        "• 48-hour booking window monitoring",
                        "• Automated booking execution coverage",
                        "• Emergency fallback browser for resiliency",
                    ]
                ),
            ),
            (
                "**🛠 Current Roadmap:**",
                "\n".join(
                    [
                        "• Enhanced queue analytics",
                        "• Expanded profile customization",
                        "• Improved admin tooling",
                    ]
                ),
            ),
        ]

    def _render_info_message(self, title: str, sections: list[tuple[str, str]]) -> str:
        parts = [title, ""]
        for heading, body in sections:
            parts.append(heading)
            if body:
                parts.append(body)
            parts.append("")
        return "\n".join(parts).strip()

    async def _display_static_page(
        self,
        query,
        *,
        title: str,
        sections: list[tuple[str, str]],
    ) -> None:
        reply_markup = TelegramUI.create_back_to_menu_keyboard()
        await query.edit_message_text(
            self._render_info_message(title, sections),
            parse_mode='Markdown',
            reply_markup=reply_markup,
        )

    async def handle_help_menu(self, update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
        t('botapp.handlers.callback_handlers.CallbackHandler._handle_help_menu')
        await self._display_static_page(
            update.callback_query,
            title="💡 **Help - LVBot Tennis Court Assistant**",
            sections=self._help_sections(),
        )

    async def handle_about_menu(self, update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
        t('botapp.handlers.callback_handlers.CallbackHandler._handle_about_menu')
        await self._display_static_page(
            update.callback_query,
            title="ℹ️ **About LVBot**",
            sections=self._about_sections(),
        )

    async def handle_back_to_menu(self, update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
        """
        Handle back to menu navigation

        Shows the main menu again using TelegramUI

        Args:
            update: The telegram update containing the callback query
            context: The callback context

        Returns:
            None
        """
        t('botapp.handlers.callback_handlers.CallbackHandler._handle_back_to_menu')
        query = update.callback_query
        user_id = query.from_user.id
        is_admin = self.deps.user_manager.is_admin(user_id)

        # Get user tier
        tier = self.deps.user_manager.get_user_tier(user_id)
        tier_badge = TelegramUI.format_user_tier_badge(tier.name)

        # Use the existing main menu from TelegramUI
        reply_markup = TelegramUI.create_main_menu_keyboard(is_admin=is_admin)

        await query.edit_message_text(
            f"🎾 Welcome to LVBot! {tier_badge}\n\nChoose an option:",
            reply_markup=reply_markup
        )

    async def handle_48h_immediate_booking(self, update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
        """
        Handle immediate booking (within 48h) - goes straight to availability check

        Args:
            update: The telegram update containing the callback query
            context: The callback context

        Returns:
            None
        """
        t('botapp.handlers.callback_handlers.CallbackHandler._handle_48h_immediate_booking')
        query = update.callback_query
        user_id = query.from_user.id

        self.logger.info(f"User {user_id} selected immediate 48h booking")

        # Set state for availability checking flow
        context.user_data['current_flow'] = 'availability_check'

        # Show loading message
        await query.edit_message_text("🔍 Checking court availability for the next 48 hours...")

        try:
            # Check if browser pool is available first
            if not hasattr(self.deps.availability_checker, 'browser_pool') or not self.deps.availability_checker.browser_pool:
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
            availability_results = await self.deps.availability_checker.check_availability()

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

    async def handle_48h_future_booking(self, update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
        """
        Handle future booking (after 48h) - show year selection

        Args:
            update: The telegram update containing the callback query
            context: The callback context

        Returns:
            None
        """
        t('botapp.handlers.callback_handlers.CallbackHandler._handle_48h_future_booking')
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

    async def handle_date_selection(self, update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
        """
        Handle date selection callbacks

        Args:
            update: The telegram update containing the callback query
            context: The callback context

        Returns:
            None
        """
        t('botapp.handlers.callback_handlers.CallbackHandler._handle_date_selection')
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
            if not hasattr(self.deps.availability_checker, 'browser_pool') or not self.deps.availability_checker.browser_pool:
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
            results = await self.deps.availability_checker.check_availability()

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

    async def handle_year_selection(self, update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
        """
        Handle year selection for future booking

        Args:
            update: The telegram update containing the callback query
            context: The callback context

        Returns:
            None
        """
        t('botapp.handlers.callback_handlers.CallbackHandler._handle_year_selection')
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

    async def handle_month_selection(self, update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
        """
        Handle month selection for future booking

        Args:
            update: The telegram update containing the callback query
            context: The callback context

        Returns:
            None
        """
        t('botapp.handlers.callback_handlers.CallbackHandler._handle_month_selection')
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

    async def handle_future_date_selection(self, update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
        """
        Handle future date selection - route to queue booking flow

        Args:
            update: The telegram update containing the callback query
            context: The callback context

        Returns:
            None
        """
        t('botapp.handlers.callback_handlers.CallbackHandler._handle_future_date_selection')
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
                reservation = self.deps.reservation_queue.get_reservation(modifying_id)
                if reservation:
                    reservation['target_date'] = selected_date.strftime('%Y-%m-%d')
                    self.deps.reservation_queue.update_reservation(modifying_id, reservation)

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
            config = get_test_mode()
            today = date.today()
            days_ahead = (selected_date - today).days

            if days_ahead < 2 and not (config.enabled and config.allow_within_48h):
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

            tz = pytz.timezone('America/Mexico_City')
            now = datetime.now(tz)

            if config.enabled and config.allow_within_48h:
                live_slots = await fetch_live_time_slots(
                    self.deps,
                    context,
                    selected_date,
                    tz,
                    now,
                    self.logger,
                    log_prefix="Booking",
                )

                if live_slots is None:
                    self.logger.warning(
                        "Test mode live availability unavailable for %s; falling back to static timetable",
                        selected_date,
                    )
                    available_time_slots = list(all_time_slots)
                else:
                    available_time_slots = live_slots
            else:
                available_time_slots = [
                    time_str
                    for time_str in all_time_slots
                    if self._slot_is_beyond_window(selected_date, time_str, tz, now)
                ]

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

    @staticmethod
    def _slot_is_beyond_window(selected_date: date, time_str: str, tz, now: datetime) -> bool:
        """Return True when the slot is at least 48 hours ahead."""

        try:
            hour, minute = map(int, time_str.split(':'))
        except ValueError:
            return False

        slot_dt = datetime.combine(
            selected_date,
            datetime.min.time().replace(hour=hour, minute=minute),
        )
        slot_dt = tz.localize(slot_dt)
        return (slot_dt - now).total_seconds() >= 48 * 3600

    async def handle_blocked_date_selection(self, update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
        """
        Handle selection of blocked dates (within 48h) - redirect to immediate booking

        Args:
            update: The telegram update containing the callback query
            context: The callback context

        Returns:
            None
        """
        t('botapp.handlers.callback_handlers.CallbackHandler._handle_blocked_date_selection')
        query = update.callback_query
        callback_data = query.data

        # Extract date from callback data (format: blocked_date_YYYY-MM-DD)
        date_str = callback_data.replace('blocked_date_', '')

        try:
            # Parse the date
            selected_date = datetime.strptime(date_str, '%Y-%m-%d').date()

            config = get_test_mode()

            if config.enabled and config.allow_within_48h:
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
                await self.handle_48h_immediate_booking(update, context)

        except Exception as e:
            self.logger.error(f"Error handling blocked date: {e}")
            await query.answer("❌ Error processing date selection")

    async def handle_back_to_month(self, update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
        """
        Handle navigation back to month selection

        Args:
            update: The telegram update containing the callback query
            context: The callback context

        Returns:
            None
        """
        t('botapp.handlers.callback_handlers.CallbackHandler._handle_back_to_month')
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

    async def handle_day_cycling(self, update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
        """
        Handle day cycling callback from matrix layout

        Args:
            update: The telegram update containing the callback query
            context: The callback context

        Returns:
            None
        """
        t('botapp.handlers.callback_handlers.CallbackHandler._handle_day_cycling')
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
                availability_results = await self.deps.availability_checker.check_availability()

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

    async def handle_unknown_menu(self, update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
        """
        Handle unknown callback data

        Logs the unknown callback and shows an error message

        Args:
            update: The telegram update containing the callback query
            context: The callback context

        Returns:
            None
        """
        t('botapp.handlers.callback_handlers.CallbackHandler._handle_unknown_menu')
        query = update.callback_query
        self.logger.warning(f"Unknown callback data: {query.data}")
        await query.edit_message_text(
            "❓ Unknown option\n\nPlease use the menu buttons or /start to begin again."
        )

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
        t('botapp.handlers.callback_handlers.CallbackHandler._extract_availability_for_date_cached')
        import asyncio

        try:
            # Extract from all courts without refresh
            tasks = []
            for court in self.deps.availability_checker.pool.courts:
                task = self._extract_court_times_for_date_cached(court, target_date)
                tasks.append(task)

            results = await asyncio.gather(*tasks, return_exceptions=True)

            # Process results and handle exceptions
            final_results = {}
            for court, result in zip(self.deps.availability_checker.pool.courts, results):
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
        t('botapp.handlers.callback_handlers.CallbackHandler._extract_court_times_for_date_cached')
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
            page = await self.deps.availability_checker.pool.get_page(court_num)
            if not page:
                self.logger.warning(f"No page available for court {court_num}")
                return []

            from automation.forms.acuity_page_validator import AcuityPageValidator

            frame = await AcuityPageValidator._get_extraction_frame(page)
            if not frame:
                self.logger.warning(f"Court {court_num}: No extraction frame available")
                return []

            times_by_day = await fetch_available_slots(page)
            target_date_str = target_date.strftime('%Y-%m-%d')

            if target_date_str in times_by_day:
                available_times = times_by_day[target_date_str]
                self.logger.info(f"Court {court_num}: Found {len(available_times)} times for {target_date}: {available_times}")
            else:
                available_times = []
                self.logger.warning(f"Court {court_num}: No times found for specific date {target_date}")

            # Convert to TimeSlot objects
            from reservations.models.time_slot import TimeSlot
            time_slots = []
            for time_str in available_times:
                try:
                    time_slots.append(TimeSlot(
                        start_time=time_str,
                        end_time=self.deps.availability_checker._add_hour(time_str),
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
        t('botapp.handlers.callback_handlers.CallbackHandler._build_complete_matrix_for_all_days')
        import asyncio
        from automation.availability import AcuityTimeParser
        from automation.forms.acuity_page_validator import AcuityPageValidator

        try:
            self.logger.info("🏗️ MATRIX BUILDER - Building complete matrix for all available days")

            # Extract times by day for all courts in parallel
            tasks = []
            for court in self.deps.availability_checker.pool.courts:
                task = self._extract_all_days_for_court(court)
                tasks.append(task)

            results = await asyncio.gather(*tasks, return_exceptions=True)

            # Merge results into complete matrix
            complete_matrix = {}

            for court, result in zip(self.deps.availability_checker.pool.courts, results):
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
        t('botapp.handlers.callback_handlers.CallbackHandler._extract_all_days_for_court')
        """
        Extract times for all available days for a specific court.

        Args:
            court_num: Court number

        Returns:
            Dict mapping date strings to time lists: {'2025-07-21': ['20:15'], '2025-07-22': ['09:00']}
        """
        try:
            # Get browser page for this court
            page = await self.deps.availability_checker.pool.get_page(court_num)
            if not page:
                self.logger.warning(f"No page available for court {court_num}")
                return {}

            from automation.forms.acuity_page_validator import AcuityPageValidator

            # Get the appropriate frame for extraction
            frame = await AcuityPageValidator._get_extraction_frame(page)
            if not frame:
                self.logger.warning(f"Court {court_num}: No extraction frame available")
                return {}

            times_by_day = await fetch_available_slots(page)

            self.logger.info(f"Court {court_num}: Extracted times for {len(times_by_day)} days: {times_by_day}")
            return times_by_day

        except Exception as e:
            self.logger.warning(f"Court {court_num} all-days extraction failed: {e}")
            return {}
