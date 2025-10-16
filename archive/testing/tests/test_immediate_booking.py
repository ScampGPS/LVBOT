#!/usr/bin/env python3
"""
Direct test of immediate booking functionality
Tests booking for tomorrow using Saul's information
"""
from tracking import t

import asyncio
import logging
from datetime import datetime, timedelta
import sys
import os

# Add parent directory to path
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

# Import required components
from lvbot.utils.async_browser_pool import AsyncBrowserPool
from lvbot.utils.async_booking_executor import AsyncBookingExecutor
from immediate_booking_handler import ImmediateBookingHandler
from lvbot.utils.user_manager import UserManager

# Setup logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    datefmt='%H:%M:%S'
)

async def test_immediate_booking():
    """Test immediate booking with working executor"""
    t('archive.testing.tests.test_immediate_booking.test_immediate_booking')
    logger = logging.getLogger('TestImmediateBooking')
    
    print("\n" + "="*80)
    print("IMMEDIATE BOOKING TEST - DIRECT EXECUTION")
    print("="*80)
    
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
    
    print(f"User: {user_info['first_name']} {user_info['last_name']}")
    print(f"Email: {user_info['email']}")
    print(f"Phone: {user_info['phone']}")
    print(f"Target Date: {target_date.strftime('%Y-%m-%d')} (tomorrow)")
    print("="*80 + "\n")
    
    # Initialize browser pool
    logger.info("Initializing browser pool...")
    browser_pool = AsyncBrowserPool()
    await browser_pool.start()
    logger.info("Browser pool ready")
    
    # Create booking executor (will use working solution)
    executor = AsyncBookingExecutor(browser_pool, use_natural_flow=False)
    
    # Test different time slots
    time_slots = ['08:00', '09:00', '10:00', '11:00', '16:00', '17:00', '18:00', '19:00']
    court_preferences = [1, 2, 3]  # Try all courts
    
    successful = False
    
    for time_slot in time_slots:
        if successful:
            break
            
        logger.info(f"\n{'='*60}")
        logger.info(f"ATTEMPTING BOOKING: {time_slot} on {target_date.strftime('%A, %B %d')}")
        logger.info(f"{'='*60}")
        
        try:
            # Execute booking attempt
            result = await executor.execute_parallel_booking(
                court_numbers=court_preferences,
                time_slot=time_slot,
                user_info=user_info,
                target_date=target_date,
                max_concurrent=3
            )
            
            if result['success']:
                successful = True
                logger.info(f"\n{'='*60}")
                logger.info(f"✅ BOOKING SUCCESSFUL!")
                logger.info(f"Court: {result['successful_court']}")
                logger.info(f"Time: {time_slot}")
                logger.info(f"Date: {target_date.strftime('%Y-%m-%d')}")
                
                # Get detailed result
                court_result = result['results'].get(result['successful_court'])
                if court_result:
                    if court_result.confirmation_id:
                        logger.info(f"Confirmation ID: {court_result.confirmation_id}")
                    if court_result.confirmation_url:
                        logger.info(f"Confirmation URL: {court_result.confirmation_url}")
                
                logger.info(f"{'='*60}")
                break
            else:
                logger.warning(f"Booking failed for {time_slot}")
                
                # Log individual court results
                for court, court_result in result['results'].items():
                    if court_result.error_message:
                        logger.warning(f"  Court {court}: {court_result.error_message}")
                
        except Exception as e:
            logger.error(f"Error attempting booking for {time_slot}: {e}")
            import traceback
            traceback.print_exc()
        
        # Small delay between attempts
        await asyncio.sleep(2)
    
    if not successful:
        logger.error("\n❌ No time slots were successfully booked")
    
    # Cleanup
    logger.info("\nCleaning up...")
    await browser_pool.cleanup()
    logger.info("Test complete")

async def test_single_slot():
    """Test a single specific time slot"""
    t('archive.testing.tests.test_immediate_booking.test_single_slot')
    logger = logging.getLogger('TestSingleSlot')
    
    print("\n" + "="*80)
    print("SINGLE SLOT BOOKING TEST")
    print("="*80)
    
    # User information
    user_info = {
        'user_id': 125763357,
        'first_name': 'Saul',
        'last_name': 'Campos',
        'email': 'msaulcampos@gmail.com',
        'phone': '31874277'
    }
    
    # Target
    target_date = datetime.now() + timedelta(days=1)
    target_time = '10:00'
    target_court = 1
    
    print(f"Testing single booking:")
    print(f"  Date: {target_date.strftime('%Y-%m-%d')}")
    print(f"  Time: {target_time}")
    print(f"  Court: {target_court}")
    print("="*80 + "\n")
    
    # Initialize browser pool
    browser_pool = AsyncBrowserPool()
    await browser_pool.start()
    
    # Create executor
    executor = AsyncBookingExecutor(browser_pool, use_natural_flow=False)
    
    # Execute single booking
    result = await executor.execute_booking(
        court_number=target_court,
        time_slot=target_time,
        user_info=user_info,
        target_date=target_date
    )
    
    if result.success:
        logger.info("✅ BOOKING SUCCESSFUL!")
        logger.info(f"Message: {result.message}")
        if result.confirmation_id:
            logger.info(f"Confirmation ID: {result.confirmation_id}")
    else:
        logger.error("❌ BOOKING FAILED!")
        logger.error(f"Error: {result.error_message}")
    
    # Cleanup
    await browser_pool.cleanup()

async def main():
    """Main test function"""
    t('archive.testing.tests.test_immediate_booking.main')
    
    # Choose which test to run
    print("\nSelect test mode:")
    print("1. Test multiple time slots")
    print("2. Test single slot (10:00)")
    
    choice = input("\nEnter choice (1 or 2): ").strip()
    
    if choice == '1':
        await test_immediate_booking()
    elif choice == '2':
        await test_single_slot()
    else:
        print("Invalid choice")

if __name__ == "__main__":
    asyncio.run(main())