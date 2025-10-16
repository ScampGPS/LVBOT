#!/usr/bin/env python3
"""
Enhanced script to capture cancel/modify links from confirmation page
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
import os

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

async def capture_cancel_link():
    """Navigate to booking form and capture cancel/modify action details"""
    t('archive.scripts.playwright.capture_cancel_link.capture_cancel_link')
    async with async_playwright() as p:
        browser = await p.chromium.launch(
            headless=False,  # Show browser
            slow_mo=500
        )
        page = await browser.new_page()
        
        # Create output directory
        output_dir = "debugging/cancel_link_capture"
        os.makedirs(output_dir, exist_ok=True)
        
        # Court URLs
        court_urls = {
            1: "https://clublavilla.as.me/schedule/7d558012/appointment/15970897/calendar/4282490",
            2: "https://clublavilla.as.me/schedule/7d558012/appointment/16021953/calendar/4291312", 
            3: "https://clublavilla.as.me/schedule/7d558012/appointment/16120442/calendar/4307254"
        }
        
        # Test parameters
        court = 2
        target_date = datetime.now() + timedelta(days=1)
        target_time = "20:15"  # Evening time
        
        # Construct direct URL
        date_str = target_date.strftime("%Y-%m-%d")
        appointment_type_id = court_urls[court].split('/')[-2]
        direct_url = f"{court_urls[court]}/datetime/{date_str}T{target_time}:00-06:00?appointmentTypeIds[]={appointment_type_id}"
        
        logger.info(f"Navigating to: {direct_url}")
        
        try:
            # Navigate to form
            await page.goto(direct_url, wait_until='networkidle')
            await page.wait_for_timeout(3000)
            
            # Check for form
            form_present = await page.query_selector('form') is not None
            
            if form_present:
                logger.info("Form found - please complete the booking manually")
                logger.info("I will capture the confirmation page details")
                logger.info("Monitoring for MODIFICAR and CANCELAR buttons...")
                
                # Monitor for confirmation page
                confirmation_found = False
                check_count = 0
                
                while not confirmation_found and check_count < 300:  # 5 minutes max
                    await page.wait_for_timeout(1000)
                    check_count += 1
                    
                    # Look for specific buttons
                    modify_button = await page.query_selector('button:has-text("MODIFICAR"), a:has-text("MODIFICAR")')
                    cancel_button = await page.query_selector('button:has-text("CANCELAR"), a:has-text("CANCELAR")')
                    
                    if modify_button or cancel_button:
                        confirmation_found = True
                        logger.info("\n✅ CONFIRMATION PAGE WITH ACTION BUTTONS DETECTED!")
                        
                        # Wait a bit for page to fully load
                        await page.wait_for_timeout(2000)
                        
                        # Capture comprehensive button data
                        button_data = await page.evaluate('''() => {
                            const data = {
                                url: window.location.href,
                                timestamp: new Date().toISOString(),
                                buttons: [],
                                confirmationId: null
                            };
                            
                            // Extract confirmation ID from URL
                            const urlMatch = window.location.href.match(/confirmation\\/([a-zA-Z0-9]+)/);
                            if (urlMatch) {
                                data.confirmationId = urlMatch[1];
                            }
                            
                            // Find all buttons and links
                            const elements = document.querySelectorAll('button, a[role="button"], a');
                            
                            elements.forEach(el => {
                                const text = (el.innerText || el.textContent || '').trim();
                                if (text === 'MODIFICAR' || text === 'CANCELAR' || 
                                    text.toLowerCase().includes('modify') || text.toLowerCase().includes('cancel')) {
                                    
                                    const buttonInfo = {
                                        text: text,
                                        tagName: el.tagName,
                                        href: el.href || null,
                                        id: el.id || null,
                                        className: el.className || null,
                                        onclick: null,
                                        dataAttributes: {}
                                    };
                                    
                                    // Get onclick handler
                                    if (el.onclick) {
                                        buttonInfo.onclick = el.onclick.toString();
                                    }
                                    
                                    // Get all data attributes
                                    for (let attr of el.attributes) {
                                        if (attr.name.startsWith('data-')) {
                                            buttonInfo.dataAttributes[attr.name] = attr.value;
                                        }
                                    }
                                    
                                    // Try to find associated form or action
                                    const parentForm = el.closest('form');
                                    if (parentForm) {
                                        buttonInfo.formAction = parentForm.action || null;
                                        buttonInfo.formMethod = parentForm.method || null;
                                    }
                                    
                                    data.buttons.push(buttonInfo);
                                }
                            });
                            
                            return data;
                        }''')
                        
                        # Log the captured data
                        logger.info(f"\nConfirmation URL: {button_data['url']}")
                        logger.info(f"Confirmation ID: {button_data.get('confirmationId')}")
                        
                        # Monitor network for API calls when buttons are hovered
                        logger.info("\nHovering over buttons to capture any API calls...")
                        
                        # Set up request monitoring
                        api_calls = []
                        def capture_request(request):
                            t('archive.scripts.playwright.capture_cancel_link.capture_cancel_link.capture_request')
                            if 'api' in request.url or 'cancel' in request.url or 'modify' in request.url:
                                api_calls.append({
                                    'url': request.url,
                                    'method': request.method,
                                    'headers': dict(request.headers)
                                })
                        
                        page.on('request', capture_request)
                        
                        # Hover over buttons
                        if cancel_button:
                            await cancel_button.hover()
                            await page.wait_for_timeout(1000)
                        
                        if modify_button:
                            await modify_button.hover()
                            await page.wait_for_timeout(1000)
                        
                        # Take screenshot
                        await page.screenshot(path=f"{output_dir}/confirmation_with_buttons.png", full_page=True)
                        
                        # Try to intercept button click without actually clicking
                        intercept_data = await page.evaluate('''() => {
                            const data = {
                                cancelAction: null,
                                modifyAction: null
                            };
                            
                            // Find cancel button and get its action
                            const cancelBtn = Array.from(document.querySelectorAll('button, a')).find(
                                el => el.innerText && el.innerText.trim() === 'CANCELAR'
                            );
                            
                            if (cancelBtn) {
                                // Try to construct the cancel URL based on common patterns
                                const confirmationId = window.location.href.match(/confirmation\\/([a-zA-Z0-9]+)/)?.[1];
                                if (confirmationId) {
                                    // Common patterns for cancel URLs
                                    const baseUrl = window.location.origin + window.location.pathname.split('/confirmation')[0];
                                    data.cancelAction = {
                                        possibleUrls: [
                                            `${baseUrl}/cancel/${confirmationId}`,
                                            `${baseUrl}/appointment/cancel/${confirmationId}`,
                                            `${window.location.origin}/api/scheduling/v1/appointments/${confirmationId}/cancel`,
                                            `${window.location.href}/cancel`
                                        ],
                                        confirmationId: confirmationId
                                    };
                                }
                            }
                            
                            // Find modify button and get its action
                            const modifyBtn = Array.from(document.querySelectorAll('button, a')).find(
                                el => el.innerText && el.innerText.trim() === 'MODIFICAR'
                            );
                            
                            if (modifyBtn) {
                                const confirmationId = window.location.href.match(/confirmation\\/([a-zA-Z0-9]+)/)?.[1];
                                if (confirmationId) {
                                    const baseUrl = window.location.origin + window.location.pathname.split('/confirmation')[0];
                                    data.modifyAction = {
                                        possibleUrls: [
                                            `${baseUrl}/reschedule/${confirmationId}`,
                                            `${baseUrl}/appointment/reschedule/${confirmationId}`,
                                            `${window.location.origin}/api/scheduling/v1/appointments/${confirmationId}/reschedule`,
                                            `${window.location.href}/reschedule`
                                        ],
                                        confirmationId: confirmationId
                                    };
                                }
                            }
                            
                            return data;
                        }''')
                        
                        # Combine all data
                        final_data = {
                            'capturedAt': datetime.now().isoformat(),
                            'confirmationUrl': button_data['url'],
                            'confirmationId': button_data.get('confirmationId'),
                            'buttons': button_data['buttons'],
                            'interceptedActions': intercept_data,
                            'apiCallsDetected': api_calls,
                            'baseUrl': court_urls[court],
                            'appointmentTypeId': appointment_type_id
                        }
                        
                        # Save the data
                        with open(f"{output_dir}/cancel_link_data.json", "w", encoding="utf-8") as f:
                            json.dump(final_data, f, indent=2, ensure_ascii=False)
                        
                        # Log findings
                        logger.info("\n🔗 Button Details:")
                        for btn in button_data['buttons']:
                            logger.info(f"\n  Button: {btn['text']}")
                            logger.info(f"    Tag: {btn['tagName']}")
                            logger.info(f"    Href: {btn.get('href')}")
                            logger.info(f"    Data attributes: {btn.get('dataAttributes')}")
                        
                        if intercept_data['cancelAction']:
                            logger.info("\n❌ Cancel Action Analysis:")
                            logger.info(f"  Confirmation ID: {intercept_data['cancelAction']['confirmationId']}")
                            logger.info("  Possible Cancel URLs:")
                            for url in intercept_data['cancelAction']['possibleUrls']:
                                logger.info(f"    - {url}")
                        
                        break
                
                if not confirmation_found:
                    logger.warning("No confirmation page with action buttons detected after 5 minutes")
                    
            else:
                logger.error("No form found on the page")
                await page.screenshot(path=f"{output_dir}/no_form.png", full_page=True)
                
        except Exception as e:
            logger.error(f"Error: {e}", exc_info=True)
            await page.screenshot(path=f"{output_dir}/error.png", full_page=True)
        
        finally:
            logger.info(f"\nResults saved to: {output_dir}")
            input("\nPress Enter to close browser...")
            await browser.close()

if __name__ == "__main__":
    logger.info("Cancel Link Capture")
    logger.info("==================")
    logger.info("This will:")
    logger.info("1. Open the booking form")
    logger.info("2. Wait for you to complete the booking")
    logger.info("3. Capture MODIFICAR and CANCELAR button details")
    logger.info("4. Analyze possible cancel/modify URLs")
    asyncio.run(capture_cancel_link())
