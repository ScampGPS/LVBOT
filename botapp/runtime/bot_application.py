"""Telegram bot runtime application wiring."""

from __future__ import annotations
from tracking import t

import asyncio
import logging
from typing import Any, Dict, Optional, Union

from telegram import Update
from telegram.constants import ParseMode
from telegram.ext import Application, ContextTypes

from botapp.bootstrap.container import DependencyContainer
from botapp.commands import register_core_handlers
from botapp.config import BotAppConfig, load_bot_config
from botapp.error_handler import ErrorHandler
from botapp.i18n import get_user_translator
from botapp.notifications import deliver_notification_with_menu
from botapp.runtime.lifecycle import LifecycleManager
from botapp.ui.telegram_ui import TelegramUI


PROFILE_FIELD_LABELS = {
    'first_name': 'profile.first_name',
    'last_name': 'profile.last_name',
    'email': 'profile.email',
    'phone': 'profile.phone',
}


class BotApplication:
    """Assemble dependencies and handlers for the Telegram bot runtime."""

    def __init__(self, config: Optional[BotAppConfig] = None) -> None:
        t('botapp.runtime.bot_application.BotApplication.__init__')
        self.logger = logging.getLogger('CleanBot')
        self.config = config or load_bot_config()
        self.token = self.config.telegram.token
        self.container = DependencyContainer(self.config)
        dependencies = self.container.build_dependencies(self.send_notification)

        self.browser_pool = dependencies.browser_pool
        self.browser_manager = dependencies.browser_manager
        self.availability_checker = dependencies.availability_checker
        self.user_manager = dependencies.user_manager
        self.reservation_service = dependencies.reservation_service
        self.reservation_queue = dependencies.reservation_queue
        self.scheduler = dependencies.scheduler
        self.callback_handler = dependencies.callback_handler
        self.lifecycle = LifecycleManager(dependencies, logger=self.logger)
        self.application = None
        # Backwards-compatible attributes for legacy callers
        self.queue = self.reservation_queue
        self.user_db = self.user_manager

        # Update scheduler with bot handler reference after initialization
        # This enables Telegram notifications for booking results
        self.scheduler.bot = self
        self.logger.info("✅ Scheduler bot handler configured for notifications")

    async def start_command(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """Handle /start command."""
        t('botapp.runtime.bot_application.BotApplication.start_command')

        telegram_user = update.effective_user
        profile, _ = self.user_manager.ensure_user_profile(telegram_user)
        user_id = telegram_user.id
        is_admin = self.user_manager.is_admin(user_id)
        tier = self.user_manager.get_user_tier(user_id)
        tier_badge = TelegramUI.format_user_tier_badge(tier.name)

        # Get user's language preference
        tr = get_user_translator(self.user_manager, user_id)
        reply_markup = TelegramUI.create_main_menu_keyboard(is_admin=is_admin, language=tr.get_language())

        await self._send_message(
            update,
            context,
            f"{tr.t('welcome.title')} {tier_badge}\n\n{tr.t('welcome.message')}",
            reply_markup=reply_markup,
        )

        await self._maybe_prompt_profile_setup(update, context, profile, tr)

    async def stop_command(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """Handle /stop command for graceful shutdown (admin only)."""
        t('botapp.runtime.bot_application.BotApplication.stop_command')

        user_id = update.effective_user.id
        if not self.user_manager.is_admin(user_id):
            await update.message.reply_text("❌ Only administrators can stop the bot.")
            return

        try:
            await update.message.reply_text(
                "🛑 **Shutting down bot gracefully...**\n\n"
                "This will:\n"
                "• Complete any ongoing bookings\n"
                "• Save all data\n"
                "• Close browser connections properly\n\n"
                "Please wait...",
                parse_mode='Markdown',
            )

            self.logger.info("Graceful shutdown requested by admin user %s", user_id)
            asyncio.create_task(self._graceful_shutdown())
        except Exception as exc:  # pragma: no cover - defensive guard
            self.logger.error("Error in stop command: %s", exc)
            await update.message.reply_text("❌ Error initiating shutdown.")

    async def _graceful_shutdown(self) -> None:
        """Request a graceful shutdown."""
        t('botapp.runtime.bot_application.BotApplication._graceful_shutdown')
        await self.lifecycle.graceful_shutdown()

    async def send_notification(self, user_id: int, message: Union[str, Dict[str, Any]]) -> None:
        """Send a Telegram notification with the standard menu follow-up."""
        t('botapp.runtime.bot_application.BotApplication.send_notification')
        try:
            await deliver_notification_with_menu(
                getattr(self, 'application', None),
                self.user_manager,
                user_id,
                message,
                logger=self.logger,
            )
        except Exception as exc:  # pragma: no cover - defensive guard
            self.logger.error("Failed to send notification to %s: %s", user_id, exc)

    async def check_courts_command(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """Handle /check_courts command via availability checker."""
        t('botapp.runtime.bot_application.BotApplication.check_courts_command')

        from datetime import datetime
        from botapp.messages.message_handlers import MessageHandlers

        try:
            await update.message.reply_text("🔍 Checking court availability, please wait...")
            results = await self.availability_checker.check_all_courts_parallel()

            formatted_times = {}
            for court_num, slots in results.items():
                if slots:
                    formatted_times[court_num] = [f"{slot.start_time} - {slot.end_time}" for slot in slots]

            message = TelegramUI.format_availability_message(
                formatted_times,
                datetime.now(),
                show_summary=True,
            )
            await update.message.reply_text(message, parse_mode=ParseMode.MARKDOWN_V2)
        except Exception as exc:  # pragma: no cover - defensive guard
            self.logger.error("Error checking courts: %s", exc)
            await MessageHandlers.handle_invalid_command(
                update,
                "Failed to check court availability",
                "Please try again with /check_courts",
            )

    async def error_handler(self, update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
        """Central error handler for Telegram exceptions."""
        t('botapp.runtime.bot_application.BotApplication.error_handler')
        error = context.error
        await ErrorHandler.handle_telegram_error(update, context, error)

    async def log_bot_metrics(self) -> None:
        """Delegate metrics logging to the lifecycle manager."""
        t('botapp.runtime.bot_application.BotApplication.log_bot_metrics')
        await self.lifecycle.log_metrics()

    def run(self) -> None:
        """Run the Telegram bot using asyncio-ready Application."""
        t('botapp.runtime.bot_application.BotApplication.run')

        app = Application.builder().token(self.token).build()
        register_core_handlers(app, self)

        app.post_init = self._post_init
        app.post_stop = self._post_stop

        self.application = app
        self.logger.info("Starting async bot...")
        app.run_polling()

    async def _post_init(self, application) -> None:
        """Initialize async components after the Telegram app starts."""
        t('botapp.runtime.bot_application.BotApplication._post_init')
        await self.lifecycle.post_init(application)
        self.application = application
        application.bot_data['user_manager'] = self.user_manager

    async def _post_stop(self, application) -> None:
        """Clean up async components after the Telegram app stops."""
        t('botapp.runtime.bot_application.BotApplication._post_stop')
        await self.lifecycle.post_stop(application)
        self.application = None

    async def _send_message(self, update: Update, context: ContextTypes.DEFAULT_TYPE, text: str, **kwargs) -> None:
        """Reply to the current chat, falling back to context.bot when needed."""
        t('botapp.runtime.bot_application.BotApplication._send_message')

        if update.message:
            await update.message.reply_text(text, **kwargs)
            return

        chat = update.effective_chat
        if not chat:
            self.logger.warning("No chat available to deliver message")
            return

        await context.bot.send_message(chat_id=chat.id, text=text, **kwargs)

    async def _maybe_prompt_profile_setup(
        self,
        update: Update,
        context: ContextTypes.DEFAULT_TYPE,
        profile: Dict[str, Any],
        translator,
    ) -> None:
        """Send a profile setup reminder if required fields are missing."""
        t('botapp.runtime.bot_application.BotApplication._maybe_prompt_profile_setup')

        missing_fields = self.user_manager.get_missing_profile_fields(profile)
        if not missing_fields:
            return

        language = translator.get_language()
        label_lookup = PROFILE_FIELD_LABELS
        missing_labels = [translator.t(label_lookup.get(field, field)) for field in missing_fields]
        bullet_list = '\n'.join(f"• {label}" for label in missing_labels)
        message = (
            f"{translator.t('profile.setup_title')}\n\n"
            f"{translator.t('profile.setup_description')}\n\n"
            f"{translator.t('profile.setup_missing')}\n{bullet_list}\n\n"
            f"{translator.t('profile.setup_cta')}"
        )

        keyboard = TelegramUI.create_profile_keyboard(language=language, user_data=profile)
        await self._send_message(
            update,
            context,
            message,
            parse_mode='Markdown',
            reply_markup=keyboard,
        )


__all__ = ['BotApplication']
