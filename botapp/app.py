#!/usr/bin/env python3
"""
Async telegram bot - Full asyncio architecture
"""
from tracking import t

import os
import sys
import logging
import asyncio
import signal
from pathlib import Path

if __name__ == "__main__" and __package__ is None:
    sys.path.append(str(Path(__file__).resolve().parents[1]))
    __package__ = "botapp"

# Import logging configuration to initialize proper logging
from infrastructure import logging_config

# Now do imports
from telegram.ext import Application, CommandHandler, CallbackQueryHandler, MessageHandler, filters
from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import ContextTypes

# Import async components
from automation.browser.async_browser_pool import AsyncBrowserPool
from automation.availability import AvailabilityChecker
from automation.browser.manager import BrowserManager
from reservations.services import ReservationService
from users.manager import UserManager
from .error_handler import ErrorHandler
from .handlers.callback_handlers import CallbackHandler
from .ui.telegram_ui import TelegramUI

# Simple config
# NOTE: Hardcoded per ops request; rotate and update here when token changes.
BOT_TOKEN = "7768823561:AAHxxvzil7lKsdf64ZuDF3Cch2KYoPJx2AY"
PRODUCTION_MODE = os.getenv('PRODUCTION_MODE', 'false').lower() == 'true'  # Opt-in flag; defaults to false for safer debugging


class BotConfig:
    """
    Configuration class for bot and scheduler parameters
    
    Contains all necessary configuration values for the tennis bot
    including booking URLs, timezone settings, and browser pool configuration
    """
    BOOKING_URL = "https://example.com/booking"  # Placeholder, replace with actual booking URL
    TIMEZONE = "America/Guatemala"  # Guatemala timezone
    BROWSER_POOL_SIZE = 3  # Number of concurrent browser instances
    BROWSER_REFRESH_INTERVAL = 180  # Browser refresh interval in seconds (3 minutes)
    
    # Additional scheduler configuration
    CHECK_INTERVAL = 30  # Queue check interval in seconds
    MAX_RETRY_ATTEMPTS = 3  # Maximum retry attempts for failed bookings
    BOOKING_WINDOW_HOURS = 48  # Booking window in hours
    
    # Additional attributes for scheduler compatibility
    browser_refresh_interval = BROWSER_REFRESH_INTERVAL
    timezone = TIMEZONE


class CleanBot:
    """Minimal clean bot with async browser components"""
    
    def __init__(self, token):
        t('botapp.app.CleanBot.__init__')
        self.token = token
        self.logger = logging.getLogger('CleanBot')
        self.config = BotConfig()
        self.browser_pool = AsyncBrowserPool()
        self.browser_manager = BrowserManager(pool=self.browser_pool)
        self.availability_checker = AvailabilityChecker(self.browser_pool)
        self.user_manager = UserManager('data/users.json')
        self.reservation_service = ReservationService(
            config=self.config,
            notification_callback=self.send_notification,
            user_manager=self.user_manager,
            browser_pool=self.browser_pool,
        )
        self.reservation_queue = self.reservation_service.queue
        self.scheduler = self.reservation_service.scheduler
        self.callback_handler = CallbackHandler(
            self.availability_checker,
            self.reservation_queue,
            self.user_manager,
            self.browser_pool,
        )
        # Attributes preserved for backward compatibility
        self.queue = self.reservation_queue
        self.user_db = self.user_manager
    
    async def start_command(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """Handle /start command"""
        t('botapp.app.CleanBot.start_command')
        # Check if user is admin
        user_id = update.effective_user.id
        is_admin = self.user_manager.is_admin(user_id)
        
        # Get user tier
        tier = self.user_manager.get_user_tier(user_id)
        tier_badge = TelegramUI.format_user_tier_badge(tier.name)
        
        # Use the existing main menu from TelegramUI
        reply_markup = TelegramUI.create_main_menu_keyboard(is_admin=is_admin)
        
        await update.message.reply_text(
            f"🎾 Welcome to LVBot! {tier_badge}\n\nChoose an option:",
            reply_markup=reply_markup
        )
    
    async def stop_command(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """Handle /stop command for graceful shutdown (admin only)"""
        t('botapp.app.CleanBot.stop_command')
        user_id = update.effective_user.id
        
        # Check if user is admin
        if not self.user_manager.is_admin(user_id):
            await update.message.reply_text("❌ Only administrators can stop the bot.")
            return
        
        try:
            # Send confirmation
            await update.message.reply_text(
                "🛑 **Shutting down bot gracefully...**\n\n"
                "This will:\n"
                "• Complete any ongoing bookings\n"
                "• Save all data\n"
                "• Close browser connections properly\n\n"
                "Please wait...",
                parse_mode='Markdown'
            )
            
            # Log shutdown request
            self.logger.info(f"Graceful shutdown requested by admin user {user_id}")
            
            # Schedule graceful shutdown
            asyncio.create_task(self._graceful_shutdown())
            
        except Exception as e:
            self.logger.error(f"Error in stop command: {e}")
            await update.message.reply_text("❌ Error initiating shutdown.")
    
    async def _graceful_shutdown(self):
        """Perform graceful shutdown"""
        t('botapp.app.CleanBot._graceful_shutdown')
        try:
            # Wait a bit for the stop message to be sent
            await asyncio.sleep(1)
            
            # Stop the application
            if self.application:
                self.logger.info("Initiating graceful shutdown...")
                await self.application.stop()
                self.logger.info("Application stop requested")
                
                # The shutdown will continue in _post_stop
        except Exception as e:
            self.logger.error(f"Error during graceful shutdown: {e}")
    
    async def send_notification(self, user_id: int, message: str) -> None:
        """
        Send notification to a user via Telegram with automatic menu follow-up
        
        Args:
            user_id: Telegram user ID to send notification to
            message: Message content to send
            
        Returns:
            None
        """
        t('botapp.app.CleanBot.send_notification')
        try:
            # Check if we have application context
            if not hasattr(self, 'application') or not self.application:
                self.logger.warning(f"No application context for notification to {user_id}")
                return
                
            # Send actual Telegram message
            await self.application.bot.send_message(
                chat_id=user_id, 
                text=message,
                parse_mode='Markdown'
            )
            self.logger.info(f"Sent notification to {user_id}: {message[:50]}...")
            
            # Check if this is a booking result message (success or failure)
            is_booking_result = (
                ("✅" in message and "Reservation Successful" in message) or  # Success
                ("✅" in message and "booked" in message) or  # Success variant
                ("❌" in message and "Reservation Failed" in message) or  # Failure
                ("❌" in message and "failed" in message.lower()) or  # Failure variant
                ("⚠️" in message and "booking" in message.lower())  # Warning/failure
            )
            
            # If it's a booking result, send the main menu after a delay
            if is_booking_result:
                # Wait 7 seconds for user to read the message
                await asyncio.sleep(7)
                
                # Get user tier for menu
                is_admin = self.user_manager.is_admin(user_id)
                tier = self.user_manager.get_user_tier(user_id)
                tier_badge = TelegramUI.format_user_tier_badge(tier.name)
                
                # Send main menu
                reply_markup = TelegramUI.create_main_menu_keyboard(is_admin=is_admin)
                await self.application.bot.send_message(
                    chat_id=user_id,
                    text=f"🎾 What would you like to do next? {tier_badge}",
                    reply_markup=reply_markup
                )
                self.logger.info(f"Sent main menu to {user_id} after booking result")
                
        except Exception as e:
            self.logger.error(f"Failed to send notification to {user_id}: {e}")
    
    # REMOVED: send_notification_sync method that was causing event loop conflicts
    # The scheduler now properly uses the async send_notification method directly
    
    async def check_courts_command(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """Handle /check_courts command - demonstrate async availability checking"""
        t('botapp.app.CleanBot.check_courts_command')
        from .ui.telegram_ui import TelegramUI
        from .messages.message_handlers import MessageHandlers
        from datetime import datetime
        
        try:
            # Send initial message
            await update.message.reply_text("🔍 Checking court availability, please wait...")
            
            # Check all courts in parallel
            results = await self.availability_checker.check_all_courts_parallel()
            
            # Convert results to format expected by TelegramUI
            # Results come as Dict[int, List[TimeSlot]], need Dict[int, List[str]]
            formatted_times = {}
            for court_num, slots in results.items():
                if slots:
                    formatted_times[court_num] = [f"{slot.start_time} - {slot.end_time}" for slot in slots]
            
            # Use existing formatter
            message = TelegramUI.format_availability_message(
                formatted_times, 
                datetime.now(),
                show_summary=True
            )
            
            # Send results
            await update.message.reply_text(message, parse_mode='Markdown')
            
        except Exception as e:
            self.logger.error(f"Error checking courts: {e}")
            # Use existing error handler
            await MessageHandlers.handle_invalid_command(
                update,
                "Failed to check court availability",
                "Please try again with /check_courts"
            )
    
    async def error_handler(self, update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
        """
        Global error handler for the Telegram bot
        
        Handles all unhandled exceptions that occur during update processing
        using the centralized ErrorHandler system.
        
        Args:
            update: The telegram update that caused the error
            context: The callback context (contains the error in context.error)
            
        Returns:
            None
        """
        t('botapp.app.CleanBot.error_handler')
        # Extract the actual error from context
        error = context.error
        
        # Use centralized error handler
        await ErrorHandler.handle_telegram_error(update, context, error)
    
    async def log_bot_metrics(self) -> None:
        """
        Collect and log key bot metrics for monitoring purposes
        
        Gathers metrics from various bot components including user count,
        reservation queue size, and scheduler statistics for operational insights.
        
        Returns:
            None
        """
        t('botapp.app.CleanBot.log_bot_metrics')
        try:
            # Collect user metrics
            all_users = self.user_manager.get_all_users()
            total_users = len(all_users)
            active_users = len([user for user in all_users.values() if user.get('is_active', False)])
            admin_users = len([user for user in all_users.values() if user.get('is_admin', False)])
            
            # Collect reservation queue metrics
            try:
                # Check if reservation_queue has get_all_reservations method
                if hasattr(self.reservation_queue, 'get_all_reservations'):
                    all_reservations = self.reservation_queue.get_all_reservations()
                    queue_size = len(all_reservations)
                    pending_reservations = len([r for r in all_reservations if r.get('status') == 'pending'])
                else:
                    # Fallback if method doesn't exist
                    queue_size = 0
                    pending_reservations = 0
                    self.logger.debug("ReservationQueue.get_all_reservations method not available")
            except Exception as e:
                queue_size = 0
                pending_reservations = 0
                self.logger.debug(f"Could not get reservation queue metrics: {e}")
            
            # Collect scheduler metrics
            try:
                # Check if scheduler has stats attribute
                if hasattr(self.scheduler, 'stats'):
                    successful_bookings = self.scheduler.stats.get('successful_bookings', 0)
                    failed_bookings = self.scheduler.stats.get('failed_bookings', 0)
                    total_booking_attempts = successful_bookings + failed_bookings
                    success_rate = (successful_bookings / total_booking_attempts * 100) if total_booking_attempts > 0 else 0
                else:
                    successful_bookings = 0
                    failed_bookings = 0
                    success_rate = 0
                    self.logger.debug("ReservationScheduler.stats not available")
            except Exception as e:
                successful_bookings = 0
                failed_bookings = 0
                success_rate = 0
                self.logger.debug(f"Could not get scheduler metrics: {e}")
            
            # Log metrics in structured format
            self.logger.info(
                "=== BOT METRICS REPORT ===\n"
                f"👥 User Metrics:\n"
                f"   Total Users: {total_users}\n"
                f"   Active Users: {active_users}\n"
                f"   Admin Users: {admin_users}\n"
                f"📋 Queue Metrics:\n"
                f"   Total Reservations: {queue_size}\n"
                f"   Pending Reservations: {pending_reservations}\n"
                f"🤖 Scheduler Metrics:\n"
                f"   Successful Bookings: {successful_bookings}\n"
                f"   Failed Bookings: {failed_bookings}\n"
                f"   Success Rate: {success_rate:.1f}%\n"
                "=========================="
            )
            
        except Exception as e:
            self.logger.error(f"Error collecting bot metrics: {e}", exc_info=True)
    
    async def _metrics_loop(self) -> None:
        """
        Periodic metrics logging loop
        
        Runs continuously, logging bot metrics every 5 minutes until cancelled.
        Handles task cancellation gracefully.
        
        Returns:
            None
        """
        t('botapp.app.CleanBot._metrics_loop')
        try:
            while True:
                await self.log_bot_metrics()
                await asyncio.sleep(300)  # 5 minutes
        except asyncio.CancelledError:
            self.logger.info("Metrics logging task cancelled")
            raise
        except Exception as e:
            self.logger.error(f"Error in metrics loop: {e}", exc_info=True)
    
    def run(self):
        """Run bot with full async architecture - synchronous entry point"""
        t('botapp.app.CleanBot.run')
        # Create application with specific configuration to prevent polling conflicts
        app = Application.builder().token(self.token).build()
        
        # Add handlers
        app.add_handler(CommandHandler("start", self.start_command))
        app.add_handler(CommandHandler("check_courts", self.check_courts_command))
        app.add_handler(CommandHandler("stop", self.stop_command))
        app.add_handler(CallbackQueryHandler(self.callback_handler.handle_callback))
        
        # Add global error handler
        app.add_error_handler(self.error_handler)
        
        # Use post_init callback to initialize async components
        app.post_init = self._post_init
        app.post_stop = self._post_stop
        
        # Store application reference for proper cleanup
        self.application = app
        
        self.logger.info("Starting async bot...")
        
        # Run polling with minimal configuration to avoid conflicts
        app.run_polling()
    
    async def _post_init(self, application):
        """Initialize async components after app starts"""
        t('botapp.app.CleanBot._post_init')
        # Store application reference for notifications
        self.application = application
        
        # Initialize browser pool - CRITICAL for tennis automation
        try:
            await self.browser_manager.start_pool(self.logger)
        except Exception as e:
            self.logger.error(f"CRITICAL: Browser pool failed to start - bot functionality limited: {e}")
            # Continue running but log the issue
        
        # Start the reservation scheduler in the main event loop
        self.scheduler_task = asyncio.create_task(self.scheduler.run_async())
        self.logger.info("Reservation scheduler task created in main event loop")
        
        # Start periodic metrics logging
        self.monitoring_task = asyncio.create_task(self._metrics_loop())
        self.logger.info("Metrics monitoring started (5-minute intervals)")
        
        # Log initial metrics
        await self.log_bot_metrics()
        
        self.logger.info("Bot started successfully - awaiting messages...")
        self.logger.info("Browser pool should be initialized")
    
    async def _post_stop(self, application):
        """Clean up async components after app stops"""
        t('botapp.app.CleanBot._post_stop')
        self.logger.info("🔴 Starting bot shutdown sequence...")
        
        # Cancel metrics monitoring task
        if hasattr(self, 'monitoring_task') and self.monitoring_task:
            self.monitoring_task.cancel()
            try:
                await self.monitoring_task
            except asyncio.CancelledError:
                pass
            self.logger.info("✅ Metrics monitoring stopped")
        
        # Stop the reservation scheduler task
        if hasattr(self, 'scheduler_task') and self.scheduler_task:
            self.logger.info("🔄 Stopping reservation scheduler...")
            self.scheduler.running = False  # Signal scheduler to stop
            self.scheduler_task.cancel()
            try:
                await self.scheduler_task
            except asyncio.CancelledError:
                pass
            # Clean up scheduler resources
            await self.scheduler.stop()
            self.logger.info("✅ Reservation scheduler stopped")
        
        # Stop browser pool using lifecycle helper with enhanced logging
        self.logger.info("🔄 Stopping browser pool...")
        try:
            success = await self.browser_manager.stop_pool(self.logger)
            if success:
                self.logger.info("✅ Browser pool cleanup completed")
            else:
                self.logger.warning("⚠️ Browser pool cleanup completed with errors")
        except Exception as e:
            self.logger.error(f"❌ Error during browser pool cleanup: {e}")
        
        self.logger.info("✅ Bot shutdown sequence completed")
    


def cleanup_browser_processes():
    """Force kill all browser processes"""
    t('botapp.app.cleanup_browser_processes')
    import subprocess
    import platform
    
    logger = logging.getLogger('Main')
    system = platform.system()
    
    try:
        force_kill = os.getenv("FORCE_PLAYWRIGHT_KILL") == "1"
        if system == "Windows":
            if force_kill:
                processes = ['chrome.exe', 'chromium.exe', 'msedge.exe']
                for process in processes:
                    try:
                        subprocess.run(
                            ['taskkill', '/F', '/IM', process],
                            capture_output=True,
                            check=False,
                        )
                    except Exception:
                        pass
                logger.info("💥 Force killed browser processes on Windows (forced mode)")
            else:
                logger.info(
                    "Skipping global browser termination on Windows. "
                    "Set FORCE_PLAYWRIGHT_KILL=1 to enable forced cleanup."
                )
        else:
            if force_kill:
                subprocess.run(['pkill', '-9', '-f', 'chromium'], capture_output=True)
                subprocess.run(['pkill', '-9', '-f', 'chrome-linux'], capture_output=True)
                subprocess.run(['pkill', '-9', '-f', 'playwright'], capture_output=True)
                logger.info("💥 Force killed Playwright browser processes on Unix")
            else:
                logger.info(
                    "Skipping Playwright process kill on Unix. "
                    "Set FORCE_PLAYWRIGHT_KILL=1 to enable."
                )
    except Exception as e:
        logger.warning(f"Could not force kill browser processes: {e}")


def signal_handler(signum, frame):
    """Handle SIGINT/SIGTERM signals for graceful shutdown"""
    t('botapp.app.signal_handler')
    logger = logging.getLogger('Main')
    logger.info(f"🚨 Received signal {signum}, initiating graceful shutdown...")
    cleanup_browser_processes()
    exit(0)


def main() -> None:
    """Entry point used by both CLI script and module execution."""
    t('botapp.app.main')

    import signal
    import atexit

    logger = logging.getLogger('Main')
    logger.info("=" * 50)
    logger.info("Async Telegram Bot - Full AsyncIO Architecture")
    logger.info("=" * 50)

    # Set up signal handlers for graceful shutdown
    signal.signal(signal.SIGINT, signal_handler)
    signal.signal(signal.SIGTERM, signal_handler)

    # Register cleanup function to run at exit
    atexit.register(cleanup_browser_processes)

    bot = CleanBot(BOT_TOKEN)

    # Kill any orphaned Chromium processes from previous runs
    logger.info("🔄 Cleaning up orphaned browser processes...")
    cleanup_browser_processes()

    # Run the bot directly, letting app.run_polling() manage the event loop
    # No asyncio.run() here, as app.run_polling() handles it
    try:
        logger.info("🚀 Starting bot...")
        bot.run()  # This will call app.run_polling() internally
    except KeyboardInterrupt:
        logger.info("✅ Stopped by user (Ctrl+C)")
    except Exception as e:
        logger.error(f"❌ Error: {e}", exc_info=True)
    finally:
        # Ensure cleanup even on abnormal exit
        logger.info("🔄 Final cleanup...")
        cleanup_browser_processes()


if __name__ == '__main__':
    main()
