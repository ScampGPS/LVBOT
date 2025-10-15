#!/usr/bin/env python3
"""
Script to inspect what happens after booking form submission
"""
import pathlib
from pathlib import Path
import sys

ROOT_DIR = pathlib.Path(__file__).resolve().parents[2]
if str(ROOT_DIR) not in sys.path:
    sys.path.insert(0, str(ROOT_DIR))


import asyncio
import logging
from datetime import datetime, timedelta
from playwright.async_api import async_playwright
import json

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

async def inspect_post_booking():
    """Navigate to booking form and capture what happens after submission"""
    async with async_playwright() as p:
        browser = await p.chromium.launch(
            headless=False,  # Show browser
            slow_mo=500      # Slow down for visibility
        )
        page = await browser.new_page()
        
        # Enable console logging
        page.on('console', lambda msg: logger.info(f"Browser console: {msg.text}"))
        
        # Court URLs
        court_urls = {
            1: "https://clublavilla.as.me/schedule/7d558012/appointment/15970897/calendar/4282490",
            2: "https://clublavilla.as.me/schedule/7d558012/appointment/16021953/calendar/4291312", 
            3: "https://clublavilla.as.me/schedule/7d558012/appointment/16120442/calendar/4307254"
        }
        
        # Test with court 2
        court = 2
        target_date = datetime.now() + timedelta(days=1)
        target_time = "10:00"  # Pick a common time
        
        # Construct direct URL
        date_str = target_date.strftime("%Y-%m-%d")
        appointment_type_id = court_urls[court].split('/')[-2]
        direct_url = f"{court_urls[court]}/datetime/{date_str}T{target_time}:00-06:00?appointmentTypeIds[]={appointment_type_id}"
        
        logger.info(f"Navigating to: {direct_url}")
        
        try:
            # Navigate to form
            await page.goto(direct_url, wait_until='networkidle')
            await page.wait_for_timeout(3000)
            
            # Take screenshot of form
            await page.screenshot(path="debugging/booking_form_before.png", full_page=True)
            logger.info("Screenshot saved: debugging/booking_form_before.png")
            
            # Fill form
            logger.info("Filling form...")
            await page.fill('input[name="client.firstName"]', "Test")
            await page.fill('input[name="client.lastName"]', "User")
            await page.fill('input[name="client.phone"]', "31874277")
            await page.fill('input[name="client.email"]', "test@example.com")
            
            # Find submit button
            submit_button = await page.query_selector('button:has-text("CONFIRMAR CITA"), button:has-text("Confirmar cita")')
            
            if submit_button:
                logger.info("\n" + "="*60)
                logger.info("READY TO SUBMIT - Press Enter to click submit button")
                logger.info("I will capture everything that happens after submission")
                logger.info("="*60)
                input("\nPress Enter to submit the form...")
                
                # Set up monitoring before clicking
                page_changed = False
                original_url = page.url
                
                # Monitor for any changes
                async def monitor_changes():
                    nonlocal page_changed
                    await asyncio.sleep(0.5)
                    if page.url != original_url:
                        page_changed = True
                        logger.info(f"URL changed to: {page.url}")
                
                # Start monitoring
                monitor_task = asyncio.create_task(monitor_changes())
                
                # Click submit
                logger.info("Clicking submit button...")
                await submit_button.click()
                
                # Wait and capture what happens
                for i in range(20):  # Monitor for 20 seconds
                    await page.wait_for_timeout(1000)
                    
                    # Take periodic screenshots
                    if i % 2 == 0:  # Every 2 seconds
                        screenshot_path = f"debugging/post_submit_{i//2:02d}.png"
                        await page.screenshot(path=screenshot_path, full_page=True)
                        logger.info(f"Screenshot: {screenshot_path}")
                    
                    # Check current state
                    current_url = page.url
                    
                    # Extract all text content
                    text_content = await page.evaluate('''() => {
                        return document.body ? document.body.innerText : '';
                    }''')
                    
                    # Look for specific elements
                    success_elements = await page.query_selector_all('[class*="success"], [class*="confirm"], [class*="thank"]')
                    error_elements = await page.query_selector_all('[class*="error"], [class*="fail"]')
                    
                    # Extract any messages
                    messages = await page.evaluate('''() => {
                        const messageElements = document.querySelectorAll('h1, h2, h3, p, div[role="alert"], .message, .notification');
                        return Array.from(messageElements).map(el => ({
                            tag: el.tagName,
                            text: el.innerText || el.textContent,
                            className: el.className
                        })).filter(msg => msg.text && msg.text.trim().length > 0);
                    }''')
                    
                    if i == 0 or i % 5 == 0:  # Log detailed info every 5 seconds
                        logger.info(f"\n--- Status at {i} seconds ---")
                        logger.info(f"URL: {current_url}")
                        logger.info(f"Success elements found: {len(success_elements)}")
                        logger.info(f"Error elements found: {len(error_elements)}")
                        if messages:
                            logger.info("Messages found:")
                            for msg in messages[:10]:  # First 10 messages
                                logger.info(f"  {msg['tag']}: {msg['text'][:100]}...")
                    
                    # Save full page content
                    if i == 5:  # After 5 seconds
                        with open("debugging/post_submit_content.txt", "w", encoding="utf-8") as f:
                            f.write(f"URL: {current_url}\n\n")
                            f.write(f"Full text content:\n{text_content}\n\n")
                            f.write(f"Messages found:\n{json.dumps(messages, indent=2, ensure_ascii=False)}")
                        logger.info("Full content saved to debugging/post_submit_content.txt")
                    
                    # Check for specific Acuity confirmation patterns
                    confirmation_patterns = [
                        "confirmación",
                        "confirmado",
                        "recibirá un correo",
                        "email de confirmación",
                        "gracias por",
                        "thank you",
                        "confirmation email",
                        "successfully booked"
                    ]
                    
                    for pattern in confirmation_patterns:
                        if pattern.lower() in text_content.lower():
                            logger.info(f"✅ Found confirmation pattern: '{pattern}'")
                
                # Final state
                logger.info("\n" + "="*60)
                logger.info("FINAL STATE:")
                logger.info(f"Final URL: {page.url}")
                logger.info(f"URL changed: {page.url != original_url}")
                
                # Final screenshot
                await page.screenshot(path="debugging/booking_final_state.png", full_page=True)
                logger.info("Final screenshot: debugging/booking_final_state.png")
                
            else:
                logger.error("Submit button not found!")
                
        except Exception as e:
            logger.error(f"Error: {e}", exc_info=True)
            await page.screenshot(path="debugging/error_state.png", full_page=True)
        
        finally:
            input("\nPress Enter to close browser...")
            await browser.close()

if __name__ == "__main__":
    import os
    os.makedirs("debugging", exist_ok=True)
    logger.info("Starting post-booking page inspector...")
    logger.info("This will help us understand what happens after form submission")
    asyncio.run(inspect_post_booking())
