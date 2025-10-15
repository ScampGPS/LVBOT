#!/usr/bin/env python3
"""
Test the working booking executor directly
This tests the exact same flow as court_booking_final.py but within LVBOT context
"""

import asyncio
import logging
from datetime import datetime, timedelta
import sys
import os

# Add parent directory to path
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

# Import working executor
from lvbot.utils.working_booking_executor import WorkingBookingExecutor
from lvbot.utils.async_browser_pool import AsyncBrowserPool

# Setup logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    datefmt='%H:%M:%S'
)

async def test_working_executor():
    """Test the working executor directly"""
    logger = logging.getLogger('TestWorkingExecutor')
    
    print("\n" + "="*80)
    print("WORKING EXECUTOR TEST - DIRECT EXECUTION")
    print("="*80)
    print("This uses the EXACT logic from court_booking_final.py")
    print("Speed Multiplier: 2.5x")
    print("="*80 + "\n")
    
    # User information (Saul's data)
    user_info = {
        'first_name': 'Saul',
        'last_name': 'Campos',
        'email': 'msaulcampos@gmail.com',
        'phone': '31874277'
    }
    
    # Target tomorrow at 10:00
    target_date = datetime.now() + timedelta(days=1)
    target_time = '10:00'
    court_number = 1
    
    print(f"Target Booking:")
    print(f"  Date: {target_date.strftime('%A, %B %d, %Y')}")
    print(f"  Time: {target_time}")
    print(f"  Court: {court_number}")
    print(f"  User: {user_info['first_name']} {user_info['last_name']}")
    print("="*80 + "\n")
    
    # Initialize browser pool
    logger.info("Initializing browser pool...")
    browser_pool = AsyncBrowserPool()
    await browser_pool.start()
    logger.info("Browser pool initialized with 3 courts")
    
    # Create working executor
    executor = WorkingBookingExecutor(browser_pool)
    
    # Execute booking
    logger.info("Starting booking execution...")
    logger.info("="*60)
    
    try:
        result = await executor.execute_booking(
            court_number=court_number,
            target_date=target_date,
            time_slot=target_time,
            user_info=user_info
        )
        
        logger.info("="*60)
        logger.info("BOOKING RESULT:")
        
        if result.success:
            logger.info("✅ BOOKING SUCCESSFUL!")
            if result.confirmation_id:
                logger.info(f"Confirmation ID: {result.confirmation_id}")
            if result.confirmation_url:
                logger.info(f"Confirmation URL: {result.confirmation_url}")
            if result.user_name:
                logger.info(f"Confirmed for: {result.user_name}")
        else:
            logger.error("❌ BOOKING FAILED!")
            logger.error(f"Error: {result.error_message}")
            
    except Exception as e:
        logger.error(f"Exception during booking: {e}")
        import traceback
        traceback.print_exc()
    
    logger.info("="*60)
    
    # Keep browser open for inspection
    print("\n" + "="*80)
    print("Browser windows will remain open for inspection")
    print("Press Ctrl+C to close and exit")
    print("="*80)
    
    try:
        while True:
            await asyncio.sleep(1)
    except KeyboardInterrupt:
        logger.info("\nClosing browsers...")
        await browser_pool.cleanup()
        logger.info("Test complete")

async def test_all_courts():
    """Test booking on all courts"""
    logger = logging.getLogger('TestAllCourts')
    
    print("\n" + "="*80)
    print("TESTING ALL COURTS")
    print("="*80)
    
    # Initialize browser pool
    browser_pool = AsyncBrowserPool()
    await browser_pool.start()
    
    # User info
    user_info = {
        'first_name': 'Saul',
        'last_name': 'Campos',
        'email': 'msaulcampos@gmail.com',
        'phone': '31874277'
    }
    
    # Target
    target_date = datetime.now() + timedelta(days=1)
    target_time = '10:00'
    
    # Create executor
    executor = WorkingBookingExecutor(browser_pool)
    
    # Test each court
    for court_number in [1, 2, 3]:
        logger.info(f"\n{'='*40}")
        logger.info(f"Testing Court {court_number}")
        logger.info(f"{'='*40}")
        
        try:
            result = await executor.execute_booking(
                court_number=court_number,
                target_date=target_date,
                time_slot=target_time,
                user_info=user_info
            )
            
            if result.success:
                logger.info(f"✅ Court {court_number}: SUCCESS")
                if result.confirmation_id:
                    logger.info(f"   Confirmation: {result.confirmation_id}")
                break  # Stop after first success
            else:
                logger.warning(f"❌ Court {court_number}: {result.error_message}")
                
        except Exception as e:
            logger.error(f"❌ Court {court_number}: Exception - {e}")
        
        # Small delay between courts
        await asyncio.sleep(2)
    
    # Cleanup
    await browser_pool.cleanup()

async def main():
    """Main test function"""
    
    # Run single court test automatically
    await test_working_executor()

if __name__ == "__main__":
    asyncio.run(main())