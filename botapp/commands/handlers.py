"""Utilities to register Telegram command and callback handlers."""

from __future__ import annotations
from tracking import t

from telegram.ext import CallbackQueryHandler, CommandHandler
from telegram.ext import Application


def register_core_handlers(application: Application, bot) -> None:
    """Wire up the bot's core command, callback, and error handlers."""

    t('botapp.commands.handlers.register_core_handlers')

    application.add_handler(CommandHandler("start", bot.start_command))
    application.add_handler(CommandHandler("check_courts", bot.check_courts_command))
    application.add_handler(CommandHandler("stop", bot.stop_command))
    application.add_handler(CallbackQueryHandler(bot.callback_handler.handle_callback))
    application.add_error_handler(bot.error_handler)


__all__ = ['register_core_handlers']
