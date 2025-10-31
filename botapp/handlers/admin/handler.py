"""Admin and supervisor callback handlers."""


from __future__ import annotations
from tracking import t

from typing import Any, Dict, List

from telegram import InlineKeyboardButton, InlineKeyboardMarkup, Update
from telegram.ext import ContextTypes

from botapp.handlers.dependencies import CallbackDependencies
from botapp.handlers.mixins import CallbackResponseMixin
from botapp.ui.telegram_ui import TelegramUI
from botapp.error_handler import ErrorHandler
from botapp.i18n.helpers import get_user_translator
from infrastructure.settings import get_test_mode, update_test_mode
from automation.availability.datetime_helpers import DateTimeHelpers


class AdminHandler(CallbackResponseMixin):
    def __init__(self, deps: CallbackDependencies) -> None:
        self.deps = deps
        self.logger = deps.logger

    def _get_user_name(self, user_id: int) -> str:
        """Get user's display name from user_id."""
        user_data = self.deps.user_manager.get_user(user_id)
        if user_data:
            first_name = user_data.get('first_name', '')
            last_name = user_data.get('last_name', '')
            name = f"{first_name} {last_name}".strip()
            return name if name else f"User {user_id}"
        return f"User {user_id}"

    async def handle_admin_menu(self, update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
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
        t('botapp.handlers.callback_handlers.CallbackHandler._handle_admin_menu')
        query = update.callback_query
        user_id = query.from_user.id

        try:
            # Get user's translator
            tr = get_user_translator(self.deps.user_manager, user_id)

            # Authorization check - retrieve user profile
            user_profile = self.deps.user_manager.get_user(user_id)

            # Check if user exists and has admin privileges
            if user_profile is None or not user_profile.get('is_admin', False):
                # Log unauthorized access attempt
                self.logger.warning(f"Unauthorized admin access attempt by user_id: {user_id}")

                # Send unauthorized message
                reply_markup = TelegramUI.create_back_to_menu_keyboard()
                await query.edit_message_text(
                    tr.t('admin.access_denied'),
                    parse_mode='Markdown',
                    reply_markup=reply_markup
                )
                return

            # User is authorized - display admin menu
            self.logger.info(f"Admin access granted to user_id: {user_id}")

            pending_count = len(self.deps.reservation_queue.get_pending_reservations())

            config = get_test_mode()

            # Create admin menu keyboard
            reply_markup = TelegramUI.create_admin_menu_keyboard(
                pending_count,
                test_mode_enabled=config.enabled,
            )

            # Display admin panel
            await query.edit_message_text(
                f"{tr.t('admin.title')}\n\n{tr.t('admin.welcome')}",
                parse_mode='Markdown',
                reply_markup=reply_markup
            )

        except Exception as e:
            await ErrorHandler.handle_booking_error(update, context, 'system_error', 
                                                   'Error accessing admin panel')

    async def handle_admin_toggle_test_mode(self, update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
        """Toggle test mode flags from the admin interface."""

        t('botapp.handlers.callback_handlers.CallbackHandler._handle_admin_toggle_test_mode')
        query = update.callback_query
        user_id = query.from_user.id
        await self._safe_answer_callback(query)

        # Get user's translator
        tr = get_user_translator(self.deps.user_manager, user_id)

        current = get_test_mode()
        if current.enabled:
            new_config = update_test_mode(
                enabled=False,
                allow_within_48h=False,
            )
            status_text = tr.t('admin.test_mode_disabled')
        else:
            new_config = update_test_mode(
                enabled=True,
                allow_within_48h=True,
            )
            status_text = tr.t('admin.test_mode_enabled')

        pending_count = len(self.deps.reservation_queue.get_pending_reservations())

        reply_markup = TelegramUI.create_admin_menu_keyboard(
            pending_count=pending_count,
            test_mode_enabled=new_config.enabled,
        )

        await query.edit_message_text(
            status_text,
            parse_mode='Markdown',
            reply_markup=reply_markup,
        )

    async def handle_admin_my_reservations(self, update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
        """
        Admin view of their own reservations

        Reuses the existing user reservations display logic
        """
        t('botapp.handlers.callback_handlers.CallbackHandler._handle_admin_my_reservations')
        # Simply show the regular user view for the admin's own reservations
        await self.display_user_reservations(update, context, update.callback_query.from_user.id)

    async def handle_admin_users_list(self, update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
        """
        Show list of users for admin to select from
        """
        t('botapp.handlers.callback_handlers.CallbackHandler._handle_admin_users_list')
        query = update.callback_query
        user_id = query.from_user.id

        try:
            # Get user's translator
            tr = get_user_translator(self.deps.user_manager, user_id)

            # Get all users
            all_users = self.deps.user_manager.get_all_users()

            if not all_users:
                await query.edit_message_text(
                    tr.t('admin.no_users'),
                    parse_mode='Markdown',
                    reply_markup=TelegramUI.create_back_to_menu_keyboard()
                )
                return

            # Create buttons for each user
            keyboard = []
            for uid, user_data in all_users.items():
                user_name = f"{user_data.get('first_name', '')} {user_data.get('last_name', '')}".strip()
                if not user_name:
                    user_name = f"User {uid}"

                # Add admin badge if user is admin
                if user_data.get('is_admin', False):
                    user_name += " 👮"

                keyboard.append([
                    InlineKeyboardButton(
                        user_name,
                        callback_data=f"admin_view_user_{uid}"
                    )
                ])

            # Add back button
            keyboard.append([InlineKeyboardButton(tr.t('admin.back_to_admin'), callback_data='menu_admin')])

            await query.edit_message_text(
                tr.t('admin.users_list'),
                parse_mode='Markdown',
                reply_markup=InlineKeyboardMarkup(keyboard)
            )

        except Exception as e:
            self.logger.error(f"Error showing users list: {e}")
            tr = get_user_translator(self.deps.user_manager, user_id)
            await query.edit_message_text(
                tr.t('admin.error_loading_users'),
                reply_markup=TelegramUI.create_back_to_menu_keyboard()
            )

    async def handle_admin_all_reservations(self, update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
        """
        Show all reservations from all users
        """
        t('botapp.handlers.callback_handlers.CallbackHandler._handle_admin_all_reservations')
        query = update.callback_query
        user_id = query.from_user.id

        try:
            # Get user's translator
            tr = get_user_translator(self.deps.user_manager, user_id)

            all_reservations = []

            # Get all users
            all_users = self.deps.user_manager.get_all_users()

            # Collect reservations from all users
            for uid in all_users.keys():
                # Get queued reservations
                queued = self.deps.reservation_queue.get_user_reservations(uid)
                for res in queued:
                    res['source'] = 'queue'
                    res['user_name'] = self._get_user_name(uid)
                    all_reservations.append(res)

                # Get active reservations
                if hasattr(self, 'reservation_tracker'):
                    active = self.deps.reservation_tracker.get_user_active_reservations(uid)
                    for res in active:
                        res['source'] = 'tracker'
                        res['user_name'] = self._get_user_name(uid)
                        all_reservations.append(res)

            if not all_reservations:
                await query.edit_message_text(
                    f"{tr.t('admin.all_reservations')}\n\n{tr.t('admin.no_reservations')}",
                    parse_mode='Markdown',
                    reply_markup=InlineKeyboardMarkup([
                        [InlineKeyboardButton(tr.t('admin.back_to_admin'), callback_data='menu_admin')],
                        [InlineKeyboardButton(tr.t('nav.back_to_menu'), callback_data='back_to_menu')]
                    ])
                )
                return

            # Sort by date and time
            all_reservations.sort(key=lambda x: (
                x.get('target_date', x.get('date', '')),
                x.get('target_time', x.get('time', ''))
            ))

            # Display reservations
            await self.display_all_reservations(query, all_reservations, user_id)

        except Exception as e:
            self.logger.error(f"Error showing all reservations: {e}")
            tr = get_user_translator(self.deps.user_manager, user_id)
            await query.edit_message_text(
                tr.t('admin.error_loading_reservations'),
                reply_markup=TelegramUI.create_back_to_menu_keyboard()
            )

    async def display_user_reservations(self, update: Update, context: ContextTypes.DEFAULT_TYPE, 
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

    async def display_all_reservations(self, query, all_reservations: List[Dict[str, Any]], user_id: int) -> None:
        """
        Display all reservations from all users

        Args:
            query: The callback query
            all_reservations: List of all reservations with user info
            user_id: The admin user ID for translations
        """
        t('botapp.handlers.callback_handlers.CallbackHandler._display_all_reservations')

        # Get user's translator
        tr = get_user_translator(self.deps.user_manager, user_id)

        # Group by date for better organization
        reservations_by_date = {}
        for res in all_reservations:
            date_key = res.get('target_date', res.get('date', 'Unknown'))
            if date_key not in reservations_by_date:
                reservations_by_date[date_key] = []
            reservations_by_date[date_key].append(res)

        # Create message
        message = f"{tr.t('admin.all_reservations')}\n\n"
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
            [InlineKeyboardButton(tr.t('admin.back_to_admin'), callback_data='menu_admin')],
            [InlineKeyboardButton(tr.t('nav.back_to_menu'), callback_data='back_to_menu')]
        ]

        await query.edit_message_text(
            message,
            parse_mode='Markdown',
            reply_markup=InlineKeyboardMarkup(keyboard)
        )
