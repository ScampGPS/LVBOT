#!/usr/bin/env python3
"""
Test script to simulate Telegram button clicks for booking
Tests the "Book Now" (within 48h) functionality
"""

import asyncio
import logging
from datetime import datetime, timedelta
from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup, CallbackQuery, User, Chat, Message
from telegram.ext import Application, CallbackContext
import sys
import os

# Add parent directory to path
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

# Import bot components
from telegram_tennis_bot import CleanBot
from lvbot.utils.user_manager import UserManager
from lvbot.utils.reservation_queue import ReservationQueue
from booking_orchestrator import BookingOrchestrator
from automation.executors.priority_manager import PriorityManager
from immediate_booking_handler import ImmediateBookingHandler

# Setup logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    datefmt='%H:%M:%S'
)

class MockUpdate:
    """Mock Telegram Update object for testing"""
    def __init__(self, user_id: int, user_name: str, callback_data: str = None, message_text: str = None):
        self.callback_query = None
        self.message = None
        
        # Create mock user
        self.mock_user = type('User', (), {
            'id': user_id,
            'first_name': user_name,
            'username': user_name.lower(),
            'is_bot': False
        })()
        
        # Create mock chat
        self.mock_chat = type('Chat', (), {
            'id': user_id,
            'type': 'private'
        })()
        
        if callback_data:
            # Create callback query for button clicks
            self.callback_query = type('CallbackQuery', (), {
                'id': '12345',
                'from_user': self.mock_user,
                'data': callback_data,
                'message': type('Message', (), {
                    'chat': self.mock_chat,
                    'message_id': 100,
                    'date': datetime.now(),
                    'edit_text': self._create_async_edit_text(),
                    'reply_text': self._create_async_reply_text(),
                    'delete': self._create_async_delete()
                })(),
                'answer': self._create_async_answer()
            })()
        
        if message_text:
            # Create regular message
            self.message = type('Message', (), {
                'chat': self.mock_chat,
                'from_user': self.mock_user,
                'text': message_text,
                'message_id': 100,
                'date': datetime.now(),
                'reply_text': self._create_async_reply_text()
            })()
    
    def _create_async_edit_text(self):
        async def edit_text(*args, **kwargs):
            print(f"[EDIT MESSAGE] {args[0] if args else kwargs.get('text', '')}")
            if 'reply_markup' in kwargs and kwargs['reply_markup']:
                print("[BUTTONS SHOWN]")
                for row in kwargs['reply_markup'].inline_keyboard:
                    for button in row:
                        print(f"  - {button.text} (callback: {button.callback_data})")
        return edit_text
    
    def _create_async_reply_text(self):
        async def reply_text(*args, **kwargs):
            print(f"[REPLY] {args[0] if args else kwargs.get('text', '')}")
            if 'reply_markup' in kwargs and kwargs['reply_markup']:
                print("[BUTTONS SHOWN]")
                for row in kwargs['reply_markup'].inline_keyboard:
                    for button in row:
                        print(f"  - {button.text} (callback: {button.callback_data})")
        return reply_text
    
    def _create_async_delete(self):
        async def delete():
            print("[MESSAGE DELETED]")
        return delete
    
    def _create_async_answer(self):
        async def answer(*args, **kwargs):
            print(f"[CALLBACK ANSWER] {args[0] if args else ''}")
        return answer

class TestTelegramBooking:
    """Test harness for Telegram booking functionality"""
    
    def __init__(self):
        self.logger = logging.getLogger('TestTelegramBooking')
        self.bot = None
        self.user_id = 125763357  # Saul's user ID
        self.user_name = "Saul"
        
    async def setup_bot(self):
        """Initialize the bot with test configuration"""
        self.logger.info("Setting up test bot...")
        
        # Create bot instance
        self.bot = CleanBot()
        
        # Initialize components
        await self.bot.initialize()
        
        # Start browser pool
        await self.bot.start_pool()
        
        self.logger.info("Bot setup complete")
        
    async def simulate_button_click(self, callback_data: str):
        """Simulate a button click"""
        self.logger.info(f"\n{'='*60}")
        self.logger.info(f"SIMULATING BUTTON CLICK: {callback_data}")
        self.logger.info(f"{'='*60}")
        
        # Create mock update
        update = MockUpdate(
            user_id=self.user_id,
            user_name=self.user_name,
            callback_data=callback_data
        )
        
        # Create mock context
        context = type('CallbackContext', (), {
            'bot': type('Bot', (), {'username': 'test_bot'})(),
            'user_data': {},
            'chat_data': {}
        })()
        
        # Handle the callback
        await self.bot.handle_button_click(update, context)
        
        # Small delay to see results
        await asyncio.sleep(1)
    
    async def simulate_message(self, text: str):
        """Simulate sending a message"""
        self.logger.info(f"\n{'='*60}")
        self.logger.info(f"SIMULATING MESSAGE: {text}")
        self.logger.info(f"{'='*60}")
        
        # Create mock update
        update = MockUpdate(
            user_id=self.user_id,
            user_name=self.user_name,
            message_text=text
        )
        
        # Create mock context
        context = type('CallbackContext', (), {
            'bot': type('Bot', (), {'username': 'test_bot'})(),
            'user_data': {},
            'chat_data': {}
        })()
        
        # Handle based on command
        if text == '/start':
            await self.bot.start(update, context)
        elif text == '/book':
            await self.bot.book(update, context)
        
        # Small delay to see results
        await asyncio.sleep(1)
    
    async def test_book_now_flow(self):
        """Test the complete Book Now flow"""
        self.logger.info("\n" + "="*80)
        self.logger.info("TESTING BOOK NOW (WITHIN 48H) FLOW")
        self.logger.info("="*80)
        
        # Step 1: Start command
        await self.simulate_message('/start')
        
        # Step 2: Book command
        await self.simulate_message('/book')
        
        # Step 3: Click "Book Now (Within 48h)"
        await self.simulate_button_click('immediate_booking')
        
        # Step 4: Select tomorrow's date
        tomorrow = datetime.now() + timedelta(days=1)
        date_callback = f"imm_date_{tomorrow.strftime('%Y-%m-%d')}"
        await self.simulate_button_click(date_callback)
        
        # Step 5: Select a time slot (try multiple common slots)
        time_slots = ['08:00', '09:00', '10:00', '11:00', '16:00', '17:00', '18:00']
        
        for time_slot in time_slots:
            self.logger.info(f"\nTrying time slot: {time_slot}")
            time_callback = f"imm_time_{time_slot}"
            await self.simulate_button_click(time_callback)
            
            # Step 6: Select court preference (Court 1)
            await self.simulate_button_click('imm_court_1')
            
            # Step 7: Confirm booking
            await self.simulate_button_click('imm_confirm')
            
            # Wait to see results
            await asyncio.sleep(5)
            
            # Check if booking was successful
            self.logger.info("\nChecking booking result...")
            
            # Try another slot
            self.logger.info("\nTrying next time slot...")
            await self.simulate_button_click('immediate_booking')
            await self.simulate_button_click(date_callback)
    
    async def cleanup(self):
        """Clean up resources"""
        if self.bot and self.bot.browser_pool:
            await self.bot.browser_pool.cleanup()
        self.logger.info("Cleanup complete")

async def main():
    """Main test function"""
    print("\n" + "="*80)
    print("TELEGRAM BOOKING TEST - BOOK NOW FUNCTIONALITY")
    print("="*80)
    print(f"Test User: Saul Campos (ID: 125763357)")
    print(f"Target Date: Tomorrow ({(datetime.now() + timedelta(days=1)).strftime('%Y-%m-%d')})")
    print(f"User Info: Saul Campos, msaulcampos@gmail.com, 31874277")
    print("="*80 + "\n")
    
    tester = TestTelegramBooking()
    
    try:
        # Setup bot
        await tester.setup_bot()
        
        # Run the test
        await tester.test_book_now_flow()
        
        print("\n" + "="*80)
        print("TEST COMPLETE")
        print("="*80)
        
    except Exception as e:
        print(f"\nERROR: {e}")
        import traceback
        traceback.print_exc()
    finally:
        await tester.cleanup()

if __name__ == "__main__":
    asyncio.run(main())
