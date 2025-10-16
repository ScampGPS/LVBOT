#!/usr/bin/env python3
"""
Debug slow navigation to booking URL with screenshots and network monitoring
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
import time
from datetime import datetime
from playwright.async_api import async_playwright
import os

# Set up logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

async def debug_navigation():
    """Debug the slow navigation issue with detailed monitoring"""
    t('archive.scripts.diagnostics.debug_slow_navigation.debug_navigation')
    
    # Create output directory for screenshots
    output_dir = f"navigation_debug_{datetime.now().strftime('%Y%m%d_%H%M%S')}"
    os.makedirs(output_dir, exist_ok=True)
    logger.info(f"Screenshots will be saved to: {output_dir}")
    
    # The problematic URL
    direct_url = "https://clublavilla.as.me/schedule/7d558012/appointment/15970897/calendar/4291312/datetime/2025-07-30T10:00:00-06:00?appointmentTypeIds[]=15970897"
    
    async with async_playwright() as p:
        # Launch browser with debugging options
        browser = await p.chromium.launch(
            headless=False,  # Show browser for visual debugging
            args=[
                '--disable-blink-features=AutomationControlled',
                '--disable-features=IsolateOrigins,site-per-process',
                '--no-sandbox'
            ]
        )
        
        context = await browser.new_context(
            viewport={'width': 1280, 'height': 720},
            user_agent='Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36'
        )
        
        # Enable request/response logging
        page = await context.new_page()
        
        # Track all network requests
        requests = []
        responses = []
        redirects = []
        
        # Network event handlers
        async def on_request(request):
            t('archive.scripts.diagnostics.debug_slow_navigation.debug_navigation.on_request')
            requests.append({
                'time': time.time(),
                'url': request.url,
                'method': request.method,
                'resource_type': request.resource_type
            })
            logger.info(f"REQUEST: {request.method} {request.url[:100]}... [{request.resource_type}]")
        
        async def on_response(response):
            t('archive.scripts.diagnostics.debug_slow_navigation.debug_navigation.on_response')
            responses.append({
                'time': time.time(),
                'url': response.url,
                'status': response.status,
                'ok': response.ok
            })
            logger.info(f"RESPONSE: {response.status} {response.url[:100]}...")
            
            # Check for redirects
            if 300 <= response.status < 400:
                location = response.headers.get('location', 'N/A')
                redirects.append({
                    'from': response.url,
                    'to': location,
                    'status': response.status
                })
                logger.warning(f"REDIRECT {response.status}: {response.url} -> {location}")
        
        async def on_request_failed(request):
            t('archive.scripts.diagnostics.debug_slow_navigation.debug_navigation.on_request_failed')
            logger.error(f"REQUEST FAILED: {request.url} - {request.failure}")
        
        async def on_request_finished(request):
            t('archive.scripts.diagnostics.debug_slow_navigation.debug_navigation.on_request_finished')
            response = await request.response()
            if response:
                timing = response.request.timing
                if timing:
                    logger.debug(f"TIMING for {request.url[:50]}...: {timing}")
        
        # Attach event handlers
        page.on("request", on_request)
        page.on("response", on_response)
        page.on("requestfailed", on_request_failed)
        page.on("requestfinished", on_request_finished)
        
        # Monitor console messages
        page.on("console", lambda msg: logger.info(f"CONSOLE: {msg.text}"))
        
        # Try different navigation strategies
        logger.info("\n=== TESTING NAVIGATION STRATEGIES ===\n")
        
        # Strategy 1: Default navigation with networkidle
        logger.info("Strategy 1: Default with networkidle")
        start_time = time.time()
        
        try:
            # Take screenshot before navigation
            await page.screenshot(path=f"{output_dir}/01_before_navigation.png")
            
            # Start navigation
            logger.info("Starting navigation...")
            response = await page.goto(direct_url, wait_until='networkidle', timeout=120000)  # 2 minute timeout
            
            nav_time = time.time() - start_time
            logger.info(f"✅ Navigation completed in {nav_time:.2f}s")
            
            # Take screenshots after navigation
            await page.screenshot(path=f"{output_dir}/02_after_navigation.png", full_page=True)
            
            # Log final URL and status
            logger.info(f"Final URL: {page.url}")
            logger.info(f"Response status: {response.status if response else 'None'}")
            
            # Check page content
            title = await page.title()
            logger.info(f"Page title: {title}")
            
            # Check for form presence
            form_present = await page.locator('form').count() > 0
            logger.info(f"Form present: {form_present}")
            
            # Check for any blocking elements
            blocking_elements = await page.locator('.loading, .spinner, [class*="load"], [class*="wait"]').all()
            if blocking_elements:
                logger.warning(f"Found {len(blocking_elements)} potential blocking elements")
                for i, elem in enumerate(blocking_elements):
                    classes = await elem.get_attribute('class')
                    logger.warning(f"  Blocking element {i+1}: {classes}")
            
        except Exception as e:
            nav_time = time.time() - start_time
            logger.error(f"Navigation failed after {nav_time:.2f}s: {e}")
            await page.screenshot(path=f"{output_dir}/error_state.png", full_page=True)
        
        # Log network summary
        logger.info("\n=== NETWORK SUMMARY ===")
        logger.info(f"Total requests: {len(requests)}")
        logger.info(f"Total responses: {len(responses)}")
        logger.info(f"Redirects: {len(redirects)}")
        
        # Find slow requests
        logger.info("\n=== SLOW REQUESTS (>5s) ===")
        for i in range(len(requests)):
            req = requests[i]
            # Find matching response
            resp = next((r for r in responses if r['url'] == req['url']), None)
            if resp:
                duration = resp['time'] - req['time']
                if duration > 5:
                    logger.warning(f"SLOW: {req['url'][:80]}... took {duration:.2f}s")
        
        # Test alternative strategies
        logger.info("\n=== TESTING ALTERNATIVE STRATEGIES ===\n")
        
        # Strategy 2: domcontentloaded only
        logger.info("Strategy 2: domcontentloaded only")
        await page.goto('about:blank')  # Reset
        start_time = time.time()
        
        try:
            response = await page.goto(direct_url, wait_until='domcontentloaded', timeout=30000)
            nav_time = time.time() - start_time
            logger.info(f"✅ Navigation (domcontentloaded) completed in {nav_time:.2f}s")
            
            # Wait a bit for dynamic content
            await page.wait_for_timeout(3000)
            await page.screenshot(path=f"{output_dir}/03_domcontentloaded.png", full_page=True)
            
            # Check form presence again
            form_present = await page.locator('form').count() > 0
            logger.info(f"Form present after domcontentloaded: {form_present}")
            
        except Exception as e:
            nav_time = time.time() - start_time
            logger.error(f"Navigation (domcontentloaded) failed after {nav_time:.2f}s: {e}")
        
        # Strategy 3: commit only (fastest)
        logger.info("\nStrategy 3: commit only")
        await page.goto('about:blank')  # Reset
        start_time = time.time()
        
        try:
            response = await page.goto(direct_url, wait_until='commit', timeout=30000)
            nav_time = time.time() - start_time
            logger.info(f"✅ Navigation (commit) completed in {nav_time:.2f}s")
            
            # Wait for form to appear
            try:
                await page.wait_for_selector('form', timeout=10000)
                logger.info("Form appeared!")
            except:
                logger.warning("Form did not appear within 10s")
            
            await page.screenshot(path=f"{output_dir}/04_commit_with_wait.png", full_page=True)
            
        except Exception as e:
            nav_time = time.time() - start_time
            logger.error(f"Navigation (commit) failed after {nav_time:.2f}s: {e}")
        
        # Check for anti-bot measures
        logger.info("\n=== CHECKING FOR ANTI-BOT MEASURES ===")
        
        # Check for Cloudflare
        cloudflare_challenge = await page.locator('text=/cloudflare|cf-challenge|checking your browser/i').count()
        if cloudflare_challenge:
            logger.warning("⚠️ Cloudflare challenge detected!")
            await page.screenshot(path=f"{output_dir}/cloudflare_challenge.png", full_page=True)
        
        # Check for reCAPTCHA
        recaptcha = await page.locator('iframe[src*="recaptcha"]').count()
        if recaptcha:
            logger.warning("⚠️ reCAPTCHA detected!")
        
        # Final state screenshot
        await page.screenshot(path=f"{output_dir}/05_final_state.png", full_page=True)
        
        # Keep browser open for manual inspection
        logger.info("\n=== KEEPING BROWSER OPEN FOR 30 SECONDS ===")
        logger.info("Check the browser window for any visual issues...")
        await asyncio.sleep(30)
        
        await browser.close()
        
    logger.info(f"\n✅ Debug session complete. Check screenshots in: {output_dir}")

if __name__ == "__main__":
    asyncio.run(debug_navigation())
