"""
Message handling helper functions
Common patterns for handling Telegram messages and updates
"""
from tracking import t

from typing import Optional, Union, List, Dict, Any
from telegram import Update, Message, CallbackQuery
import logging

from botapp.messages.components import (
    ChunkedMessageSender,
    MessageResponder,
    MessageSender,
    delete_message_safe,
    format_command_list,
    get_user_info,
    rate_limit_check,
    split_message,
)


_responder = MessageResponder()
_sender = MessageSender(_responder)
_chunker = ChunkedMessageSender()


class MessageHandlers:
    """Collection of message handling helpers"""
    
    @staticmethod
    async def handle_unauthorized_user(update: Update) -> None:
        """Standard response for unauthorized users"""
        t('botapp.messages.message_handlers.MessageHandlers.handle_unauthorized_user')
        await _sender.handle_unauthorized_user(update)
    
    @staticmethod
    async def handle_invalid_command(update: Update, error_msg: str, 
                                   help_text: Optional[str] = None) -> None:
        """Standard response for invalid commands"""
        t('botapp.messages.message_handlers.MessageHandlers.handle_invalid_command')
        await _sender.handle_invalid_command(update, error_msg, help_text=help_text)
    
    @staticmethod
    async def send_loading_message(update: Update, 
                                 text: str = "Processing...") -> Optional[Message]:
        """Send a loading message that can be edited later"""
        t('botapp.messages.message_handlers.MessageHandlers.send_loading_message')
        return await _sender.send_loading(update, text)
    
    @staticmethod
    async def edit_or_reply(update: Update, text: str, **kwargs) -> None:
        """Edit message if it's a callback query, otherwise reply"""
        t('botapp.messages.message_handlers.MessageHandlers.edit_or_reply')
        await _responder.edit_or_reply(update, text, **kwargs)

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
        target_logger = logger or logging.getLogger('MessageHandlers')
        await _responder.edit_callback_message(
            callback_query,
            text,
            retries=retries,
            retry_padding=retry_padding,
            logger=target_logger,
            **kwargs,
        )

    @staticmethod
    async def safe_answer_callback(callback_query: CallbackQuery, 
                                 text: Optional[str] = None, 
                                 show_alert: bool = False) -> None:
        """Safely answer a callback query"""
        t('botapp.messages.message_handlers.MessageHandlers.safe_answer_callback')
        await _responder.safe_answer(callback_query, text, show_alert=show_alert)
    
    @staticmethod
    async def send_chunked_message(update: Update, text: str, 
                                 chunk_size: int = 4000) -> List[Message]:
        """Send long messages in chunks to avoid Telegram limits"""
        t('botapp.messages.message_handlers.MessageHandlers.send_chunked_message')
        return await _chunker.send(update, text, chunk_size=chunk_size)
    
    @staticmethod
    def split_message(text: str, max_length: int = 4000) -> List[str]:
        """Split long message into chunks"""
        t('botapp.messages.message_handlers.MessageHandlers.split_message')
        return split_message(text, max_length)
    
    @staticmethod
    async def delete_message_safe(message: Message) -> bool:
        """Safely delete a message"""
        t('botapp.messages.message_handlers.MessageHandlers.delete_message_safe')
        return await delete_message_safe(message)
    
    @staticmethod
    async def send_error_message(update: Update, error: Exception, 
                               user_friendly: bool = True) -> None:
        """Send error message to user"""
        t('botapp.messages.message_handlers.MessageHandlers.send_error_message')
        await _sender.send_error(update, error, user_friendly=user_friendly)
    
    @staticmethod
    def format_command_list(commands: Dict[str, str], 
                          is_admin: bool = False) -> str:
        """Format command list for help message"""
        t('botapp.messages.message_handlers.MessageHandlers.format_command_list')
        return format_command_list(commands, is_admin=is_admin)
    
    @staticmethod
    async def confirm_action(update: Update, question: str, 
                           callback_yes: str, callback_no: str) -> None:
        """Ask user to confirm an action"""
        t('botapp.messages.message_handlers.MessageHandlers.confirm_action')
        await _sender.confirm_action(update, question, callback_yes, callback_no)
    
    @staticmethod
    def get_user_info(update: Update) -> Dict[str, Any]:
        """Extract user information from update"""
        t('botapp.messages.message_handlers.MessageHandlers.get_user_info')
        return get_user_info(update)
    
    @staticmethod
    async def rate_limit_check(user_id: int, action: str, 
                             limit_seconds: int = 5,
                             storage: Dict[str, float] = None) -> bool:
        """
        Check if user is rate limited for an action
        Returns True if action is allowed, False if rate limited
        """
        t('botapp.messages.message_handlers.MessageHandlers.rate_limit_check')
        return rate_limit_check(
            user_id,
            action,
            limit_seconds=limit_seconds,
            storage=storage,
        )
