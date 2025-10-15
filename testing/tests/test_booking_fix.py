"""
Test the booking fix for the overlay issue
"""
import asyncio
import logging
from datetime import datetime
from lvbot.utils.async_browser_pool import AsyncBrowserPool
from lvbot.utils.async_booking_executor import AsyncBookingExecutor
from lvbot.utils.tennis_executor import ExecutionResult

logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

async def test_booking_fix():
    """Test the booking with the fixed JavaScript click method"""
    
    # Initialize browser pool
    browser_pool = AsyncBrowserPool(courts=[1])
    await browser_pool.start()
    
    try:
        # Create booking executor
        executor = AsyncBookingExecutor(browser_pool, use_javascript_forms=True)
        
        # Test data
        court_number = 1
        time_slot = "11:00"
        user_info = {
            'first_name': 'Test',
            'last_name': 'User',
            'email': 'test@example.com',
            'phone': '5551234567'
        }
        target_date = datetime(2025, 7, 30)  # Tomorrow
        
        logger.info(f"Testing booking for Court {court_number} at {time_slot} on {target_date.strftime('%Y-%m-%d')}")
        
        # Execute booking
        start_time = asyncio.get_event_loop().time()
        result = await executor.execute_booking(
            court_number=court_number,
            time_slot=time_slot,
            user_info=user_info,
            target_date=target_date
        )
        end_time = asyncio.get_event_loop().time()
        
        # Log results
        logger.info(f"Booking completed in {end_time - start_time:.2f} seconds")
        logger.info(f"Success: {result.success}")
        if result.error_message:
            logger.error(f"Error: {result.error_message}")
        if result.confirmation_message:
            logger.info(f"Confirmation: {result.confirmation_message}")
        
        # Keep browser open for inspection
        logger.info("Browser will stay open for 30 seconds for inspection...")
        await asyncio.sleep(30)
            
    finally:
        await browser_pool.stop()

if __name__ == "__main__":
    asyncio.run(test_booking_fix())