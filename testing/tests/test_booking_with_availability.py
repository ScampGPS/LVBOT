#!/usr/bin/env python3
"""
Test booking with actual court availability checking
This simulates the Telegram flow and books the first available slot
"""

import asyncio
import logging
from datetime import datetime, timedelta
from typing import List, Dict, Optional

# Setup logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    datefmt='%H:%M:%S'
)

async def test_booking_with_availability():
    """Test booking using actual court availability"""
    logger = logging.getLogger('TestBooking')
    
    print("\n" + "="*80)
    print("COURT BOOKING TEST - WITH AVAILABILITY CHECK")
    print("="*80)
    print("This will check actual court availability and book the first available slot")
    print("="*80 + "\n")
    
    # Import required modules
    from lvbot.utils.async_browser_pool import AsyncBrowserPool
    from lvbot.utils.court_availability import CourtAvailability
    from lvbot.utils.async_booking_executor import AsyncBookingExecutor
    from lvbot.utils.immediate_booking_handler import ImmediateBookingHandler
    from lvbot.utils.user_manager import UserManager
    
    # User information
    user_info = {
        'user_id': 125763357,
        'first_name': 'Saul',
        'last_name': 'Campos',
        'email': 'msaulcampos@gmail.com',
        'phone': '31874277'
    }
    
    # Target date (tomorrow)
    target_date = datetime.now() + timedelta(days=1)
    target_date_str = target_date.strftime('%Y-%m-%d')
    
    print(f"User: {user_info['first_name']} {user_info['last_name']}")
    print(f"Target Date: {target_date.strftime('%A, %B %d, %Y')} (tomorrow)")
    print("="*80 + "\n")
    
    # Initialize browser pool
    logger.info("Initializing browser pool...")
    browser_pool = AsyncBrowserPool()
    await browser_pool.start()
    logger.info("Browser pool ready with 3 courts")
    
    # Create availability checker
    availability = CourtAvailability()
    
    # Check availability for each court
    all_available_times = {}
    
    for court_number in [1, 2, 3]:
        logger.info(f"\nChecking availability for Court {court_number}...")
        
        try:
            # Get the page for this court
            page = await browser_pool.get_page(court_number)
            if not page:
                logger.warning(f"Could not get page for Court {court_number}")
                continue
            
            # Check if we're on Acuity page
            if await availability.is_acuity_scheduling_page(page):
                logger.info(f"Court {court_number} is on Acuity Scheduling page")
                
                # Extract available times by day
                times_by_day = await availability.extract_acuity_times_by_day(page)
                
                # Look for tomorrow's times
                if target_date_str in times_by_day:
                    available_times = times_by_day[target_date_str]
                    logger.info(f"Court {court_number} has {len(available_times)} available slots for tomorrow:")
                    for time in available_times:
                        logger.info(f"  ✓ {time}")
                    all_available_times[court_number] = available_times
                else:
                    logger.info(f"No available times for tomorrow on Court {court_number}")
            else:
                logger.warning(f"Court {court_number} is not on Acuity page")
                
        except Exception as e:
            logger.error(f"Error checking Court {court_number}: {e}")
    
    # Now try to book the first available slot
    if not all_available_times:
        logger.error("\n❌ NO AVAILABLE TIMES FOUND ON ANY COURT")
        await browser_pool.cleanup()
        return
    
    # Create booking executor
    executor = AsyncBookingExecutor(browser_pool, use_natural_flow=False)
    
    # Try to book from available times
    booking_successful = False
    
    for court_number, times in all_available_times.items():
        if booking_successful:
            break
            
        for time_slot in times:
            logger.info(f"\n{'='*60}")
            logger.info(f"ATTEMPTING TO BOOK: Court {court_number} at {time_slot}")
            logger.info(f"{'='*60}")
            
            try:
                # Execute single court booking
                result = await executor.execute_booking(
                    court_number=court_number,
                    time_slot=time_slot,
                    user_info=user_info,
                    target_date=target_date
                )
                
                if result.success:
                    booking_successful = True
                    logger.info("\n" + "="*60)
                    logger.info("✅ BOOKING SUCCESSFUL!")
                    logger.info(f"Court: {court_number}")
                    logger.info(f"Time: {time_slot}")
                    logger.info(f"Date: {target_date_str}")
                    if result.confirmation_id:
                        logger.info(f"Confirmation ID: {result.confirmation_id}")
                    if result.confirmation_url:
                        logger.info(f"Confirmation URL: {result.confirmation_url}")
                    logger.info("="*60)
                    break
                else:
                    logger.warning(f"Booking failed: {result.error_message}")
                    
            except Exception as e:
                logger.error(f"Error during booking: {e}")
                import traceback
                traceback.print_exc()
            
            # Small delay between attempts
            await asyncio.sleep(2)
    
    if not booking_successful:
        logger.error("\n❌ COULD NOT BOOK ANY AVAILABLE SLOT")
    
    # Keep browsers open to see result
    print("\n" + "="*80)
    print("Browsers will remain open for inspection")
    print("Press Ctrl+C to close and exit")
    print("="*80)
    
    try:
        while True:
            await asyncio.sleep(1)
    except KeyboardInterrupt:
        logger.info("\nClosing browsers...")
        await browser_pool.cleanup()
        logger.info("Test complete")

async def quick_availability_check():
    """Quick check of available times without booking"""
    logger = logging.getLogger('QuickCheck')
    
    print("\n" + "="*80)
    print("QUICK AVAILABILITY CHECK")
    print("="*80)
    
    from lvbot.utils.async_browser_pool import AsyncBrowserPool
    from lvbot.utils.court_availability import CourtAvailability
    
    # Initialize browser pool
    browser_pool = AsyncBrowserPool()
    await browser_pool.start()
    
    # Check availability
    availability = CourtAvailability()
    target_date = datetime.now() + timedelta(days=1)
    target_date_str = target_date.strftime('%Y-%m-%d')
    
    print(f"\nChecking availability for {target_date.strftime('%A, %B %d')}...")
    
    for court_number in [1, 2, 3]:
        try:
            page = await browser_pool.get_page(court_number)
            if page and await availability.is_acuity_scheduling_page(page):
                times_by_day = await availability.extract_acuity_times_by_day(page)
                if target_date_str in times_by_day:
                    times = times_by_day[target_date_str]
                    print(f"\nCourt {court_number}: {len(times)} slots available")
                    for time in times[:5]:  # Show first 5
                        print(f"  • {time}")
                    if len(times) > 5:
                        print(f"  ... and {len(times) - 5} more")
                else:
                    print(f"\nCourt {court_number}: No times available")
            else:
                print(f"\nCourt {court_number}: Not on booking page")
        except Exception as e:
            print(f"\nCourt {court_number}: Error - {e}")
    
    await browser_pool.cleanup()

if __name__ == "__main__":
    # Run availability check first
    asyncio.run(quick_availability_check())
    
    # Then run booking test
    proceed = input("\nProceed with booking test? (y/n): ")
    if proceed.lower() == 'y':
        asyncio.run(test_booking_with_availability())