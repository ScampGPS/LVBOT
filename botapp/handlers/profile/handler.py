"""Profile management callbacks."""

from __future__ import annotations
from tracking import t

from typing import Any, Callable

from telegram import InlineKeyboardButton, InlineKeyboardMarkup, Update
from telegram.ext import ContextTypes

from botapp.handlers.dependencies import CallbackDependencies
from botapp.handlers.state import get_session_state
from botapp.ui.telegram_ui import TelegramUI
from botapp.error_handler import ErrorHandler


class ProfileHandler:
    """Handles profile viewing and editing callbacks."""

    def __init__(self, deps: CallbackDependencies) -> None:
        self.deps = deps
        self.logger = deps.logger

    async def handle_profile_menu(self, update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
        t('botapp.handlers.profile.handler.ProfileHandler.handle_profile_menu')
        query = update.callback_query
        user_id = query.from_user.id

        try:
            user_profile = self.deps.user_manager.get_user(user_id)
            if not user_profile:
                await query.edit_message_text(
                    "📇 No profile found. Please contact an administrator.",
                    reply_markup=TelegramUI.create_back_to_menu_keyboard(),
                )
                return

            tier = self.deps.user_manager.get_user_tier(user_id)
            tier_badge = TelegramUI.format_user_tier_badge(tier.name)

            message = (
                "📇 **Profile Overview**\n\n"
                f"Name: {user_profile.get('first_name', 'Unknown')} {user_profile.get('last_name', '')}\n"
                f"Email: {user_profile.get('email', 'Not set')}\n"
                f"Phone: (+502) {user_profile.get('phone', 'Not set')}\n"
                f"Tier: {tier_badge}\n"
            )

            keyboard = TelegramUI.create_profile_menu_keyboard()
            await query.edit_message_text(message, reply_markup=keyboard, parse_mode='Markdown')
        except Exception as exc:  # pragma: no cover - defensive guard
            self.logger.error("Failed to show profile menu: %s", exc)
            await ErrorHandler.handle_booking_error(update, context, 'system_error', 'Failed to load profile')

    async def handle_edit_profile(self, update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
        t('botapp.handlers.profile.handler.ProfileHandler.handle_edit_profile')
        query = update.callback_query
        try:
            keyboard = TelegramUI.create_profile_edit_keyboard()
            await query.edit_message_text(
                "✏️ **Edit Profile**\n\nSelect a field to edit:",
                parse_mode='Markdown',
                reply_markup=reply_markup,
            )
        except Exception as exc:
            await ErrorHandler.handle_booking_error(update, context, 'system_error', 'Failed to show edit options')

    async def handle_edit_name(self, update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
        t('botapp.handlers.profile.handler.ProfileHandler.handle_edit_name')
        query = update.callback_query
        user_id = query.from_user.id

        try:
            session = get_session_state(context)
            session.profile.name_input = ''
            session.profile.editing_name_field = None
            context.user_data['name_input'] = ''
            context.user_data.pop('editing_name_field', None)

            buttons = [
                [InlineKeyboardButton("Edit First Name", callback_data='edit_first_name')],
                [InlineKeyboardButton("Edit Last Name", callback_data='edit_last_name')],
                [InlineKeyboardButton("Back", callback_data='menu_profile')],
            ]
            keyboard = InlineKeyboardMarkup(buttons)

            await query.edit_message_text(
                "🧑‍💼 **Name Editing**\n\nChoose the name field you want to edit:",
                parse_mode='Markdown',
                reply_markup=reply_markup,
            )
        except Exception as exc:
            await ErrorHandler.handle_booking_error(update, context, 'system_error', 'Failed to start name edit')

    async def handle_edit_first_name(self, update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
        t('botapp.handlers.profile.handler.ProfileHandler.handle_edit_first_name')
        try:
            await self._start_name_edit(
                update,
                context,
                field='first_name',
                icon='👤',
                label='First Name',
            )
        except Exception as exc:
            await ErrorHandler.handle_booking_error(update, context, 'system_error', 'Failed to edit first name')

    async def handle_edit_last_name(self, update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
        t('botapp.handlers.profile.handler.ProfileHandler.handle_edit_last_name')
        try:
            await self._start_name_edit(
                update,
                context,
                field='last_name',
                icon='👥',
                label='Last Name',
            )
        except Exception as exc:
            await ErrorHandler.handle_booking_error(update, context, 'system_error', 'Failed to edit last name')

    async def handle_edit_phone(self, update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
        t('botapp.handlers.profile.handler.ProfileHandler.handle_edit_phone')
        try:
            await self._start_contact_edit(
                update,
                context,
                field='phone',
                session_attr='phone_input',
                context_key='phone_input',
                icon='📱',
                label='Phone Number',
                message_builder=lambda current: (
                    "📱 **Edit Phone Number**\n\n"
                    f"Current: (+502) {current if current else 'Not set'}\n\n"
                    "(+502) ________\n\n"
                    "Use the keypad below to enter your phone number:"
                ),
                keyboard_factory=TelegramUI.create_phone_keypad,
            )
        except Exception as exc:
            await ErrorHandler.handle_booking_error(update, context, 'system_error', 'Failed to show phone edit')

    async def handle_edit_email(self, update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
        t('botapp.handlers.profile.handler.ProfileHandler.handle_edit_email')
        try:
            await self._start_contact_edit(
                update,
                context,
                field='email',
                session_attr='email_input',
                context_key='email_input',
                icon='📧',
                label='Email',
                message_builder=lambda current: (
                    "📧 **Edit Email**\n\n"
                    f"Current: {current if current else 'Not set'}\n\n"
                    "Email: \\_\n\n"
                    "Use the keyboard below:"
                ),
                keyboard_factory=TelegramUI.create_email_char_keyboard,
            )
        except Exception as exc:
            await ErrorHandler.handle_booking_error(update, context, 'system_error', 'Failed to show email edit')

    async def handle_cancel_edit(self, update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
        t('botapp.handlers.profile.handler.ProfileHandler.handle_cancel_edit')
        query = update.callback_query
        try:
            session = get_session_state(context)
            session.profile = session.profile.__class__()
            context.user_data.pop('editing_field', None)
            context.user_data.pop('phone_input', None)
            context.user_data.pop('name_input', None)
            context.user_data.pop('editing_name_field', None)
            context.user_data.pop('email_input', None)

            await self.handle_profile_menu(update, context)
        except Exception as exc:
            await ErrorHandler.handle_booking_error(update, context, 'system_error', 'Failed to cancel edit')

    async def _start_name_edit(
        self,
        update: Update,
        context: ContextTypes.DEFAULT_TYPE,
        *,
        field: str,
        icon: str,
        label: str,
    ) -> None:
        query = update.callback_query
        user_id = query.from_user.id

        session = get_session_state(context)
        session.profile.name_input = ''
        session.profile.editing_name_field = field
        context.user_data['name_input'] = ''
        context.user_data['editing_name_field'] = field

        user_profile = self.deps.user_manager.get_user(user_id) or {}
        current_value = user_profile.get(field, '')

        message = (
            f"{icon} **Edit {label}**\n\n"
            f"Current: {current_value if current_value else 'Not set'}\n\n"
            f"{label}: \\_\n\n"
            "Use the keyboard below:"
        )
        reply_markup = TelegramUI.create_letter_keyboard()
        await query.edit_message_text(
            message,
            parse_mode='Markdown',
            reply_markup=reply_markup,
        )

    async def _start_contact_edit(
        self,
        update: Update,
        context: ContextTypes.DEFAULT_TYPE,
        *,
        field: str,
        session_attr: str,
        context_key: str,
        icon: str,
        label: str,
        message_builder: Callable[[str], str],
        keyboard_factory: Callable[[], Any],
    ) -> None:
        query = update.callback_query
        user_id = query.from_user.id

        session = get_session_state(context)
        session.profile.editing_field = field
        setattr(session.profile, session_attr, '')
        context.user_data['editing_field'] = field
        context.user_data[context_key] = ''

        profile = self.deps.user_manager.get_user(user_id) or {}
        current_value = profile.get(field, '')

        message = message_builder(current_value)
        reply_markup = keyboard_factory()
        await query.edit_message_text(
            message,
            parse_mode='Markdown',
            reply_markup=reply_markup,
        )

    async def handle_phone_keypad(self, update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
        t('botapp.handlers.profile.handler.ProfileHandler.handle_phone_keypad')
        query = update.callback_query
        callback_data = query.data

        try:
            session = get_session_state(context)
            if session.profile.editing_field != 'phone':
                await query.answer("❌ Not in phone editing mode")
                return

            phone_input = session.profile.phone_input

            if callback_data.startswith('phone_digit_'):
                digit = callback_data.replace('phone_digit_', '')
                if len(phone_input) < 8:
                    phone_input += digit
                else:
                    await query.answer("❌ Phone number must be 8 digits")
                    return
            elif callback_data == 'phone_delete':
                phone_input = phone_input[:-1]
            elif callback_data == 'phone_done':
                if len(phone_input) != 8:
                    await query.answer("❌ Phone number must be exactly 8 digits")
                    return

                full_phone = f"+502 {phone_input}"
                profile = self.deps.user_manager.get_user(query.from_user.id) or {'user_id': query.from_user.id}
                profile['phone'] = phone_input
                self.deps.user_manager.save_user(profile)

                session.profile.editing_field = None
                session.profile.phone_input = ''
                context.user_data.pop('phone_input', None)
                context.user_data.pop('editing_field', None)

                await query.edit_message_text(
                    f"✅ Phone number updated to {full_phone}",
                    reply_markup=TelegramUI.create_back_to_menu_keyboard(),
                )
                return

            session.profile.phone_input = phone_input
            context.user_data['phone_input'] = phone_input

            message = (
                "📱 **Edit Phone Number**\n\n"
                f"(+502) {phone_input}\n\n"
                "Use the keypad below to continue:"
            )
            reply_markup = TelegramUI.create_phone_keypad(current=phone_input)

            await query.edit_message_text(
                message,
                parse_mode='Markdown',
                reply_markup=reply_markup,
            )
            await query.answer()
        except Exception as exc:
            self.logger.error("Error updating phone: %s", exc)
            await ErrorHandler.handle_booking_error(update, context, 'system_error', 'Failed to process phone input')

    async def handle_name_callbacks(self, update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
        t('botapp.handlers.profile.handler.ProfileHandler.handle_name_callbacks')
        query = update.callback_query
        callback_data = query.data
        user_id = query.from_user.id

        try:
            session = get_session_state(context)
            editing_field = session.profile.editing_name_field or context.user_data.get('editing_name_field', 'first_name')

            if callback_data == 'name_use_telegram':
                user = query.from_user
                first_name = user.first_name or ''
                last_name = user.last_name or ''
                profile = self.deps.user_manager.get_user(user_id) or {'user_id': user_id}
                profile['first_name'] = first_name
                profile['last_name'] = last_name
                self.deps.user_manager.save_user(profile)

                await query.answer("✅ Name updated from Telegram!")
                await self.handle_edit_name(update, context)
                return

            if callback_data.startswith('letter_'):
                await self.handle_letter_input(update, context)
                return

            await query.answer()
        except Exception as exc:
            self.logger.error("Error handling name callback: %s", exc)
            await ErrorHandler.handle_booking_error(update, context, 'system_error', 'Failed to process name edit')

    async def handle_letter_input(self, update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
        t('botapp.handlers.profile.handler.ProfileHandler.handle_letter_input')
        query = update.callback_query
        callback_data = query.data
        user_id = query.from_user.id

        session = get_session_state(context)
        name_input = session.profile.name_input
        editing_field = session.profile.editing_name_field or context.user_data.get('editing_name_field', 'first_name')

        if callback_data == 'letter_delete':
            name_input = name_input[:-1]
        elif callback_data == 'letter_done':
            if not name_input:
                await query.answer("❌ Please enter a name")
                return

            profile = self.deps.user_manager.get_user(user_id) or {'user_id': user_id}
            profile[editing_field] = name_input
            self.deps.user_manager.save_user(profile)

            session.profile.name_input = ''
            session.profile.editing_name_field = None
            context.user_data.pop('name_input', None)
            context.user_data.pop('editing_name_field', None)

            await query.answer(f"✅ {editing_field.replace('_', ' ').title()} updated!")
            await self.handle_edit_name(update, context)
            return
        else:
            if callback_data == 'letter_apostrophe':
                letter = "'"
            else:
                letter = callback_data.replace('letter_', '')

            if len(name_input) < 20:
                name_input += letter
            else:
                await query.answer("❌ Name too long")
                return

        session.profile.name_input = name_input
        context.user_data['name_input'] = name_input

        field_display = "First Name" if editing_field == 'first_name' else "Last Name"
        emoji = "👤" if editing_field == 'first_name' else "👥"
        message = (
            f"{emoji} **Edit {field_display}**\n\n"
            f"{field_display}: {name_input}\\_\n\n"
            "Use the keyboard below:"
        )
        reply_markup = TelegramUI.create_letter_keyboard()

        await query.edit_message_text(message, parse_mode='Markdown', reply_markup=reply_markup)
        await query.answer()

    async def handle_email_callbacks(self, update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
        t('botapp.handlers.profile.handler.ProfileHandler.handle_email_callbacks')
        query = update.callback_query
        callback_data = query.data
        user_id = query.from_user.id

        try:
            session = get_session_state(context)
            email_input = session.profile.email_input

            if callback_data.startswith('email_char_'):
                char = callback_data.replace('email_char_', '')
                if len(email_input) < 50:
                    email_input += char
                    session.profile.email_input = email_input
                    context.user_data['email_input'] = email_input
                else:
                    await query.answer("❌ Email too long")
                    return
            elif callback_data == 'email_delete':
                if email_input:
                    email_input = email_input[:-1]
                    session.profile.email_input = email_input
                    context.user_data['email_input'] = email_input
            elif callback_data == 'email_done':
                if '@' not in email_input:
                    await query.answer("❌ Email must contain @")
                    return

                message = (
                    f"📧 **Confirm Email**\n\nEmail: {email_input}\n\nIs this correct?"
                )
                reply_markup = TelegramUI.create_email_confirm_keyboard(email_input)

                await query.edit_message_text(
                    message,
                    parse_mode='Markdown',
                    reply_markup=reply_markup,
                )
                return
            elif callback_data.startswith('email_confirm_'):
                confirmed_email = callback_data.replace('email_confirm_', '')
                profile = self.deps.user_manager.get_user(user_id) or {'user_id': user_id}
                profile['email'] = confirmed_email
                self.deps.user_manager.save_user(profile)

                session.profile.email_input = ''
                session.profile.editing_field = None
                context.user_data.pop('email_input', None)

                await query.answer("✅ Email updated!")
                await self.handle_profile_menu(update, context)
                return

            message = (
                "📧 **Edit Email**\n\n"
                f"Email: {email_input}\\_\n\n"
                "Use the keyboard below:"
            )
            reply_markup = TelegramUI.create_email_char_keyboard()
            await query.edit_message_text(
                message,
                parse_mode='Markdown',
                reply_markup=reply_markup,
            )
            await query.answer()
        except Exception as exc:
            self.logger.error("Error handling email callback: %s", exc)
            await ErrorHandler.handle_booking_error(update, context, 'system_error', 'Failed to process email edit')
