#!/usr/bin/env python3
"""
Focused test for email typing speed limits
Tests only the email field typing speed in isolation
"""
from tracking import t

import asyncio
import logging
import time
import random
from playwright.async_api import async_playwright

# Setup logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    datefmt='%H:%M:%S'
)

async def test_email_typing_speed(speed_multiplier: float, email_text: str = "msaulcampos@gmail.com"):
    """Test email typing at a specific speed on a test form"""
    t('archive.testing.tests.test_email_speed_focused.test_email_typing_speed')
    logger = logging.getLogger('EmailSpeedTest')
    
    async with async_playwright() as p:
        # Launch browser
        browser = await p.chromium.launch(
            headless=False,
            args=[
                '--disable-blink-features=AutomationControlled',
                '--disable-features=IsolateOrigins,site-per-process',
                '--no-sandbox',
                '--disable-setuid-sandbox',
                '--disable-dev-shm-usage'
            ]
        )
        
        context = await browser.new_context(
            viewport={'width': 1280, 'height': 800},
            user_agent='Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36'
        )
        
        page = await context.new_page()
        
        # Navigate to the booking site
        await page.goto('https://clublavilla.as.me/schedule/7d558012/appointment/16021953')
        
        # Wait for page to load and find any available time slot
        await page.wait_for_selector('button[class*="time"]', timeout=30000)
        
        # Click first available time slot
        time_buttons = await page.query_selector_all('button[class*="time"]')
        if time_buttons:
            await time_buttons[0].click()
            logger.info("Clicked on available time slot")
        else:
            logger.error("No time slots available")
            await browser.close()
            return False, 0, False, "No slots"
        
        # Wait for form
        try:
            await page.wait_for_selector('#client\\.email', timeout=10000)
        except:
            logger.error("Form did not load")
            await browser.close()
            return False, 0, False, "Form not loaded"
        
        # Test email typing speed
        email_field = await page.query_selector('#client\\.email')
        if not email_field:
            logger.error("Email field not found")
            await browser.close()
            return False, 0, False, "Email field not found"
        
        # Time the email typing
        start_time = time.time()
        
        # Click and clear
        await email_field.click()
        await asyncio.sleep(0.1)
        await email_field.fill('')
        
        # Type email with specified speed
        for char in email_text:
            # Base delay 90-220ms divided by speed multiplier
            base_delay = random.randint(90, 220) / speed_multiplier
            await email_field.type(char, delay=max(10, int(base_delay)))
            
            # Occasional thinking pause
            if random.random() < (0.1 / speed_multiplier):
                await asyncio.sleep(random.uniform(0.2, 0.5) / speed_multiplier)
        
        typing_time = time.time() - start_time
        logger.info(f"Email typed in {typing_time:.2f}s at {speed_multiplier}x speed")
        
        # Wait a moment
        await asyncio.sleep(2)
        
        # Check for bot detection
        bot_detected = False
        error_msg = ""
        
        try:
            # Take screenshot
            await page.screenshot(path=f'/mnt/c/Documents/code/python/lvbot/email_test_{speed_multiplier}x.png')
            
            # Check for error messages
            error_element = await page.query_selector('p[role="alert"]')
            if error_element:
                error_text = await error_element.inner_text()
                if 'irregular' in error_text.lower() or 'detectó' in error_text.lower():
                    bot_detected = True
                    error_msg = error_text
            
            # Check page content
            page_text = await page.inner_text('body')
            if 'irregular' in page_text.lower() and not bot_detected:
                bot_detected = True
                error_msg = "Bot detection in page"
        except Exception as e:
            logger.warning(f"Error checking detection: {e}")
        
        await browser.close()
        
        return not bot_detected, typing_time, bot_detected, error_msg

async def main():
    """Test multiple email typing speeds"""
    t('archive.testing.tests.test_email_speed_focused.main')
    
    print("\n" + "="*80)
    print("EMAIL TYPING SPEED ANALYSIS")
    print("="*80)
    print("Testing email field typing at different speeds")
    print("Email: msaulcampos@gmail.com (21 characters)")
    print("="*80 + "\n")
    
    # Test speeds from safe to aggressive
    test_speeds = [2.5, 3.0, 4.0, 5.0, 7.0, 10.0]
    results = []
    
    for speed in test_speeds:
        print(f"\nTesting {speed}x speed...")
        
        success, typing_time, bot_detected, error = await test_email_typing_speed(speed)
        
        results.append({
            'speed': speed,
            'time': typing_time,
            'success': success,
            'bot_detected': bot_detected,
            'error': error
        })
        
        print(f"Result: {'✅ SAFE' if success else '❌ DETECTED'}")
        print(f"Typing time: {typing_time:.2f}s")
        if error:
            print(f"Error: {error}")
        
        if bot_detected:
            print("\n⚠️ Bot detection triggered!")
            break
        
        # Wait between tests
        if speed != test_speeds[-1]:
            print("Waiting 10s...")
            await asyncio.sleep(10)
    
    # Summary
    print("\n" + "="*80)
    print("EMAIL SPEED TEST RESULTS")
    print("="*80)
    print(f"{'Speed':<8} {'Time (s)':<10} {'Status':<15} {'Notes':<30}")
    print("-"*80)
    
    max_safe = 2.5
    for r in results:
        status = "✅ SAFE" if r['success'] else "❌ DETECTED"
        notes = r['error'] if r['error'] else ""
        print(f"{r['speed']:<8} {r['time']:<10.2f} {status:<15} {notes:<30}")
        
        if r['success']:
            max_safe = r['speed']
    
    print("="*80)
    print(f"\n🎯 MAXIMUM SAFE SPEED: {max_safe}x")
    
    # Calculate savings
    baseline_time = results[0]['time'] if results else 10.4
    optimized_time = baseline_time * (2.5 / max_safe) if max_safe > 2.5 else baseline_time
    savings = baseline_time - optimized_time
    
    print(f"\n📊 POTENTIAL OPTIMIZATION:")
    print(f"   Current (2.5x): {baseline_time:.2f}s")
    print(f"   Optimized ({max_safe}x): {optimized_time:.2f}s")
    print(f"   Time saved: {savings:.2f}s")
    print(f"   Total booking: ~{40.2 - savings:.1f}s (from 40.2s)")

if __name__ == "__main__":
    asyncio.run(main())