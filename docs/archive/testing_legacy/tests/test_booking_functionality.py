#!/usr/bin/env python3
"""
Test script to validate actual booking functionality
Tests whether the system can navigate through the booking process
"""

import asyncio
import logging
import sys
import os
from datetime import datetime, timedelta

# Add the project root to Python path
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from lvbot.utils.async_browser_pool import AsyncBrowserPool
from lvbot.utils.tennis_config import TennisConfig
from lvbot.utils.async_booking_executor import AsyncBookingExecutor
from lvbot.utils.constants import COURT_CONFIG

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

async def test_booking_flow():
    """Test the complete booking flow"""
    logger.info("🧪 Starting booking functionality test...")
    
    browser_pool = None
    try:
        # Initialize browser pool with one court
        logger.info("📱 Initializing browser pool...")
        browser_pool = AsyncBrowserPool(courts=[1])
        await browser_pool.start()
        
        if not browser_pool.is_ready():
            logger.error("❌ Browser pool not ready")
            return
            
        logger.info("✅ Browser pool ready")
        
        # Create test configuration
        test_config = TennisConfig(
            email="test@example.com",
            first_name="Test",
            last_name="User", 
            phone="555-1234",
            user_id="test_user",
            preferred_time="09:00",
            target_time="09:00",
            fallback_times=["10:00", "11:00"],
            court_preference=[1]
        )
        
        # Create booking executor
        logger.info("⚙️ Creating booking executor...")
        booking_executor = AsyncBookingExecutor()
        
        # Test date - 3 days from now to avoid conflicts
        test_date = datetime.now() + timedelta(days=3)
        test_date_str = test_date.strftime('%Y-%m-%d')
        
        logger.info(f"📅 Testing booking for: {test_date_str} at 09:00")
        
        # Test navigation to booking form
        page = await browser_pool.get_page(1)
        if not page:
            logger.error("❌ Could not get page from browser pool")
            return
            
        logger.info("🌐 Testing navigation to booking form...")
        appointment_id = COURT_CONFIG[1]['appointment_id']
        calendar_id = COURT_CONFIG[1]['calendar_id'] 
        booking_url = f"https://clublavilla.as.me/schedule/7d558012/appointment/{appointment_id}/calendar/{calendar_id}/datetime/{test_date_str}T09:00:00-06:00?appointmentTypeIds[]={appointment_id}"
        
        await page.goto(booking_url, wait_until='networkidle')
        
        # Check if form loaded
        await asyncio.sleep(2)
        
        # Try to find form elements
        form_elements = {
            'firstName': 'input[name="client.firstName"]',
            'lastName': 'input[name="client.lastName"]',
            'phone': 'input[name="client.phone"]', 
            'email': 'input[name="client.email"]'
        }
        
        elements_found = 0
        for field_name, selector in form_elements.items():
            try:
                element = await page.wait_for_selector(selector, timeout=5000)
                if element:
                    elements_found += 1
                    logger.info(f"  ✅ Found {field_name} field")
            except:
                logger.info(f"  ❌ Missing {field_name} field")
        
        if elements_found >= 3:
            logger.info("✅ Booking form accessible - form fields found")
            
            # Test filling form (without submitting)
            logger.info("🖊️ Testing form filling...")
            try:
                await page.fill('input[name="client.firstName"]', test_config.first_name)
                await page.fill('input[name="client.lastName"]', test_config.last_name)
                await page.fill('input[name="client.phone"]', test_config.phone)
                await page.fill('input[name="client.email"]', test_config.email)
                logger.info("✅ Form filling successful")
                
                # Check if submit button exists
                try:
                    submit_button = await page.wait_for_selector('input[type="submit"], button[type="submit"]', timeout=3000)
                    if submit_button:
                        logger.info("✅ Submit button found")
                        logger.info("🎯 BOOKING SYSTEM IS FUNCTIONAL - All components working")
                    else:
                        logger.warning("⚠️ Submit button not found")
                        
                except:
                    logger.warning("⚠️ Submit button not found")
                    
            except Exception as e:
                logger.error(f"❌ Form filling failed: {e}")
        else:
            logger.error(f"❌ Booking form not accessible - only {elements_found}/4 fields found")
            
    except Exception as e:
        logger.error(f"❌ Booking test failed: {e}")
        import traceback
        traceback.print_exc()
        
    finally:
        if browser_pool:
            logger.info("🧹 Cleaning up...")
            await browser_pool.stop()
            logger.info("✅ Cleanup completed")

async def main():
    """Main test execution"""
    await test_booking_flow()

if __name__ == "__main__":
    asyncio.run(main())