"""
Message handling helper functions
Common patterns for handling Telegram messages and updates
"""
from tracking import t

from typing import Optional, Union, List, Dict, Any
from telegram import Update, Message, CallbackQuery
from telegram.constants import ParseMode
from telegram.error import RetryAfter
import logging
import asyncio


class MessageHandlers:
    """Collection of message handling helpers"""
    
    @staticmethod
    async def handle_unauthorized_user(update: Update) -> None:
        """Standard response for unauthorized users"""
        t('botapp.messages.message_handlers.MessageHandlers.handle_unauthorized_user')
        message = (
            "🔐 You are not authorized to use this bot.\n"
            "Please send /start to request access."
        )
        
        if update.message:
            await update.message.reply_text(message, parse_mode=ParseMode.MARKDOWN)
        elif update.callback_query:
            await update.callback_query.answer(
                "Unauthorized! Please send /start first.", 
                show_alert=True
            )
    
    @staticmethod
    async def handle_invalid_command(update: Update, error_msg: str, 
                                   help_text: Optional[str] = None) -> None:
        """Standard response for invalid commands"""
        t('botapp.messages.message_handlers.MessageHandlers.handle_invalid_command')
        msg = f"❌ {error_msg}"
        if help_text:
            msg += f"\n\n💡 {help_text}"
        
        if update.message:
            await update.message.reply_text(msg, parse_mode=ParseMode.MARKDOWN)
        elif update.callback_query:
            await update.callback_query.answer(error_msg, show_alert=True)
    
    @staticmethod
    async def send_loading_message(update: Update, 
                                 text: str = "Processing...") -> Optional[Message]:
        """Send a loading message that can be edited later"""
        t('botapp.messages.message_handlers.MessageHandlers.send_loading_message')
        loading_text = f"⏳ {text}"
        
        if update.message:
            return await update.message.reply_text(loading_text)
        elif update.callback_query:
            await update.callback_query.answer(text)
            return update.callback_query.message
        
        return None
    
    @staticmethod
    async def edit_or_reply(update: Update, text: str, **kwargs) -> None:
        """Edit message if it's a callback query, otherwise reply"""
        t('botapp.messages.message_handlers.MessageHandlers.edit_or_reply')
        # Set default parse mode
        if 'parse_mode' not in kwargs:
            kwargs['parse_mode'] = ParseMode.MARKDOWN

        try:
            if update.callback_query:
                message = update.callback_query.message
                # Check if message content actually changed
                if message.text != text or message.reply_markup != kwargs.get('reply_markup'):
                    await update.callback_query.edit_message_text(text, **kwargs)
                else:
                    # If no change, just acknowledge the callback
                    await update.callback_query.answer()
            else:
                await update.message.reply_text(text, **kwargs)
        except Exception as e:
            # If edit fails, try to send new message
            logging.debug(f"Edit failed, sending new message: {e}")
            if update.callback_query:
                await update.callback_query.message.reply_text(text, **kwargs)
            else:
                await update.message.reply_text(text, **kwargs)

    @staticmethod
    async def edit_callback_message(
        callback_query: CallbackQuery,
        text: str,
        *,
        retries: int = 1,
        retry_padding: float = 0.5,
        logger: Optional[logging.Logger] = None,
        **kwargs: Any,
    ) -> None:
        """Edit a callback message while gracefully handling rate limits."""
        t('botapp.messages.message_handlers.MessageHandlers.edit_callback_message')

        attempts = 0
        wait_time = 0.0
        target_logger = logger or logging.getLogger('MessageHandlers')

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

    @staticmethod
    async def safe_answer_callback(callback_query: CallbackQuery, 
                                 text: Optional[str] = None, 
                                 show_alert: bool = False) -> None:
        """Safely answer a callback query"""
        t('botapp.messages.message_handlers.MessageHandlers.safe_answer_callback')
        try:
            await callback_query.answer(text, show_alert=show_alert)
        except Exception as e:
            logging.debug(f"Failed to answer callback: {e}")
    
    @staticmethod
    async def send_chunked_message(update: Update, text: str, 
                                 chunk_size: int = 4000) -> List[Message]:
        """Send long messages in chunks to avoid Telegram limits"""
        t('botapp.messages.message_handlers.MessageHandlers.send_chunked_message')
        messages = []
        chunks = MessageHandlers.split_message(text, chunk_size)
        
        for chunk in chunks:
            if update.message:
                msg = await update.message.reply_text(
                    chunk, 
                    parse_mode=ParseMode.MARKDOWN,
                    disable_web_page_preview=True
                )
            elif update.callback_query:
                msg = await update.callback_query.message.reply_text(
                    chunk,
                    parse_mode=ParseMode.MARKDOWN,
                    disable_web_page_preview=True
                )
            else:
                continue
            
            messages.append(msg)
            
            # Small delay between messages to avoid rate limits
            if len(chunks) > 1:
                await asyncio.sleep(0.1)
        
        return messages
    
    @staticmethod
    def split_message(text: str, max_length: int = 4000) -> List[str]:
        """Split long message into chunks"""
        t('botapp.messages.message_handlers.MessageHandlers.split_message')
        if len(text) <= max_length:
            return [text]
        
        chunks = []
        current_chunk = ""
        
        # Try to split by paragraphs first
        paragraphs = text.split('\n\n')
        
        for paragraph in paragraphs:
            if len(current_chunk) + len(paragraph) + 2 <= max_length:
                if current_chunk:
                    current_chunk += "\n\n"
                current_chunk += paragraph
            else:
                if current_chunk:
                    chunks.append(current_chunk)
                
                # If paragraph itself is too long, split by lines
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
    
    @staticmethod
    async def delete_message_safe(message: Message) -> bool:
        """Safely delete a message"""
        t('botapp.messages.message_handlers.MessageHandlers.delete_message_safe')
        try:
            await message.delete()
            return True
        except Exception as e:
            logging.debug(f"Failed to delete message: {e}")
            return False
    
    @staticmethod
    async def send_error_message(update: Update, error: Exception, 
                               user_friendly: bool = True) -> None:
        """Send error message to user"""
        t('botapp.messages.message_handlers.MessageHandlers.send_error_message')
        if user_friendly:
            # Don't expose internal errors to users
            message = (
                "❌ An error occurred while processing your request.\n"
                "Please try again later or contact support."
            )
        else:
            # For debugging - only use in development
            message = f"❌ Error: {type(error).__name__}: {str(error)}"
        
        await MessageHandlers.edit_or_reply(update, message)
    
    @staticmethod
    def format_command_list(commands: Dict[str, str], 
                          is_admin: bool = False) -> str:
        """Format command list for help message"""
        t('botapp.messages.message_handlers.MessageHandlers.format_command_list')
        message = "📋 **Available Commands**\n\n"
        
        # Regular commands
        for cmd, desc in commands.items():
            if not cmd.startswith('admin_') or is_admin:
                message += f"/{cmd} - {desc}\n"
        
        message += "\n💡 You can also use the menu buttons for easy navigation."
        
        return message
    
    @staticmethod
    async def confirm_action(update: Update, question: str, 
                           callback_yes: str, callback_no: str) -> None:
        """Ask user to confirm an action"""
        t('botapp.messages.message_handlers.MessageHandlers.confirm_action')
        from telegram import InlineKeyboardButton, InlineKeyboardMarkup
        
        keyboard = InlineKeyboardMarkup([
            [
                InlineKeyboardButton("✅ Yes", callback_data=callback_yes),
                InlineKeyboardButton("❌ No", callback_data=callback_no)
            ]
        ])
        
        await MessageHandlers.edit_or_reply(
            update, 
            f"❓ {question}", 
            reply_markup=keyboard
        )
    
    @staticmethod
    def get_user_info(update: Update) -> Dict[str, Any]:
        """Extract user information from update"""
        t('botapp.messages.message_handlers.MessageHandlers.get_user_info')
        user = update.effective_user
        
        return {
            'user_id': user.id,
            'first_name': user.first_name or '',
            'last_name': user.last_name or '',
            'username': user.username or '',
            'language_code': user.language_code or 'en',
            'is_bot': user.is_bot
        }
    
    @staticmethod
    async def rate_limit_check(user_id: int, action: str, 
                             limit_seconds: int = 5,
                             storage: Dict[str, float] = None) -> bool:
        """
        Check if user is rate limited for an action
        Returns True if action is allowed, False if rate limited
        """
        t('botapp.messages.message_handlers.MessageHandlers.rate_limit_check')
        if storage is None:
            return True  # No storage provided, allow action
        
        import time
        key = f"{user_id}_{action}"
        current_time = time.time()
        
        if key in storage:
            time_passed = current_time - storage[key]
            if time_passed < limit_seconds:
                return False  # Rate limited
        
        storage[key] = current_time
        return True  # Action allowed
