#!/usr/bin/env python3
"""
Test booking execution timing to identify bottlenecks
"""

import asyncio
import logging
import time
from datetime import datetime, timedelta
from lvbot.utils.async_booking_executor import AsyncBookingExecutor
from lvbot.utils.async_browser_pool import AsyncBrowserPool
from lvbot.utils.acuity_booking_form import AcuityBookingForm
from lvbot.utils.browser_allocation import BrowserAllocation
from lvbot.utils.error_handler import ErrorHandler

# Set up logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

async def test_booking_timing():
    """Test booking execution with detailed timing breakdown"""
    
    # Test parameters
    court_number = 1
    target_date = datetime.now() + timedelta(days=2)
    time_slot = "10:00"
    user_info = {
        'firstName': 'Test',
        'lastName': 'User',
        'email': 'test@example.com',
        'phone': '5025551234'
    }
    
    # Initialize components
    browser_pool = AsyncBrowserPool()
    form_handler = AcuityBookingForm()
    browser_allocation = BrowserAllocation()
    error_handler = ErrorHandler()
    
    executor = AsyncBookingExecutor(
        browser_pool=browser_pool,
        form_handler=form_handler,
        browser_allocation=browser_allocation,
        error_handler=error_handler,
        speed_mode='normal'
    )
    
    try:
        # Initialize browser pool
        logger.info("Initializing browser pool...")
        init_start = time.time()
        await browser_pool.initialize()
        init_time = time.time() - init_start
        logger.info(f"Browser pool initialized in {init_time:.2f}s")
        
        # Test navigation only
        logger.info("\n=== TESTING NAVIGATION ONLY ===")
        page = browser_pool.pages[court_number]
        
        # Construct URL
        date_str = target_date.strftime("%Y-%m-%d")
        appointment_type_ids = {1: "15970897", 2: "16021953", 3: "16120442"}
        appointment_type_id = appointment_type_ids[court_number]
        base_url = "https://clublavilla.as.me/schedule/7d558012/appointment"
        calendar_id = "4291312"
        datetime_str = f"{date_str}T{time_slot}:00-06:00"
        direct_url = f"{base_url}/{appointment_type_id}/calendar/{calendar_id}/datetime/{datetime_str}?appointmentTypeIds[]={appointment_type_id}"
        
        logger.info(f"Testing URL: {direct_url}")
        
        # Test optimized navigation
        from lvbot.utils.optimized_navigation import OptimizedNavigation
        
        nav_start = time.time()
        nav_success, nav_message = await OptimizedNavigation.navigate_and_validate(
            page,
            direct_url,
            expected_form_fields=[
                'input[name="client.firstName"]',
                'input[name="client.lastName"]',
                'input[name="client.email"]',
                'input[name="client.phone"]'
            ]
        )
        nav_time = time.time() - nav_start
        
        logger.info(f"Navigation result: {nav_success} - {nav_message}")
        logger.info(f"Navigation time: {nav_time:.2f}s")
        
        # Test form filling
        logger.info("\n=== TESTING FORM FILLING ===")
        fill_start = time.time()
        
        try:
            # Fill form
            await form_handler.fill_booking_form(page, user_info)
            fill_time = time.time() - fill_start
            logger.info(f"Form filling completed in {fill_time:.2f}s")
        except Exception as e:
            fill_time = time.time() - fill_start
            logger.error(f"Form filling failed after {fill_time:.2f}s: {e}")
        
        # Test full execution
        logger.info("\n=== TESTING FULL EXECUTION ===")
        exec_start = time.time()
        
        result = await executor.execute_booking(
            court_number=court_number,
            time_slot=time_slot,
            user_info=user_info,
            target_date=target_date
        )
        
        exec_time = time.time() - exec_start
        logger.info(f"Full execution completed in {exec_time:.2f}s")
        logger.info(f"Result: {result}")
        
        # Summary
        logger.info("\n=== TIMING SUMMARY ===")
        logger.info(f"Browser init: {init_time:.2f}s")
        logger.info(f"Navigation only: {nav_time:.2f}s")
        logger.info(f"Form filling: {fill_time:.2f}s")
        logger.info(f"Full execution: {exec_time:.2f}s")
        
        # Calculate overhead
        overhead = exec_time - (nav_time + fill_time)
        logger.info(f"Overhead (submission, checks, etc): {overhead:.2f}s")
        
    except Exception as e:
        logger.error(f"Test failed: {e}", exc_info=True)
    finally:
        # Cleanup
        await browser_pool.close()
        logger.info("Browser pool closed")

if __name__ == "__main__":
    asyncio.run(test_booking_timing())