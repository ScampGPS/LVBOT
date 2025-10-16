#!/usr/bin/env python3
"""
Script to inspect what happens after booking form submission (automatic version)
"""
from utils.tracking import t
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
    t('archive.scripts.maintenance.inspect_post_booking_auto.inspect_post_booking')
    async with async_playwright() as p:
        browser = await p.chromium.launch(
            headless=True,  # Run headless
            slow_mo=500     # Slow down for reliability
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
        target_time = "20:15"  # Pick an evening time that's likely available
        
        # Construct direct URL
        date_str = target_date.strftime("%Y-%m-%d")
        appointment_type_id = court_urls[court].split('/')[-2]
        direct_url = f"{court_urls[court]}/datetime/{date_str}T{target_time}:00-06:00?appointmentTypeIds[]={appointment_type_id}"
        
        logger.info(f"Navigating to: {direct_url}")
        
        try:
            # Navigate to form
            response = await page.goto(direct_url, wait_until='networkidle')
            if response and response.status != 200:
                logger.warning(f"Got status {response.status} - time slot might not be available")
            
            await page.wait_for_timeout(3000)
            
            # Check if we're on the form page
            form_fields = await page.query_selector('input[name="client.firstName"]')
            if not form_fields:
                logger.error("Form not found - time slot might not be available")
                # Try a different time
                target_time = "11:00"
                direct_url = f"{court_urls[court]}/datetime/{date_str}T{target_time}:00-06:00?appointmentTypeIds[]={appointment_type_id}"
                logger.info(f"Trying different time: {direct_url}")
                await page.goto(direct_url, wait_until='networkidle')
                await page.wait_for_timeout(3000)
            
            # Take screenshot of form
            await page.screenshot(path="debugging/booking_form_before.png", full_page=True)
            logger.info("Screenshot saved: debugging/booking_form_before.png")
            
            # Fill form
            logger.info("Filling form...")
            await page.fill('input[name="client.firstName"]', "Test")
            await page.fill('input[name="client.lastName"]', "Automated")
            await page.fill('input[name="client.phone"]', "31874277")
            await page.fill('input[name="client.email"]', "automated-test@example.com")
            
            # Find submit button
            submit_button = await page.query_selector('button:has-text("CONFIRMAR CITA"), button:has-text("Confirmar cita")')
            
            if submit_button:
                logger.info("Found submit button - clicking in 2 seconds...")
                await page.wait_for_timeout(2000)
                
                # Set up monitoring before clicking
                original_url = page.url
                
                # Click submit without waiting for navigation
                logger.info("Clicking submit button...")
                await submit_button.click()
                
                # Monitor what happens for 15 seconds
                logger.info("Monitoring post-submission state...")
                
                for i in range(15):  # Monitor for 15 seconds
                    await page.wait_for_timeout(1000)
                    
                    # Take screenshots at key moments
                    if i in [0, 2, 5, 10, 14]:
                        screenshot_path = f"debugging/post_submit_{i:02d}s.png"
                        await page.screenshot(path=screenshot_path, full_page=True)
                        logger.info(f"Screenshot at {i}s: {screenshot_path}")
                    
                    # Check current state
                    current_url = page.url
                    
                    # Extract all text content
                    text_content = await page.evaluate('''() => {
                        return document.body ? document.body.innerText : '';
                    }''')
                    
                    # Look for specific confirmation patterns
                    confirmation_found = False
                    confirmation_patterns = [
                        "confirmación",
                        "confirmado", 
                        "recibirá un correo",
                        "email de confirmación",
                        "gracias por",
                        "thank you",
                        "confirmation email",
                        "successfully",
                        "recibirás",
                        "enviado",
                        "scheduled"
                    ]
                    
                    for pattern in confirmation_patterns:
                        if pattern.lower() in text_content.lower():
                            logger.info(f"✅ Found confirmation pattern: '{pattern}'")
                            confirmation_found = True
                            
                            # Extract the context around the pattern
                            lines = text_content.split('\n')
                            for idx, line in enumerate(lines):
                                if pattern.lower() in line.lower():
                                    logger.info(f"Context: {line.strip()}")
                                    # Get surrounding lines
                                    if idx > 0:
                                        logger.info(f"Previous: {lines[idx-1].strip()}")
                                    if idx < len(lines) - 1:
                                        logger.info(f"Next: {lines[idx+1].strip()}")
                    
                    # Save detailed info at 5 seconds
                    if i == 5:
                        # Extract all visible text elements
                        visible_texts = await page.evaluate('''() => {
                            const elements = document.querySelectorAll('*');
                            const texts = [];
                            for (const el of elements) {
                                if (el.offsetParent !== null && el.innerText && el.innerText.trim()) {
                                    const style = window.getComputedStyle(el);
                                    if (style.display !== 'none' && style.visibility !== 'hidden') {
                                        texts.push({
                                            tag: el.tagName,
                                            text: el.innerText.trim(),
                                            className: el.className
                                        });
                                    }
                                }
                            }
                            return texts;
                        }''')
                        
                        with open("debugging/post_submit_analysis.json", "w", encoding="utf-8") as f:
                            json.dump({
                                "url": current_url,
                                "url_changed": current_url != original_url,
                                "confirmation_found": confirmation_found,
                                "full_text": text_content,
                                "visible_elements": visible_texts[:50]  # First 50 elements
                            }, f, indent=2, ensure_ascii=False)
                        logger.info("Detailed analysis saved to debugging/post_submit_analysis.json")
                    
                    # Check if URL changed
                    if current_url != original_url and i == 2:
                        logger.info(f"URL changed from {original_url} to {current_url}")
                
                # Final analysis
                logger.info("\n" + "="*60)
                logger.info("FINAL ANALYSIS:")
                logger.info(f"Original URL: {original_url}")
                logger.info(f"Final URL: {page.url}")
                logger.info(f"URL changed: {page.url != original_url}")
                logger.info(f"Confirmation found: {confirmation_found}")
                
                # Try to extract any email-related messages
                email_patterns = await page.evaluate('''() => {
                    const patterns = ['email', 'correo', 'e-mail', 'notification', 'notificación'];
                    const found = [];
                    const elements = document.querySelectorAll('*');
                    for (const el of elements) {
                        const text = el.innerText || el.textContent || '';
                        for (const pattern of patterns) {
                            if (text.toLowerCase().includes(pattern)) {
                                found.push({
                                    element: el.tagName,
                                    text: text.substring(0, 200)
                                });
                                break;
                            }
                        }
                    }
                    return found.slice(0, 10);  // First 10 matches
                }''')
                
                if email_patterns:
                    logger.info("\nEmail/Notification related messages found:")
                    for item in email_patterns:
                        logger.info(f"- {item['element']}: {item['text']}")
                
            else:
                logger.error("Submit button not found!")
                await page.screenshot(path="debugging/no_submit_button.png", full_page=True)
                
        except Exception as e:
            logger.error(f"Error: {e}", exc_info=True)
            await page.screenshot(path="debugging/error_state.png", full_page=True)
        
        finally:
            await browser.close()
            logger.info("\nInspection complete. Check the debugging/ folder for results.")

if __name__ == "__main__":
    import os
    os.makedirs("debugging", exist_ok=True)
    logger.info("Starting automated post-booking page inspector...")
    asyncio.run(inspect_post_booking())
