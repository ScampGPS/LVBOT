"""Profile management callbacks."""

from __future__ import annotations
from tracking import t

from typing import Any, Callable

from telegram import InlineKeyboardButton, InlineKeyboardMarkup, Update
from telegram.ext import ContextTypes

from botapp.handlers.dependencies import CallbackDependencies
from botapp.handlers.state import get_session_state
from botapp.i18n import get_user_translator
from botapp.ui.telegram_ui import TelegramUI
from botapp.error_handler import ErrorHandler


class ProfileHandler:
    """Handles profile viewing and editing callbacks."""

    def __init__(self, deps: CallbackDependencies) -> None:
        t('botapp.handlers.profile.handler.ProfileHandler.__init__')
        self.deps = deps
        self.logger = deps.logger

    async def handle_profile_menu(self, update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
        t('botapp.handlers.profile.handler.ProfileHandler.handle_profile_menu')
        query = update.callback_query
        user_id = query.from_user.id

        try:
            user_profile = self.deps.user_manager.get_user(user_id)
            if not user_profile:
                user_profile, _ = self.deps.user_manager.ensure_user_profile(query.from_user)
            tr = get_user_translator(self.deps.user_manager, user_id)

            if not user_profile:
                await query.edit_message_text(
                    "📇 No profile found. Please contact an administrator.",
                    reply_markup=TelegramUI.create_back_to_menu_keyboard(language=tr.get_language()),
                )
                return

            # Use the formatted profile message with compact mode
            message = TelegramUI.format_user_profile_message(user_profile, compact=True)
            keyboard = TelegramUI.create_profile_keyboard(language=tr.get_language(), user_data=user_profile)

            await query.edit_message_text(message, reply_markup=keyboard, parse_mode='Markdown')
        except Exception as exc:  # pragma: no cover - defensive guard
            self.logger.error("Failed to show profile menu: %s", exc)
            await ErrorHandler.handle_booking_error(update, context, 'system_error', 'Failed to load profile')

    async def handle_edit_profile(self, update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
        t('botapp.handlers.profile.handler.ProfileHandler.handle_edit_profile')
        query = update.callback_query
        user_id = query.from_user.id
        try:
            tr = get_user_translator(self.deps.user_manager, user_id)
            keyboard = TelegramUI.create_edit_profile_keyboard(language=tr.get_language())
            message = f"{tr.t('profile.edit_profile_title')}\n\n{tr.t('profile.select_field')}"
            await query.edit_message_text(
                message,
                parse_mode='Markdown',
                reply_markup=keyboard,
            )
        except Exception as exc:
            await ErrorHandler.handle_booking_error(update, context, 'system_error', 'Failed to show edit options')

    async def handle_edit_name(self, update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
        t('botapp.handlers.profile.handler.ProfileHandler.handle_edit_name')
        query = update.callback_query
        user_id = query.from_user.id

        try:
            tr = get_user_translator(self.deps.user_manager, user_id)
            session = get_session_state(context)
            session.profile.name_input = ''
            session.profile.editing_name_field = None
            context.user_data['name_input'] = ''
            context.user_data.pop('editing_name_field', None)

            keyboard = TelegramUI.create_name_type_keyboard()
            message = f"{tr.t('profile.name_editing')}\n\n{tr.t('profile.choose_name_field')}"

            await query.edit_message_text(
                message,
                parse_mode='Markdown',
                reply_markup=keyboard,
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
        query = update.callback_query
        user_id = query.from_user.id
        tr = get_user_translator(self.deps.user_manager, user_id)

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
                    f"{tr.t('profile.edit_phone_title')}\n\n"
                    f"{tr.t('profile.current')}: (+502) {current if current else tr.t('profile.not_set')}\n\n"
                    "(+502) ________\n\n"
                    f"{tr.t('profile.use_keypad')}"
                ),
                keyboard_factory=TelegramUI.create_phone_keypad,
            )
        except Exception as exc:
            await ErrorHandler.handle_booking_error(update, context, 'system_error', 'Failed to show phone edit')

    async def handle_edit_email(self, update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
        t('botapp.handlers.profile.handler.ProfileHandler.handle_edit_email')
        query = update.callback_query
        user_id = query.from_user.id
        tr = get_user_translator(self.deps.user_manager, user_id)

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
                    f"{tr.t('profile.edit_email_title')}\n\n"
                    f"{tr.t('profile.current')}: {current if current else tr.t('profile.not_set')}\n\n"
                    f"{tr.t('profile.email_label')}: \\_\n\n"
                    f"{tr.t('profile.use_keyboard')}"
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
        t('botapp.handlers.profile.handler.ProfileHandler._start_name_edit')
        query = update.callback_query
        user_id = query.from_user.id
        tr = get_user_translator(self.deps.user_manager, user_id)

        session = get_session_state(context)
        session.profile.name_input = ''
        session.profile.editing_name_field = field
        context.user_data['name_input'] = ''
        context.user_data['editing_name_field'] = field

        user_profile = self.deps.user_manager.get_user(user_id) or {}
        current_value = user_profile.get(field, '')

        # Translate the label
        translated_label = tr.t(f'profile.{field}')

        message = (
            f"{icon} {tr.t('profile.edit_field', field=translated_label)}\n\n"
            f"{tr.t('profile.current')}: {current_value if current_value else tr.t('profile.not_set')}\n\n"
            f"{translated_label}: \\_\n\n"
            f"{tr.t('profile.use_keyboard')}"
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
        t('botapp.handlers.profile.handler.ProfileHandler._start_contact_edit')
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
        user_id = query.from_user.id
        tr = get_user_translator(self.deps.user_manager, user_id)

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
                    await query.answer(tr.t('profile.phone_8_digits'))
                    return
            elif callback_data == 'phone_delete':
                phone_input = phone_input[:-1]
            elif callback_data == 'phone_done':
                if len(phone_input) != 8:
                    await query.answer(tr.t('profile.phone_exactly_8'))
                    return

                full_phone = f"+502 {phone_input}"
                profile = self.deps.user_manager.get_user(user_id) or {'user_id': user_id}
                profile['phone'] = phone_input
                self.deps.user_manager.save_user(profile)

                session.profile.editing_field = None
                session.profile.phone_input = ''
                context.user_data.pop('phone_input', None)
                context.user_data.pop('editing_field', None)

                await query.edit_message_text(
                    tr.t('profile.phone_updated', phone=full_phone),
                    reply_markup=TelegramUI.create_back_to_menu_keyboard(),
                )
                return

            session.profile.phone_input = phone_input
            context.user_data['phone_input'] = phone_input

            message = (
                f"{tr.t('profile.edit_phone_title')}\n\n"
                f"(+502) {phone_input}\n\n"
                f"{tr.t('profile.use_keypad')}"
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
        tr = get_user_translator(self.deps.user_manager, user_id)

        try:
            session = get_session_state(context)
            editing_field = session.profile.editing_name_field or context.user_data.get('editing_name_field', 'first_name')

            if callback_data == 'name_use_telegram':
                user = query.from_user
                first_name = user.first_name or ''
                last_name = user.last_name or ''
                profile = self.deps.user_manager.get_user(user_id) or {
                    'user_id': user_id,
                    'language': 'es'  # Default new users to Spanish
                }
                profile['first_name'] = first_name
                profile['last_name'] = last_name
                self.deps.user_manager.save_user(profile)

                await query.answer(tr.t('profile.name_updated_telegram'))
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
        tr = get_user_translator(self.deps.user_manager, user_id)

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

            field_display = tr.t(f'profile.{editing_field}')
            await query.answer(f"✅ {field_display} updated!")
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
                await query.answer(tr.t('profile.name_too_long'))
                return

        session.profile.name_input = name_input
        context.user_data['name_input'] = name_input

        field_display = tr.t(f'profile.{editing_field}')
        emoji = "👤" if editing_field == 'first_name' else "👥"
        message = (
            f"{emoji} {tr.t('profile.edit_field', field=field_display)}\n\n"
            f"{field_display}: {name_input}\\_\n\n"
            f"{tr.t('profile.use_keyboard')}"
        )
        reply_markup = TelegramUI.create_letter_keyboard()

        await query.edit_message_text(message, parse_mode='Markdown', reply_markup=reply_markup)
        await query.answer()

    async def handle_email_callbacks(self, update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
        t('botapp.handlers.profile.handler.ProfileHandler.handle_email_callbacks')
        query = update.callback_query
        callback_data = query.data
        user_id = query.from_user.id
        tr = get_user_translator(self.deps.user_manager, user_id)

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
                    await query.answer(tr.t('profile.email_too_long'))
                    return
            elif callback_data == 'email_delete':
                if email_input:
                    email_input = email_input[:-1]
                    session.profile.email_input = email_input
                    context.user_data['email_input'] = email_input
            elif callback_data == 'email_done':
                if '@' not in email_input:
                    await query.answer(tr.t('profile.email_must_have_at'))
                    return

                message = (
                    f"{tr.t('profile.confirm_email_title')}\n\n"
                    f"{tr.t('profile.email_label')}: {email_input}\n\n"
                    f"{tr.t('profile.is_correct')}"
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

                await query.answer(tr.t('profile.email_updated'))
                await self.handle_profile_menu(update, context)
                return

            message = (
                f"{tr.t('profile.edit_email_title')}\n\n"
                f"{tr.t('profile.email_label')}: {email_input}\\_\n\n"
                f"{tr.t('profile.use_keyboard')}"
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

    async def handle_edit_language(self, update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
        """Show language selection menu."""
        t('botapp.handlers.profile.handler.ProfileHandler.handle_edit_language')
        query = update.callback_query
        user_id = query.from_user.id
        tr = get_user_translator(self.deps.user_manager, user_id)

        try:
            user_profile = self.deps.user_manager.get_user(user_id)
            current_lang = user_profile.get('language', 'es') if user_profile else 'es'
            lang_display = "🇪🇸 Español" if current_lang == 'es' else "🇺🇸 English"

            message = (
                f"{tr.t('profile.language_selection')}\n\n"
                f"{tr.t('profile.current_language')}: {lang_display}\n\n"
                f"{tr.t('profile.select_language')}"
            )

            keyboard = TelegramUI.create_language_selection_keyboard()
            await query.edit_message_text(
                message,
                parse_mode='Markdown',
                reply_markup=keyboard,
            )
        except Exception as exc:
            self.logger.error("Error showing language selection: %s", exc)
            await ErrorHandler.handle_booking_error(update, context, 'system_error', 'Failed to show language options')

    async def handle_language_selection(self, update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
        """Handle language selection callback."""
        t('botapp.handlers.profile.handler.ProfileHandler.handle_language_selection')
        query = update.callback_query
        user_id = query.from_user.id
        callback_data = query.data or ''

        try:
            # Extract language code from callback_data (lang_es or lang_en)
            lang_code = callback_data.replace('lang_', '')

            if lang_code not in ['es', 'en']:
                await query.answer("❌ Invalid language")
                return

            # Update user language preference
            success = self.deps.user_manager.set_user_language(user_id, lang_code)

            if success:
                lang_name = "Español" if lang_code == 'es' else "English"
                await query.answer(f"✅ Language changed to {lang_name}")

                # Show profile menu with updated language
                await self.handle_profile_menu(update, context)
            else:
                await query.answer("❌ Failed to update language")

        except Exception as exc:
            self.logger.error("Error handling language selection: %s", exc)
            await ErrorHandler.handle_booking_error(update, context, 'system_error', 'Failed to change language')

    async def handle_edit_court_preference(self, update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
        """Show court preference editing interface."""
        t('botapp.handlers.profile.handler.ProfileHandler.handle_edit_court_preference')
        query = update.callback_query
        user_id = query.from_user.id

        try:
            user_profile = self.deps.user_manager.get_user(user_id)
            tr = get_user_translator(self.deps.user_manager, user_id)

            if not user_profile:
                await query.answer("❌ Profile not found")
                return

            # Get current court preference or default to empty
            court_pref = user_profile.get('court_preference', []) or []

            # Store in session for editing
            session = get_session_state(context)
            session.profile.court_preference = court_pref.copy()
            context.user_data['editing_court_preference'] = court_pref.copy()

            message = (
                f"🎾 **{tr.t('profile.court_preference')}**\n\n"
                f"{tr.t('profile.court_preference_help', default='Use ⬆️⬇️ to reorder, ❌ to remove, ➕ to add courts.')}\n\n"
                f"{tr.t('profile.court_order_matters', default='The order determines booking priority.')}"
            )

            keyboard = TelegramUI.create_court_preference_keyboard(court_pref, translator=tr)
            await query.edit_message_text(message, parse_mode='Markdown', reply_markup=keyboard)

        except Exception as exc:
            self.logger.error("Error showing court preference editor: %s", exc)
            await ErrorHandler.handle_booking_error(update, context, 'system_error', 'Failed to show court editor')

    async def handle_court_preference_callbacks(self, update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
        """Handle court preference editing callbacks."""
        t('botapp.handlers.profile.handler.ProfileHandler.handle_court_preference_callbacks')
        query = update.callback_query
        user_id = query.from_user.id
        callback_data = query.data or ''

        try:
            session = get_session_state(context)
            court_pref = session.profile.court_preference or context.user_data.get('editing_court_preference', [])
            tr = get_user_translator(self.deps.user_manager, user_id)

            if callback_data.startswith('court_move_up_'):
                index = int(callback_data.replace('court_move_up_', ''))
                if index > 0 and index < len(court_pref):
                    # Swap with previous
                    court_pref[index], court_pref[index - 1] = court_pref[index - 1], court_pref[index]
                    await query.answer("⬆️ Moved up")

            elif callback_data.startswith('court_move_down_'):
                index = int(callback_data.replace('court_move_down_', ''))
                if index >= 0 and index < len(court_pref) - 1:
                    # Swap with next
                    court_pref[index], court_pref[index + 1] = court_pref[index + 1], court_pref[index]
                    await query.answer("⬇️ Moved down")

            elif callback_data.startswith('court_remove_'):
                court_num = int(callback_data.replace('court_remove_', ''))
                if court_num in court_pref:
                    court_pref.remove(court_num)
                    await query.answer("❌ Court removed")

            elif callback_data.startswith('court_add_'):
                court_num = int(callback_data.replace('court_add_', ''))
                if court_num not in court_pref:
                    court_pref.append(court_num)
                    await query.answer("➕ Court added")

            elif callback_data == 'court_pref_done':
                # Save to user profile
                profile = self.deps.user_manager.get_user(user_id) or {'user_id': user_id}
                profile['court_preference'] = court_pref
                self.deps.user_manager.save_user(profile)

                # Clear session
                session.profile.court_preference = None
                context.user_data.pop('editing_court_preference', None)

                await query.answer("✅ Court preference saved!")
                await self.handle_profile_menu(update, context)
                return

            elif callback_data == 'noop':
                # No operation button (spacers)
                await query.answer()
                return

            # Update session
            session.profile.court_preference = court_pref
            context.user_data['editing_court_preference'] = court_pref

            # Refresh display
            message = (
                f"🎾 **{tr.t('profile.court_preference')}**\n\n"
                f"{tr.t('profile.court_preference_help', default='Use ⬆️⬇️ to reorder, ❌ to remove, ➕ to add courts.')}\n\n"
                f"{tr.t('profile.court_order_matters', default='The order determines booking priority.')}"
            )

            keyboard = TelegramUI.create_court_preference_keyboard(court_pref, translator=tr)
            await query.edit_message_text(message, parse_mode='Markdown', reply_markup=keyboard)

        except Exception as exc:
            self.logger.error("Error handling court preference callback: %s", exc)
            await ErrorHandler.handle_booking_error(update, context, 'system_error', 'Failed to update court preference')
