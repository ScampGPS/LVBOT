#!/usr/bin/env python3
"""
Test Telegram bot booking flow with dynamic time selection
Simulates user clicking through the Book Now flow and selecting from available times
"""
from utils.tracking import t

import asyncio
import logging
import re
from datetime import datetime, timedelta
from typing import List, Optional

# Setup logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    datefmt='%H:%M:%S'
)

class TelegramBotTester:
    """Simulates Telegram user interactions with the bot"""
    
    def __init__(self):
        t('archive.testing.tests.test_telegram_dynamic.TelegramBotTester.__init__')
        self.logger = logging.getLogger('TelegramBotTester')
        self.bot = None
        self.user_id = 125763357  # Saul's user ID
        self.user_name = "Saul"
        self.captured_buttons = []
        self.captured_messages = []
        
    async def setup(self):
        """Initialize the bot"""
        t('archive.testing.tests.test_telegram_dynamic.TelegramBotTester.setup')
        from telegram_tennis_bot import CleanBot
        
        self.logger.info("Initializing Telegram bot...")
        self.bot = CleanBot()
        await self.bot.initialize()
        await self.bot.start_pool()
        self.logger.info("Bot initialized successfully")
        
    async def create_mock_update(self, callback_data: str = None, message_text: str = None):
        """Create a mock Telegram update"""
        t('archive.testing.tests.test_telegram_dynamic.TelegramBotTester.create_mock_update')
        class MockUser:
            def __init__(self, user_id, name):
                t('archive.testing.tests.test_telegram_dynamic.TelegramBotTester.create_mock_update.MockUser.__init__')
                self.id = user_id
                self.first_name = name
                self.username = name.lower()
                self.is_bot = False
                
        class MockChat:
            def __init__(self, chat_id):
                t('archive.testing.tests.test_telegram_dynamic.TelegramBotTester.create_mock_update.MockChat.__init__')
                self.id = chat_id
                self.type = 'private'
                
        class MockMessage:
            def __init__(self, chat, user, text=None):
                t('archive.testing.tests.test_telegram_dynamic.TelegramBotTester.create_mock_update.MockMessage.__init__')
                self.chat = chat
                self.from_user = user
                self.text = text
                self.message_id = 100
                self.date = datetime.now()
                self.captured_buttons = []
                self.captured_text = []
                
            async def reply_text(self, text, **kwargs):
                t('archive.testing.tests.test_telegram_dynamic.TelegramBotTester.create_mock_update.MockMessage.reply_text')
                self.captured_text.append(text)
                print(f"\n[BOT REPLY] {text}")
                if 'reply_markup' in kwargs and kwargs['reply_markup']:
                    self.captured_buttons = kwargs['reply_markup'].inline_keyboard
                    print("[AVAILABLE BUTTONS]:")
                    for row in kwargs['reply_markup'].inline_keyboard:
                        for button in row:
                            print(f"  ▶ {button.text} (callback: {button.callback_data})")
                return self
                
            async def edit_text(self, text, **kwargs):
                t('archive.testing.tests.test_telegram_dynamic.TelegramBotTester.create_mock_update.MockMessage.edit_text')
                self.captured_text.append(text)
                print(f"\n[BOT EDIT] {text}")
                if 'reply_markup' in kwargs and kwargs['reply_markup']:
                    self.captured_buttons = kwargs['reply_markup'].inline_keyboard
                    print("[AVAILABLE BUTTONS]:")
                    for row in kwargs['reply_markup'].inline_keyboard:
                        for button in row:
                            print(f"  ▶ {button.text} (callback: {button.callback_data})")
                return self
                
            async def delete(self):
                t('archive.testing.tests.test_telegram_dynamic.TelegramBotTester.create_mock_update.MockMessage.delete')
                print("[MESSAGE DELETED]")
                
        class MockCallbackQuery:
            def __init__(self, user, data, message):
                t('archive.testing.tests.test_telegram_dynamic.TelegramBotTester.create_mock_update.MockCallbackQuery.__init__')
                self.id = '12345'
                self.from_user = user
                self.data = data
                self.message = message
                
            async def answer(self, text=""):
                t('archive.testing.tests.test_telegram_dynamic.TelegramBotTester.create_mock_update.MockCallbackQuery.answer')
                if text:
                    print(f"[CALLBACK ANSWER] {text}")
                    
        class MockUpdate:
            def __init__(self):
                t('archive.testing.tests.test_telegram_dynamic.TelegramBotTester.create_mock_update.MockUpdate.__init__')
                self.callback_query = None
                self.message = None
                
        # Create mock objects
        user = MockUser(self.user_id, self.user_name)
        chat = MockChat(self.user_id)
        message = MockMessage(chat, user, message_text)
        
        update = MockUpdate()
        
        if callback_data:
            update.callback_query = MockCallbackQuery(user, callback_data, message)
        elif message_text:
            update.message = message
            
        return update, message
        
    async def create_mock_context(self):
        """Create a mock context"""
        t('archive.testing.tests.test_telegram_dynamic.TelegramBotTester.create_mock_context')
        class MockBot:
            username = 'test_bot'
            
        class MockContext:
            def __init__(self):
                t('archive.testing.tests.test_telegram_dynamic.TelegramBotTester.create_mock_context.MockContext.__init__')
                self.bot = MockBot()
                self.user_data = {}
                self.chat_data = {}
                
        return MockContext()
        
    async def send_command(self, command: str):
        """Send a command to the bot"""
        t('archive.testing.tests.test_telegram_dynamic.TelegramBotTester.send_command')
        self.logger.info(f"\n{'='*60}")
        self.logger.info(f"SENDING COMMAND: {command}")
        self.logger.info(f"{'='*60}")
        
        update, message = await self.create_mock_update(message_text=command)
        context = await self.create_mock_context()
        
        if command == '/start':
            await self.bot.start(update, context)
        elif command == '/book':
            await self.bot.book(update, context)
            
        return message
        
    async def click_button(self, callback_data: str, description: str = ""):
        """Simulate clicking a button"""
        t('archive.testing.tests.test_telegram_dynamic.TelegramBotTester.click_button')
        self.logger.info(f"\n{'='*60}")
        self.logger.info(f"CLICKING: {description or callback_data}")
        self.logger.info(f"{'='*60}")
        
        update, message = await self.create_mock_update(callback_data=callback_data)
        context = await self.create_mock_context()
        
        await self.bot.handle_button_click(update, context)
        
        return message
        
    def extract_available_times(self, buttons) -> List[str]:
        """Extract available time slots from buttons"""
        t('archive.testing.tests.test_telegram_dynamic.TelegramBotTester.extract_available_times')
        times = []
        for row in buttons:
            for button in row:
                # Look for time pattern in button text (e.g., "09:00", "10:00")
                if re.match(r'\d{2}:\d{2}', button.text):
                    times.append({
                        'time': button.text,
                        'callback': button.callback_data
                    })
        return times
        
    async def test_book_now_flow(self):
        """Test the complete Book Now flow with dynamic time selection"""
        t('archive.testing.tests.test_telegram_dynamic.TelegramBotTester.test_book_now_flow')
        print("\n" + "="*80)
        print("TESTING TELEGRAM BOT - BOOK NOW FLOW")
        print("="*80)
        print(f"User: {self.user_name} (ID: {self.user_id})")
        print(f"Target: Tomorrow ({(datetime.now() + timedelta(days=1)).strftime('%A, %B %d')})")
        print("="*80)
        
        # Step 1: Send /book command
        message = await self.send_command('/book')
        await asyncio.sleep(1)
        
        # Step 2: Click "Book Now (Within 48h)"
        await self.click_button('immediate_booking', "Book Now (Within 48h)")
        await asyncio.sleep(1)
        
        # Step 3: Select tomorrow's date
        tomorrow = datetime.now() + timedelta(days=1)
        date_callback = f"imm_date_{tomorrow.strftime('%Y-%m-%d')}"
        message = await self.click_button(date_callback, f"Tomorrow ({tomorrow.strftime('%A')})")
        await asyncio.sleep(1)
        
        # Step 4: Check available times
        if message.captured_buttons:
            available_times = self.extract_available_times(message.captured_buttons)
            
            if available_times:
                print(f"\n[FOUND {len(available_times)} AVAILABLE TIME SLOTS]")
                for time_info in available_times:
                    print(f"  ✓ {time_info['time']}")
                
                # Try to book each available time
                for time_info in available_times:
                    print(f"\n{'='*60}")
                    print(f"ATTEMPTING TO BOOK: {time_info['time']}")
                    print(f"{'='*60}")
                    
                    # Click the time
                    message = await self.click_button(time_info['callback'], f"Time: {time_info['time']}")
                    await asyncio.sleep(1)
                    
                    # Select court preference (try Court 1 first)
                    message = await self.click_button('imm_court_1', "Court 1")
                    await asyncio.sleep(1)
                    
                    # Confirm booking
                    message = await self.click_button('imm_confirm', "Confirm Booking")
                    await asyncio.sleep(5)  # Wait for booking to process
                    
                    # Check if booking was successful
                    if message.captured_text:
                        last_message = message.captured_text[-1]
                        if "confirmado" in last_message.lower() or "éxito" in last_message.lower() or "successfully" in last_message.lower():
                            print("\n" + "="*60)
                            print("✅ BOOKING SUCCESSFUL!")
                            print(f"Time: {time_info['time']}")
                            print(f"Date: {tomorrow.strftime('%Y-%m-%d')}")
                            print("="*60)
                            return True
                        else:
                            print(f"❌ Booking failed for {time_info['time']}")
                            
                    # Go back to time selection for next attempt
                    if available_times.index(time_info) < len(available_times) - 1:
                        # Click Book Now again to restart
                        await self.send_command('/book')
                        await asyncio.sleep(1)
                        await self.click_button('immediate_booking', "Book Now (Within 48h)")
                        await asyncio.sleep(1)
                        await self.click_button(date_callback, f"Tomorrow ({tomorrow.strftime('%A')})")
                        await asyncio.sleep(1)
                        
            else:
                print("\n❌ NO AVAILABLE TIME SLOTS FOUND")
        else:
            print("\n❌ NO BUTTONS CAPTURED - Bot may not be responding correctly")
            
        return False
        
    async def cleanup(self):
        """Clean up resources"""
        t('archive.testing.tests.test_telegram_dynamic.TelegramBotTester.cleanup')
        if self.bot and self.bot.browser_pool:
            await self.bot.browser_pool.cleanup()
        self.logger.info("Cleanup complete")

async def main():
    """Main test function"""
    t('archive.testing.tests.test_telegram_dynamic.main')
    tester = TelegramBotTester()
    
    try:
        # Setup
        await tester.setup()
        
        # Run the test
        success = await tester.test_book_now_flow()
        
        print("\n" + "="*80)
        if success:
            print("✅ TEST PASSED - Booking was successful!")
        else:
            print("❌ TEST FAILED - No booking could be completed")
        print("="*80)
        
    except Exception as e:
        print(f"\n❌ ERROR: {e}")
        import traceback
        traceback.print_exc()
    finally:
        await tester.cleanup()

if __name__ == "__main__":
    asyncio.run(main())