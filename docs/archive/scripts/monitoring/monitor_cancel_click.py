#!/usr/bin/env python3
"""
Monitor what happens when CANCELAR button is clicked
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
import os

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

async def monitor_cancel_click():
    """Monitor the actual cancel button click"""
    async with async_playwright() as p:
        browser = await p.chromium.launch(
            headless=False,
            slow_mo=500
        )
        page = await browser.new_page()
        
        # Create output directory
        output_dir = "debugging/cancel_click_monitor"
        os.makedirs(output_dir, exist_ok=True)
        
        # Track all API calls
        api_calls = []
        
        def log_request(request):
            """Log all requests, especially API calls"""
            if any(keyword in request.url for keyword in ['api', 'cancel', 'delete', 'appointment']):
                api_calls.append({
                    'timestamp': datetime.now().isoformat(),
                    'method': request.method,
                    'url': request.url,
                    'headers': dict(request.headers),
                    'post_data': request.post_data
                })
                logger.info(f"API Call: {request.method} {request.url}")
        
        def log_response(response):
            """Log responses to tracked requests"""
            if any(keyword in response.url for keyword in ['api', 'cancel', 'delete', 'appointment']):
                logger.info(f"Response: {response.status} {response.url}")
        
        # Set up monitoring
        page.on('request', log_request)
        page.on('response', log_response)
        
        # Court URLs
        court_urls = {
            1: "https://clublavilla.as.me/schedule/7d558012/appointment/15970897/calendar/4282490",
            2: "https://clublavilla.as.me/schedule/7d558012/appointment/16021953/calendar/4291312", 
            3: "https://clublavilla.as.me/schedule/7d558012/appointment/16120442/calendar/4307254"
        }
        
        # Test parameters
        court = 2
        target_date = datetime.now() + timedelta(days=1)
        target_time = "20:30"  # Different time to avoid conflicts
        
        # Construct direct URL
        date_str = target_date.strftime("%Y-%m-%d")
        appointment_type_id = court_urls[court].split('/')[-2]
        direct_url = f"{court_urls[court]}/datetime/{date_str}T{target_time}:00-06:00?appointmentTypeIds[]={appointment_type_id}"
        
        logger.info("Cancel Button Click Monitor")
        logger.info("=" * 60)
        logger.info("Instructions:")
        logger.info("1. Complete a booking manually")
        logger.info("2. When you see the CANCELAR button, I'll click it")
        logger.info("3. I'll capture all network activity")
        logger.info("")
        
        try:
            # Navigate to form
            logger.info(f"Navigating to: {direct_url}")
            await page.goto(direct_url, wait_until='networkidle')
            
            # Wait for manual booking completion
            logger.info("Please complete the booking manually...")
            
            cancel_clicked = False
            check_count = 0
            
            while not cancel_clicked and check_count < 300:  # 5 minutes
                await page.wait_for_timeout(1000)
                check_count += 1
                
                # Look for CANCELAR button
                cancel_button = await page.query_selector('button:has-text("CANCELAR")')
                
                if cancel_button:
                    logger.info("\n✅ CANCELAR button found!")
                    
                    # Take pre-click screenshot
                    await page.screenshot(path=f"{output_dir}/01_before_cancel.png")
                    
                    # Clear previous API calls to focus on cancel action
                    api_calls.clear()
                    
                    # Wait for user confirmation
                    logger.info("\nPress Enter when ready to click CANCELAR...")
                    input()
                    
                    logger.info("Clicking CANCELAR button...")
                    
                    # Set up navigation promise
                    navigation_promise = page.wait_for_navigation(timeout=10000)
                    
                    try:
                        # Click the button
                        await cancel_button.click()
                        
                        # Wait for navigation or timeout
                        try:
                            await navigation_promise
                            logger.info("Navigation occurred after cancel click")
                        except:
                            logger.info("No navigation after cancel click (checking for API calls)")
                        
                        # Wait a bit for any API calls
                        await page.wait_for_timeout(3000)
                        
                        # Take post-click screenshot
                        await page.screenshot(path=f"{output_dir}/02_after_cancel.png")
                        
                        # Check current state
                        current_url = page.url
                        page_text = await page.inner_text('body')
                        
                        # Save all captured data
                        cancel_data = {
                            'clicked_at': datetime.now().isoformat(),
                            'pre_click_url': direct_url,
                            'post_click_url': current_url,
                            'url_changed': current_url != direct_url,
                            'api_calls': api_calls,
                            'page_text_sample': page_text[:500] if page_text else '',
                            'cancel_success': any(word in page_text.lower() for word in ['cancelada', 'cancelled', 'anulada'])
                        }
                        
                        with open(f"{output_dir}/cancel_click_data.json", "w", encoding="utf-8") as f:
                            json.dump(cancel_data, f, indent=2, ensure_ascii=False)
                        
                        # Log results
                        logger.info("\n" + "=" * 60)
                        logger.info("CANCEL CLICK RESULTS:")
                        logger.info(f"URL Changed: {cancel_data['url_changed']}")
                        if cancel_data['url_changed']:
                            logger.info(f"New URL: {current_url}")
                        
                        if api_calls:
                            logger.info(f"\n📡 API Calls Detected: {len(api_calls)}")
                            for call in api_calls:
                                logger.info(f"  {call['method']} {call['url']}")
                        else:
                            logger.info("\n❌ No API calls detected")
                        
                        if cancel_data['cancel_success']:
                            logger.info("\n✅ Cancellation appears successful!")
                        
                        cancel_clicked = True
                        
                    except Exception as e:
                        logger.error(f"Error clicking cancel: {e}")
                        await page.screenshot(path=f"{output_dir}/error.png")
                
            if not cancel_clicked:
                logger.warning("No CANCELAR button found after 5 minutes")
                
        except Exception as e:
            logger.error(f"Error: {e}", exc_info=True)
        
        finally:
            logger.info(f"\nResults saved to: {output_dir}")
            input("\nPress Enter to close browser...")
            await browser.close()

if __name__ == "__main__":
    asyncio.run(monitor_cancel_click())
