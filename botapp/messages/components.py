"""Reusable message handling components for bot workflows."""

from __future__ import annotations
from tracking import t

import asyncio
import logging
import time
from typing import Any, Dict, List, Optional

from telegram import InlineKeyboardButton, InlineKeyboardMarkup, Message, Update
from telegram.constants import ParseMode
from telegram.error import RetryAfter


class MessageResponder:
    """Low-level helpers for replying/editing Telegram messages."""

    def __init__(self, *, logger: Optional[logging.Logger] = None) -> None:
        t('botapp.messages.components.MessageResponder.__init__')
        self._logger = logger or logging.getLogger('MessageHandlers')

    async def edit_or_reply(self, update: Update, text: str, **kwargs: Any) -> None:
        t('botapp.messages.components.MessageResponder.edit_or_reply')
        if 'parse_mode' not in kwargs:
            kwargs['parse_mode'] = ParseMode.MARKDOWN

        try:
            if update.callback_query:
                message = update.callback_query.message
                if message.text != text or message.reply_markup != kwargs.get('reply_markup'):
                    await update.callback_query.edit_message_text(text, **kwargs)
                else:
                    await update.callback_query.answer()
            elif update.message:
                await update.message.reply_text(text, **kwargs)
        except Exception as exc:
            self._logger.debug("Edit failed, sending new message: %s", exc)
            if update.callback_query:
                await update.callback_query.message.reply_text(text, **kwargs)
            elif update.message:
                await update.message.reply_text(text, **kwargs)

    async def edit_callback_message(
        self,
        callback_query,
        text: str,
        *,
        retries: int = 1,
        retry_padding: float = 0.5,
        logger: Optional[logging.Logger] = None,
        **kwargs: Any,
    ) -> None:
        t('botapp.messages.components.MessageResponder.edit_callback_message')
        attempts = 0
        wait_time = 0.0
        target_logger = logger or self._logger

        while attempts <= retries:
            if wait_time > 0:
                await asyncio.sleep(wait_time)

            try:
                await callback_query.edit_message_text(text, **kwargs)
                return
            except RetryAfter as exc:
                attempts += 1
                if attempts > retries:
                    raise

                wait_time = float(getattr(exc, 'retry_after', 1)) + max(retry_padding, 0)
                target_logger.warning(
                    'Telegram rate limit triggered while editing message; retrying in %.1fs',
                    wait_time,
                )
            except Exception:
                raise

    async def safe_answer(self, callback_query, text: Optional[str] = None, *, show_alert: bool = False) -> None:
        t('botapp.messages.components.MessageResponder.safe_answer')
        try:
            await callback_query.answer(text, show_alert=show_alert)
        except Exception as exc:
            self._logger.debug("Failed to answer callback: %s", exc)


class MessageSender:
    """High-level helpers for sending notifications and confirmations."""

    def __init__(self, responder: MessageResponder) -> None:
        t('botapp.messages.components.MessageSender.__init__')
        self._responder = responder

    async def handle_unauthorized_user(self, update: Update) -> None:
        t('botapp.messages.components.MessageSender.handle_unauthorized_user')
        message = (
            "🔐 You are not authorized to use this bot.\n"
            "Please send /start to request access."
        )

        if update.message:
            await update.message.reply_text(message, parse_mode=ParseMode.MARKDOWN)
        elif update.callback_query:
            await self._responder.safe_answer(
                update.callback_query,
                "Unauthorized! Please send /start first.",
                show_alert=True,
            )

    async def handle_invalid_command(
        self,
        update: Update,
        error_msg: str,
        *,
        help_text: Optional[str] = None,
    ) -> None:
        t('botapp.messages.components.MessageSender.handle_invalid_command')
        msg = f"❌ {error_msg}"
        if help_text:
            msg += f"\n\n💡 {help_text}"

        if update.message:
            await update.message.reply_text(msg, parse_mode=ParseMode.MARKDOWN)
        elif update.callback_query:
            await self._responder.safe_answer(update.callback_query, error_msg, show_alert=True)

    async def send_loading(self, update: Update, text: str = "Processing...") -> Optional[Message]:
        t('botapp.messages.components.MessageSender.send_loading')
        loading_text = f"⏳ {text}"

        if update.message:
            return await update.message.reply_text(loading_text)
        if update.callback_query:
            await update.callback_query.answer(text)
            return update.callback_query.message
        return None

    async def send_error(self, update: Update, error: Exception, *, user_friendly: bool = True) -> None:
        t('botapp.messages.components.MessageSender.send_error')
        if user_friendly:
            message = (
                "❌ An error occurred while processing your request.\n"
                "Please try again later or contact support."
            )
        else:
            message = f"❌ Error: {type(error).__name__}: {error}"

        await self._responder.edit_or_reply(update, message)

    async def confirm_action(
        self,
        update: Update,
        question: str,
        callback_yes: str,
        callback_no: str,
    ) -> None:
        t('botapp.messages.components.MessageSender.confirm_action')
        keyboard = InlineKeyboardMarkup(
            [[
                InlineKeyboardButton("✅ Yes", callback_data=callback_yes),
                InlineKeyboardButton("❌ No", callback_data=callback_no),
            ]]
        )
        await self._responder.edit_or_reply(update, f"❓ {question}", reply_markup=keyboard)


class ChunkedMessageSender:
    """Utility for sending chunked messages within Telegram limits."""

    def __init__(self, *, parse_mode: str = ParseMode.MARKDOWN) -> None:
        t('botapp.messages.components.ChunkedMessageSender.__init__')
        self._parse_mode = parse_mode

    async def send(self, update: Update, text: str, *, chunk_size: int = 4000) -> List[Message]:
        t('botapp.messages.components.ChunkedMessageSender.send')
        messages: List[Message] = []
        chunks = split_message(text, chunk_size)

        for chunk in chunks:
            if update.message:
                msg = await update.message.reply_text(
                    chunk,
                    parse_mode=self._parse_mode,
                    disable_web_page_preview=True,
                )
            elif update.callback_query:
                msg = await update.callback_query.message.reply_text(
                    chunk,
                    parse_mode=self._parse_mode,
                    disable_web_page_preview=True,
                )
            else:
                continue

            messages.append(msg)
            if len(chunks) > 1:
                await asyncio.sleep(0.1)
        return messages


def split_message(text: str, max_length: int = 4000) -> List[str]:
    t('botapp.messages.components.split_message')
    if len(text) <= max_length:
        return [text]

    chunks: List[str] = []
    current_chunk = ""
    paragraphs = text.split('\n\n')

    for paragraph in paragraphs:
        if len(current_chunk) + len(paragraph) + 2 <= max_length:
            if current_chunk:
                current_chunk += "\n\n"
            current_chunk += paragraph
        else:
            if current_chunk:
                chunks.append(current_chunk)
            if len(paragraph) > max_length:
                lines = paragraph.split('\n')
                current_chunk = ""
                for line in lines:
                    if len(current_chunk) + len(line) + 1 <= max_length:
                        if current_chunk:
                            current_chunk += "\n"
                        current_chunk += line
                    else:
                        if current_chunk:
                            chunks.append(current_chunk)
                        current_chunk = line
            else:
                current_chunk = paragraph

    if current_chunk:
        chunks.append(current_chunk)

    return chunks


async def delete_message_safe(message: Message) -> bool:
    t('botapp.messages.components.delete_message_safe')
    try:
        await message.delete()
        return True
    except Exception as exc:
        logging.getLogger('MessageHandlers').debug("Failed to delete message: %s", exc)
        return False


def format_command_list(commands: Dict[str, str], *, is_admin: bool = False) -> str:
    t('botapp.messages.components.format_command_list')
    message = "📋 **Available Commands**\n\n"
    for cmd, desc in commands.items():
        if not cmd.startswith('admin_') or is_admin:
            message += f"/{cmd} - {desc}\n"
    return message + "\n💡 You can also use the menu buttons for easy navigation."


def get_user_info(update: Update) -> Dict[str, Any]:
    t('botapp.messages.components.get_user_info')
    user = update.effective_user
    return {
        'user_id': user.id,
        'first_name': user.first_name or '',
        'last_name': user.last_name or '',
        'username': user.username or '',
        'language_code': user.language_code or 'en',
        'is_bot': user.is_bot,
    }


def rate_limit_check(
    user_id: int,
    action: str,
    *,
    limit_seconds: int = 5,
    storage: Optional[Dict[str, float]] = None,
) -> bool:
    t('botapp.messages.components.rate_limit_check')
    if storage is None:
        return True

    key = f"{user_id}_{action}"
    current_time = time.time()
    previous = storage.get(key)
    if previous is not None and current_time - previous < limit_seconds:
        return False

    storage[key] = current_time
    return True
