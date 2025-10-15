#!/usr/bin/env python3
"""
Simple test of Telegram immediate booking
Tests if the bot can execute a booking for tomorrow
"""

import asyncio
import logging
from datetime import datetime, timedelta

# Setup logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    datefmt='%H:%M:%S'
)

async def test_booking():
    """Test immediate booking directly"""
    logger = logging.getLogger('TestBooking')
    
    print("\n" + "="*80)
    print("TELEGRAM BOT IMMEDIATE BOOKING TEST")
    print("="*80)
    print("This will simulate the Telegram 'Book Now' flow")
    print("="*80 + "\n")
    
    # Import after setting up logging
    from telegram_tennis_bot import CleanBot
    from immediate_booking_handler import ImmediateBookingHandler
    
    # Initialize bot
    logger.info("Initializing bot...")
    bot = CleanBot()
    await bot.initialize()
    await bot.start_pool()
    logger.info("Bot initialized with browser pool")
    
    # Get immediate booking handler
    handler = ImmediateBookingHandler(
        browser_pool=bot.browser_pool,
        user_manager=bot.user_manager
    )
    
    # User info
    user_id = 125763357
    target_date = datetime.now() + timedelta(days=1)
    
    logger.info(f"Testing booking for user {user_id} (Saul)")
    logger.info(f"Target date: {target_date.strftime('%Y-%m-%d')} (tomorrow)")
    
    # Test multiple time slots
    time_slots = ['09:00', '10:00', '11:00', '16:00', '17:00', '18:00']
    court_prefs = [1, 2, 3]
    
    for time_slot in time_slots:
        logger.info(f"\n{'='*60}")
        logger.info(f"ATTEMPTING: {time_slot} on {target_date.strftime('%A')}")
        logger.info(f"{'='*60}")
        
        try:
            # Execute immediate booking
            result = await handler.execute_immediate_booking(
                user_id=user_id,
                date=target_date,
                time=time_slot,
                court_preferences=court_prefs
            )
            
            if result['success']:
                logger.info("✅ BOOKING SUCCESSFUL!")
                logger.info(f"Message: {result.get('message', 'No message')}")
                if 'confirmation_details' in result:
                    details = result['confirmation_details']
                    if details.get('confirmation_id'):
                        logger.info(f"Confirmation ID: {details['confirmation_id']}")
                    if details.get('court'):
                        logger.info(f"Court: {details['court']}")
                break
            else:
                logger.warning(f"Booking failed: {result.get('error', 'Unknown error')}")
                
        except Exception as e:
            logger.error(f"Exception during booking: {e}")
            import traceback
            traceback.print_exc()
        
        # Small delay between attempts
        await asyncio.sleep(2)
    
    # Cleanup
    logger.info("\nCleaning up...")
    await bot.browser_pool.cleanup()
    logger.info("Test complete")

if __name__ == "__main__":
    asyncio.run(test_booking())