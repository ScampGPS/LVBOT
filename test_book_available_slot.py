#!/usr/bin/env python3
"""
Test booking an available slot for tomorrow
Books the first available slot from the courts
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

async def book_first_available_slot():
    """Book the first available slot for tomorrow"""
    logger = logging.getLogger('BookAvailableSlot')
    
    print("\n" + "="*80)
    print("BOOKING FIRST AVAILABLE SLOT FOR TOMORROW")
    print("="*80)
    print("User: Saul Campos")
    print("Date: Tomorrow (July 30, 2025)")
    print("="*80 + "\n")
    
    # Import required modules
    from utils.async_browser_pool import AsyncBrowserPool
    from utils.async_booking_executor import AsyncBookingExecutor
    
    # User information
    user_info = {
        'user_id': 125763357,
        'first_name': 'Saul',
        'last_name': 'Campos',
        'email': 'msaulcampos@gmail.com',
        'phone': '31874277'
    }
    
    # Target date
    target_date = datetime.now() + timedelta(days=1)
    
    # Based on the availability check, we know these times are available
    # Let's try to book 10:00 on Court 1
    target_time = '10:00'
    target_court = 1
    
    print(f"Attempting to book: Court {target_court} at {target_time}")
    print("="*80 + "\n")
    
    # Initialize browser pool
    logger.info("Initializing browser pool...")
    browser_pool = AsyncBrowserPool()
    await browser_pool.start()
    logger.info("Browser pool ready")
    
    # Create booking executor (uses working solution)
    executor = AsyncBookingExecutor(browser_pool, use_natural_flow=False)
    
    try:
        # Execute booking
        logger.info(f"Starting booking execution for Court {target_court} at {target_time}...")
        
        result = await executor.execute_booking(
            court_number=target_court,
            time_slot=target_time,
            user_info=user_info,
            target_date=target_date
        )
        
        print("\n" + "="*80)
        if result.success:
            print("✅ BOOKING SUCCESSFUL!")
            print(f"Court: {target_court}")
            print(f"Time: {target_time}")
            print(f"Date: {target_date.strftime('%Y-%m-%d')}")
            if result.confirmation_id:
                print(f"Confirmation ID: {result.confirmation_id}")
            if result.confirmation_url:
                print(f"Confirmation URL: {result.confirmation_url}")
            if result.message:
                print(f"Message: {result.message}")
        else:
            print("❌ BOOKING FAILED!")
            print(f"Error: {result.error_message}")
            
            # Try another time slot
            print("\nTrying 11:00 instead...")
            target_time = '11:00'
            
            result = await executor.execute_booking(
                court_number=target_court,
                time_slot=target_time,
                user_info=user_info,
                target_date=target_date
            )
            
            if result.success:
                print("\n✅ BOOKING SUCCESSFUL!")
                print(f"Court: {target_court}")
                print(f"Time: {target_time}")
                if result.confirmation_id:
                    print(f"Confirmation ID: {result.confirmation_id}")
            else:
                print(f"\n❌ Also failed: {result.error_message}")
                
        print("="*80)
        
    except Exception as e:
        logger.error(f"Exception during booking: {e}")
        import traceback
        traceback.print_exc()
    
    # Keep browsers open for inspection
    print("\nBrowsers will remain open for inspection")
    print("Press Ctrl+C to close and exit")
    
    try:
        while True:
            await asyncio.sleep(1)
    except KeyboardInterrupt:
        logger.info("\nClosing browsers...")
        # Use the correct cleanup method
        if hasattr(browser_pool, 'cleanup'):
            await browser_pool.cleanup()
        elif hasattr(browser_pool, 'close'):
            await browser_pool.close()
        else:
            logger.warning("No cleanup method found for browser pool")
        logger.info("Test complete")

if __name__ == "__main__":
    asyncio.run(book_first_available_slot())