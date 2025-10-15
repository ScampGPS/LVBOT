#!/usr/bin/env python3
"""
Test booking with screenshots at every step
This will show EXACTLY what happens during and after booking
"""

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

async def book_with_screenshots():
    """Book a slot and take screenshots at every critical step"""
    logger = logging.getLogger('BookingWithScreenshots')
    
    print("\n" + "="*80)
    print("BOOKING TEST WITH FULL SCREENSHOT DOCUMENTATION")
    print("="*80)
    print("This will capture EXACTLY what happens at each step")
    print("="*80 + "\n")
    
    # Create screenshots directory under the new testing artifact layout
    screenshots_dir_path = Path(__file__).resolve().parent.parent / "screencaps" / "booking_screenshots"
    screenshots_dir_path.mkdir(parents=True, exist_ok=True)
    screenshots_dir = str(screenshots_dir_path)
    print(f"Screenshots will be saved to: {screenshots_dir}/")
    
    # Import required modules
    from lvbot.utils.async_browser_pool import AsyncBrowserPool
    from lvbot.utils.working_booking_executor import WorkingBookingExecutor
    
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
    court_number = 1
    
    print(f"Target: Court {court_number} at {target_time} on {target_date.strftime('%Y-%m-%d')}")
    print("="*80 + "\n")
    
    # Initialize browser pool
    browser_pool = AsyncBrowserPool()
    await browser_pool.start()
    
    # Get page
    page = await browser_pool.get_page(court_number)
    if not page:
        logger.error("Could not get page!")
        return
    
    # Take initial screenshot
    await page.screenshot(path=f"{screenshots_dir}/01_initial_page.png", full_page=True)
    logger.info(f"Screenshot saved: 01_initial_page.png")
    
    try:
        # Step 1: Find time slot
        logger.info(f"Looking for {target_time} time slot...")
        time_button = await page.query_selector(f'button:has-text("{target_time}")')
        
        if not time_button:
            # Try alternative formats
            for alt_time in ['10', '10:00 AM', '10:00 am']:
                time_button = await page.query_selector(f'button:has-text("{alt_time}")')
                if time_button:
                    logger.info(f"Found with alternative format: {alt_time}")
                    break
        
        if not time_button:
            await page.screenshot(path=f"{screenshots_dir}/ERROR_no_time_slot.png", full_page=True)
            logger.error(f"Time slot {target_time} not found! Check ERROR_no_time_slot.png")
            return
        
        logger.info(f"Found {target_time} time slot!")
        
        # Highlight the button before clicking
        await page.evaluate('''(button) => {
            button.style.border = "3px solid red";
            button.style.backgroundColor = "yellow";
        }''', time_button)
        
        await page.screenshot(path=f"{screenshots_dir}/02_time_slot_highlighted.png", full_page=True)
        logger.info("Screenshot saved: 02_time_slot_highlighted.png")
        
        # Step 2: Click time slot
        logger.info("Clicking time slot...")
        await time_button.click()
        
        # Wait for navigation/form
        await asyncio.sleep(3)
        
        await page.screenshot(path=f"{screenshots_dir}/03_after_time_click.png", full_page=True)
        logger.info("Screenshot saved: 03_after_time_click.png")
        
        # Step 3: Check if form loaded
        logger.info("Checking for booking form...")
        
        # Look for form fields
        first_name_field = await page.query_selector('#client\\.firstName')
        if not first_name_field:
            logger.warning("Form not found with standard selector, trying alternatives...")
            first_name_field = await page.query_selector('input[name*="firstName"], input[name*="nombre"], input[id*="firstName"]')
        
        if first_name_field:
            logger.info("Booking form found!")
            await page.screenshot(path=f"{screenshots_dir}/04_booking_form.png", full_page=True)
            logger.info("Screenshot saved: 04_booking_form.png")
            
            # Fill form
            logger.info("Filling form...")
            
            # First name
            await first_name_field.fill('')
            await first_name_field.type(user_info['first_name'])
            
            # Last name
            last_name_field = await page.query_selector('#client\\.lastName')
            if last_name_field:
                await last_name_field.fill('')
                await last_name_field.type(user_info['last_name'])
            
            # Phone
            phone_field = await page.query_selector('#client\\.phone')
            if phone_field:
                await phone_field.fill('')
                await phone_field.type(user_info['phone'])
            
            # Email
            email_field = await page.query_selector('#client\\.email')
            if email_field:
                await email_field.fill('')
                await email_field.type(user_info['email'])
            
            await page.screenshot(path=f"{screenshots_dir}/05_form_filled.png", full_page=True)
            logger.info("Screenshot saved: 05_form_filled.png")
            
            # Find submit button
            submit_button = await page.query_selector('button:has-text("CONFIRMAR CITA"), button:has-text("Confirmar"), button:has-text("Submit")')
            
            if submit_button:
                # Highlight submit button
                await page.evaluate('''(button) => {
                    button.style.border = "3px solid green";
                    button.style.backgroundColor = "lightgreen";
                }''', submit_button)
                
                await page.screenshot(path=f"{screenshots_dir}/06_submit_highlighted.png", full_page=True)
                logger.info("Screenshot saved: 06_submit_highlighted.png")
                
                # Click submit
                logger.info("Submitting booking...")
                await submit_button.click()
                
                # Wait for response
                logger.info("Waiting for booking response...")
                await asyncio.sleep(5)
                
                # Take multiple screenshots after submission
                await page.screenshot(path=f"{screenshots_dir}/07_after_submit_5s.png", full_page=True)
                logger.info("Screenshot saved: 07_after_submit_5s.png")
                
                # Check current URL
                current_url = page.url
                logger.info(f"Current URL: {current_url}")
                
                # Get page content
                page_content = await page.content()
                
                # Save page HTML for analysis
                with open(f"{screenshots_dir}/08_page_content.html", 'w', encoding='utf-8') as f:
                    f.write(page_content)
                logger.info("Page HTML saved: 08_page_content.html")
                
                # Check for success indicators
                success_keywords = ['confirmado', 'confirmed', 'éxito', 'success', 'reserva', 'booking']
                error_keywords = ['error', 'failed', 'problema', 'unavailable', 'ocupado', 'taken']
                
                page_text = await page.inner_text('body')
                page_text_lower = page_text.lower()
                
                # Save page text
                with open(f"{screenshots_dir}/09_page_text.txt", 'w', encoding='utf-8') as f:
                    f.write(f"URL: {current_url}\n")
                    f.write(f"Page Text:\n{page_text}")
                logger.info("Page text saved: 09_page_text.txt")
                
                # Analyze result
                print("\n" + "="*80)
                print("BOOKING RESULT ANALYSIS:")
                print("="*80)
                print(f"URL changed: {'confirmation' in current_url or current_url != await browser_pool.get_page(court_number).url}")
                print(f"Success keywords found: {any(kw in page_text_lower for kw in success_keywords)}")
                print(f"Error keywords found: {any(kw in page_text_lower for kw in error_keywords)}")
                
                if 'confirmation' in current_url:
                    print(f"✅ CONFIRMATION URL DETECTED: {current_url}")
                
                for keyword in success_keywords:
                    if keyword in page_text_lower:
                        print(f"✅ Found success keyword: '{keyword}'")
                
                for keyword in error_keywords:
                    if keyword in page_text_lower:
                        print(f"❌ Found error keyword: '{keyword}'")
                
                # Extract any confirmation ID
                import re
                confirmation_patterns = [
                    r'confirmation[/:]+([a-zA-Z0-9]+)',
                    r'id[:\s]+([a-zA-Z0-9]+)',
                    r'número[:\s]+([a-zA-Z0-9]+)',
                    r'code[:\s]+([a-zA-Z0-9]+)'
                ]
                
                for pattern in confirmation_patterns:
                    match = re.search(pattern, page_text_lower)
                    if match:
                        print(f"📋 Possible confirmation ID: {match.group(1)}")
                
                print("="*80)
                
                # Wait a bit more and take final screenshot
                await asyncio.sleep(3)
                await page.screenshot(path=f"{screenshots_dir}/10_final_state.png", full_page=True)
                logger.info("Screenshot saved: 10_final_state.png")
                
            else:
                await page.screenshot(path=f"{screenshots_dir}/ERROR_no_submit_button.png", full_page=True)
                logger.error("Submit button not found! Check ERROR_no_submit_button.png")
        else:
            await page.screenshot(path=f"{screenshots_dir}/ERROR_no_form.png", full_page=True)
            logger.error("Booking form not found! Check ERROR_no_form.png")
            
    except Exception as e:
        await page.screenshot(path=f"{screenshots_dir}/ERROR_exception.png", full_page=True)
        logger.error(f"Exception occurred: {e}")
        import traceback
        traceback.print_exc()
    
    print(f"\n📸 All screenshots saved to: {screenshots_dir}/")
    print("Please check the screenshots to see EXACTLY what happened!")
    
    # Keep browser open
    print("\nBrowser will remain open. Press Ctrl+C to exit.")
    try:
        while True:
            await asyncio.sleep(1)
    except KeyboardInterrupt:
        if hasattr(browser_pool, 'close'):
            await browser_pool.close()

if __name__ == "__main__":
    asyncio.run(book_with_screenshots())
