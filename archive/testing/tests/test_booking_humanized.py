#!/usr/bin/env python3
"""
Test booking with humanized browser behavior
Includes warm-up delays and anti-bot measures
"""
from tracking import t

import asyncio
import logging
from datetime import datetime, timedelta
from pathlib import Path

# Setup logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    datefmt='%H:%M:%S'
)

async def test_humanized_booking():
    """Test booking with humanized behavior"""
    t('archive.testing.tests.test_booking_humanized.test_humanized_booking')
    logger = logging.getLogger('HumanizedBooking')
    
    print("\n" + "="*80)
    print("HUMANIZED BOOKING TEST")
    print("="*80)
    print("Features:")
    print("- 10 second browser warm-up on each court page")
    print("- Anti-webdriver detection measures")
    print("- Natural mouse movements and delays")
    print("- Realistic browser fingerprint")
    print("="*80 + "\n")
    
    # Import modules
    from lvbot.utils.async_browser_pool import AsyncBrowserPool
    from lvbot.utils.async_booking_executor import AsyncBookingExecutor
    
    # User info
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
    
    print(f"Target: Court {target_court} at {target_time} on {target_date.strftime('%Y-%m-%d')}")
    print(f"User: {user_info['first_name']} {user_info['last_name']}")
    print("="*80 + "\n")
    
    # Initialize browser pool
    logger.info("Initializing browser pool with warm-up...")
    browser_pool = AsyncBrowserPool()
    
    start_time = datetime.now()
    await browser_pool.start()
    init_time = (datetime.now() - start_time).total_seconds()
    
    logger.info(f"Browser pool initialized in {init_time:.1f} seconds (includes 10s warm-up per court)")
    
    # Create screenshots directory in the new consolidated testing layout
    screenshots_dir_path = Path(__file__).resolve().parent.parent / "screencaps" / "humanized_booking_screenshots"
    screenshots_dir_path.mkdir(parents=True, exist_ok=True)
    screenshots_dir = str(screenshots_dir_path)
    
    # Take screenshot of warmed-up page
    page = await browser_pool.get_page(target_court)
    if page:
        await page.screenshot(path=f"{screenshots_dir}/01_warmed_up_page.png", full_page=True)
        logger.info(f"Screenshot saved: 01_warmed_up_page.png")
    
    # Execute booking
    executor = AsyncBookingExecutor(browser_pool, use_natural_flow=False)
    
    logger.info("Starting booking execution...")
    booking_start = datetime.now()
    
    try:
        result = await executor.execute_booking(
            court_number=target_court,
            time_slot=target_time,
            user_info=user_info,
            target_date=target_date
        )
        
        booking_time = (datetime.now() - booking_start).total_seconds()
        
        # Take final screenshot
        if page:
            await page.screenshot(path=f"{screenshots_dir}/02_final_result.png", full_page=True)
            logger.info(f"Screenshot saved: 02_final_result.png")
            
            # Get page content for analysis
            page_content = await page.content()
            with open(f"{screenshots_dir}/page_content.html", 'w', encoding='utf-8') as f:
                f.write(page_content)
            
            # Check for anti-bot message
            page_text = await page.inner_text('body')
            if 'irregular' in page_text.lower() or 'detectó' in page_text.lower():
                logger.warning("⚠️ Anti-bot detection message found!")
            
        print("\n" + "="*80)
        print("BOOKING RESULT:")
        print(f"Execution time: {booking_time:.1f} seconds")
        
        if result.success:
            print("✅ BOOKING SUCCESSFUL!")
            if result.confirmation_id:
                print(f"Confirmation ID: {result.confirmation_id}")
            if result.message:
                print(f"Message: {result.message}")
        else:
            print("❌ BOOKING FAILED!")
            print(f"Error: {result.error_message}")
            
            # Check page for specific error
            if page:
                error_element = await page.query_selector('p[role="alert"]')
                if error_element:
                    error_text = await error_element.inner_text()
                    print(f"Page error: {error_text}")
                    
        print("="*80)
        
    except Exception as e:
        logger.error(f"Exception: {e}")
        import traceback
        traceback.print_exc()
    
    print(f"\n📸 Screenshots saved to: {screenshots_dir}/")
    print("\nBrowsers will remain open. Press Ctrl+C to exit.")
    
    try:
        while True:
            await asyncio.sleep(1)
    except KeyboardInterrupt:
        # Use correct cleanup method
        if hasattr(browser_pool, 'close'):
            await browser_pool.close()
        elif hasattr(browser_pool, 'cleanup'):
            await browser_pool.cleanup()
        logger.info("Test complete")

if __name__ == "__main__":
    asyncio.run(test_humanized_booking())
