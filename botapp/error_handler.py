"""
Centralized Error Handling System for Tennis Bot
Provides robust, user-friendly error handling across all bot operations
"""
from tracking import t

import logging
from typing import Optional
from telegram import Update
from telegram.ext import ContextTypes
from .ui.telegram_ui import TelegramUI


class ErrorHandler:
    """
    Centralized error handling for the tennis bot
    
    Provides static methods for handling different types of errors
    with appropriate user messaging and comprehensive logging
    """
    
    @staticmethod
    async def handle_telegram_error(update: Update, context: ContextTypes.DEFAULT_TYPE, error: Exception) -> None:
        """
        Main entry point for handling errors that occur during Telegram updates
        
        Logs error details and sends a generic, user-friendly error message to the user
        with a fallback navigation option.
        
        Args:
            update: The telegram update that caused the error
            context: The callback context
            error: The exception that occurred
            
        Returns:
            None
        """
        t('botapp.error_handler.ErrorHandler.handle_telegram_error')
        logger = logging.getLogger('ErrorHandler')
        
        # Check for common non-critical errors that shouldn't be logged as errors
        error_message_str = str(error).lower()
        if "message is not modified" in error_message_str:
            # This is a common Telegram error when users click buttons multiple times
            # Log as warning instead of error
            logger.warning(f"Telegram message not modified (user likely clicked button multiple times): {error}")
            return  # Don't send error message to user for this case
        
        # Log comprehensive error details
        logger.error(f"Telegram error occurred: {type(error).__name__}: {error}", exc_info=True)
        
        # Extract user info for logging context
        if update and update.effective_user:
            user_id = update.effective_user.id
            logger.error(f"Error context - User ID: {user_id}")
        
        try:
            # Create fallback navigation
            reply_markup = TelegramUI.create_back_to_menu_keyboard()
            
            # Generic user-friendly error message
            error_message = (
                "❌ **Unexpected Error**\n\n"
                "An unexpected error occurred while processing your request. "
                "This has been logged and will be investigated.\n\n"
                "Please try again later or use the menu to navigate to a different section."
            )
            
            # Check if update exists before trying to access it
            if not update:
                logger.warning("No update object available - cannot send error message to user")
                return
                
            # Try to send error message via callback query if available
            if update.callback_query:
                await update.callback_query.edit_message_text(
                    error_message,
                    parse_mode='Markdown',
                    reply_markup=reply_markup
                )
            # Fallback to regular message if no callback query
            elif update.message:
                await update.message.reply_text(
                    error_message,
                    parse_mode='Markdown',
                    reply_markup=reply_markup
                )
            else:
                logger.warning("Unable to send error message - no callback query or message available")
                
        except Exception as send_error:
            # If we can't even send an error message, log it
            logger.error(f"Failed to send error message to user: {send_error}", exc_info=True)
    
    @staticmethod
    async def handle_booking_error(update: Update, context: ContextTypes.DEFAULT_TYPE, 
                                 error_type: str, details: Optional[str] = None) -> None:
        """
        Handle specific booking-related errors with contextual user messages
        
        Uses TelegramUI formatting for consistent error messaging and provides
        specific guidance based on the error type.
        
        Args:
            update: The telegram update that caused the error
            context: The callback context
            error_type: Type of booking error (e.g., 'court_unavailable', 'invalid_time')
            details: Optional additional error details
            
        Returns:
            None
        """
        t('botapp.error_handler.ErrorHandler.handle_booking_error')
        logger = logging.getLogger('ErrorHandler')
        
        # Log booking error with context
        user_id = update.effective_user.id if update.effective_user else "Unknown"
        logger.warning(f"Booking error - User: {user_id}, Type: {error_type}, Details: {details}")
        
        try:
            # Generate user-friendly error message using TelegramUI
            error_message = TelegramUI.format_error_message(error_type, details)
            
            # Create navigation keyboard
            reply_markup = TelegramUI.create_back_to_menu_keyboard()
            
            # Send error message via callback query if available
            if update.callback_query:
                await update.callback_query.edit_message_text(
                    error_message,
                    reply_markup=reply_markup
                )
            # Fallback to regular message
            elif update.message:
                await update.message.reply_text(
                    error_message,
                    reply_markup=reply_markup
                )
            else:
                logger.warning(f"Unable to send booking error message - no callback query or message available")
                
        except Exception as send_error:
            logger.error(f"Failed to send booking error message: {send_error}", exc_info=True)
            # Fallback to generic error handler
            await ErrorHandler.handle_telegram_error(update, context, send_error)
    
    @staticmethod
    async def handle_user_authorization_error(update: Update, context: ContextTypes.DEFAULT_TYPE, 
                                            operation: str) -> None:
        """
        Handle user authorization errors with security logging
        
        Provides specific messaging for authorization failures and logs
        security-relevant events for monitoring.
        
        Args:
            update: The telegram update that caused the error
            context: The callback context
            operation: The operation that required authorization
            
        Returns:
            None
        """
        t('botapp.error_handler.ErrorHandler.handle_user_authorization_error')
        logger = logging.getLogger('ErrorHandler')
        
        # Log security event
        user_id = update.effective_user.id if update.effective_user else "Unknown"
        logger.warning(f"Authorization failure - User: {user_id}, Operation: {operation}")
        
        try:
            # Create navigation keyboard
            reply_markup = TelegramUI.create_back_to_menu_keyboard()
            
            # Authorization-specific error message
            error_message = (
                "🔐 **Access Denied**\n\n"
                f"You are not authorized to perform this operation: {operation}.\n\n"
                "If you believe this is an error, please contact the system administrator."
            )
            
            # Send error message
            if update.callback_query:
                await update.callback_query.edit_message_text(
                    error_message,
                    parse_mode='Markdown',
                    reply_markup=reply_markup
                )
            elif update.message:
                await update.message.reply_text(
                    error_message,
                    parse_mode='Markdown',
                    reply_markup=reply_markup
                )
                
        except Exception as send_error:
            logger.error(f"Failed to send authorization error message: {send_error}", exc_info=True)
    
    @staticmethod
    async def handle_validation_error(update: Update, context: ContextTypes.DEFAULT_TYPE, 
                                    field: str, value: str, reason: str) -> None:
        """
        Handle input validation errors with specific guidance
        
        Provides clear feedback on validation failures to help users
        correct their input and proceed successfully.
        
        Args:
            update: The telegram update that caused the error
            context: The callback context
            field: The field that failed validation
            value: The invalid value provided
            reason: The reason validation failed
            
        Returns:
            None
        """
        t('botapp.error_handler.ErrorHandler.handle_validation_error')
        logger = logging.getLogger('ErrorHandler')
        
        # Log validation error
        user_id = update.effective_user.id if update.effective_user else "Unknown"
        logger.info(f"Validation error - User: {user_id}, Field: {field}, Value: {value}, Reason: {reason}")
        
        try:
            # Create navigation keyboard
            reply_markup = TelegramUI.create_back_to_menu_keyboard()
            
            # Validation-specific error message
            error_message = (
                f"❌ **Invalid Input**\n\n"
                f"The value '{value}' for {field} is invalid.\n\n"
                f"**Reason**: {reason}\n\n"
                f"Please try again with a valid value."
            )
            
            # Send error message
            if update.callback_query:
                await update.callback_query.edit_message_text(
                    error_message,
                    parse_mode='Markdown',
                    reply_markup=reply_markup
                )
            elif update.message:
                await update.message.reply_text(
                    error_message,
                    parse_mode='Markdown',
                    reply_markup=reply_markup
                )
                
        except Exception as send_error:
            logger.error(f"Failed to send validation error message: {send_error}", exc_info=True)
    
    @staticmethod
    def log_error_context(update: Update, context: ContextTypes.DEFAULT_TYPE, 
                         operation: str, additional_context: Optional[dict] = None) -> None:
        """
        Log comprehensive error context for debugging
        
        Captures relevant context information to aid in debugging
        and error analysis without exposing sensitive data.
        
        Args:
            update: The telegram update
            context: The callback context
            operation: The operation being performed
            additional_context: Optional additional context data
            
        Returns:
            None
        """
        t('botapp.error_handler.ErrorHandler.log_error_context')
        logger = logging.getLogger('ErrorHandler')
        
        # Build context information
        context_info = {
            'operation': operation,
            'user_id': update.effective_user.id if update.effective_user else None,
            'chat_id': update.effective_chat.id if update.effective_chat else None,
            'callback_data': update.callback_query.data if update.callback_query else None,
            'message_text': update.message.text if update.message else None
        }
        
        # Add additional context if provided
        if additional_context:
            context_info.update(additional_context)
        
        # Log context (excluding sensitive data)
        logger.debug(f"Error context: {context_info}")
