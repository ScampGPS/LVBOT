#!/usr/bin/env python3
"""
Script to monitor manual booking - logs all events, fields, and information
while you perform a manual booking
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

logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(message)s')
logger = logging.getLogger(__name__)

async def monitor_manual_booking():
    """Launch browser and monitor manual booking interactions"""
    t('archive.scripts.monitoring.monitor_manual_booking.monitor_manual_booking')
    async with async_playwright() as p:
        browser = await p.chromium.launch(
            headless=False,  # Show browser
            args=['--start-maximized']
        )
        context = await browser.new_context(
            viewport={'width': 1920, 'height': 1080},
            record_video_dir="debugging/manual_booking_video"
        )
        page = await context.new_page()
        
        # Create output directory
        output_dir = f"debugging/manual_booking_{datetime.now().strftime('%Y%m%d_%H%M%S')}"
        os.makedirs(output_dir, exist_ok=True)
        
        # Log file
        log_file = open(f"{output_dir}/events.log", "w", encoding="utf-8")
        
        def log_event(event_type, data):
            """Log event to console and file"""
            t('archive.scripts.monitoring.monitor_manual_booking.monitor_manual_booking.log_event')
            timestamp = datetime.now().strftime("%H:%M:%S.%f")[:-3]
            log_entry = f"[{timestamp}] {event_type}: {json.dumps(data, ensure_ascii=False)}"
            logger.info(log_entry)
            log_file.write(log_entry + "\n")
            log_file.flush()
        
        # Monitor console messages
        page.on('console', lambda msg: log_event('CONSOLE', {
            'type': msg.type,
            'text': msg.text,
            'location': f"{msg.location.get('url', '')}:{msg.location.get('lineNumber', '')}"
        }))
        
        # Monitor navigation
        page.on('framenavigated', lambda frame: log_event('NAVIGATION', {
            'url': frame.url,
            'name': frame.name,
            'is_main': frame == page.main_frame
        }))
        
        # Monitor requests
        page.on('request', lambda req: log_event('REQUEST', {
            'method': req.method,
            'url': req.url,
            'type': req.resource_type,
            'post_data': req.post_data if req.method == 'POST' else None
        }))
        
        # Monitor responses
        page.on('response', lambda resp: log_event('RESPONSE', {
            'status': resp.status,
            'url': resp.url,
            'ok': resp.ok,
            'type': resp.headers.get('content-type', '')
        }))
        
        # Monitor DOM content loaded
        page.on('domcontentloaded', lambda: log_event('DOM_LOADED', {'url': page.url}))
        
        # Monitor load event
        page.on('load', lambda: log_event('PAGE_LOADED', {'url': page.url}))
        
        # Court URLs
        court_urls = {
            1: "https://clublavilla.as.me/schedule/7d558012/appointment/15970897/calendar/4282490",
            2: "https://clublavilla.as.me/schedule/7d558012/appointment/16021953/calendar/4291312", 
            3: "https://clublavilla.as.me/schedule/7d558012/appointment/16120442/calendar/4307254"
        }
        
        # Test parameters
        court = 2
        target_date = datetime.now() + timedelta(days=1)
        target_time = "10:00"
        
        # Construct direct URL
        date_str = target_date.strftime("%Y-%m-%d")
        appointment_type_id = court_urls[court].split('/')[-2]
        direct_url = f"{court_urls[court]}/datetime/{date_str}T{target_time}:00-06:00?appointmentTypeIds[]={appointment_type_id}"
        
        logger.info("="*80)
        logger.info("MANUAL BOOKING MONITOR")
        logger.info(f"Direct URL: {direct_url}")
        logger.info(f"Court: {court}")
        logger.info(f"Date: {date_str}")
        logger.info(f"Time: {target_time}")
        logger.info("="*80)
        
        try:
            # Navigate to URL
            log_event('NAVIGATING', {'url': direct_url})
            await page.goto(direct_url, wait_until='networkidle', timeout=30000)
            
            # Initial screenshot
            await page.screenshot(path=f"{output_dir}/01_initial.png", full_page=True)
            
            # Periodic monitoring
            screenshot_count = 1
            while True:
                await asyncio.sleep(2)  # Check every 2 seconds
                
                # Get current state
                current_state = await page.evaluate('''() => {
                    // Get all form fields
                    const formFields = {};
                    const inputs = document.querySelectorAll('input, textarea, select');
                    inputs.forEach(input => {
                        if (input.name || input.id) {
                            formFields[input.name || input.id] = {
                                type: input.type,
                                value: input.value,
                                placeholder: input.placeholder,
                                required: input.required,
                                visible: input.offsetParent !== null
                            };
                        }
                    });
                    
                    // Get all buttons
                    const buttons = [];
                    const buttonElements = document.querySelectorAll('button, input[type="submit"], input[type="button"]');
                    buttonElements.forEach(btn => {
                        if (btn.offsetParent !== null) {
                            buttons.push({
                                text: btn.innerText || btn.value,
                                type: btn.type,
                                disabled: btn.disabled,
                                className: btn.className
                            });
                        }
                    });
                    
                    // Get any alerts or messages
                    const messages = [];
                    const messageSelectors = ['.alert', '.message', '.notification', '.error', '.success', '[role="alert"]'];
                    messageSelectors.forEach(selector => {
                        document.querySelectorAll(selector).forEach(el => {
                            if (el.offsetParent !== null && el.innerText) {
                                messages.push({
                                    text: el.innerText,
                                    className: el.className,
                                    type: selector
                                });
                            }
                        });
                    });
                    
                    // Get page title and URL
                    return {
                        url: window.location.href,
                        title: document.title,
                        formFields: formFields,
                        buttons: buttons,
                        messages: messages,
                        hasForm: document.querySelector('form') !== null,
                        bodyText: document.body.innerText.substring(0, 200)
                    };
                }''')
                
                # Log significant changes
                if current_state['messages'].length > 0:
                    log_event('MESSAGES_DETECTED', current_state['messages'])
                
                # Check for specific events
                if 'CONFIRMAR CITA' in str(current_state['buttons']):
                    log_event('SUBMIT_BUTTON_FOUND', {'buttons': current_state['buttons']})
                
                # Monitor for URL changes
                if current_state['url'] != direct_url:
                    log_event('URL_CHANGED', {
                        'from': direct_url,
                        'to': current_state['url']
                    })
                    screenshot_count += 1
                    await page.screenshot(path=f"{output_dir}/{screenshot_count:02d}_url_changed.png", full_page=True)
                
                # Check for success indicators
                body_text = current_state['bodyText'].lower()
                success_keywords = ['confirmación', 'confirmado', 'gracias', 'éxito', 'recibirá', 'email']
                for keyword in success_keywords:
                    if keyword in body_text:
                        log_event('SUCCESS_INDICATOR', {'keyword': keyword, 'context': current_state['bodyText']})
                        screenshot_count += 1
                        await page.screenshot(path=f"{output_dir}/{screenshot_count:02d}_success.png", full_page=True)
                
                # Monitor form submission
                form_data_changed = False
                for field_name, field_data in current_state['formFields'].items():
                    if field_data['value']:
                        log_event('FORM_FIELD_FILLED', {
                            'field': field_name,
                            'type': field_data['type'],
                            'has_value': bool(field_data['value'])
                        })
                        form_data_changed = True
                
                if form_data_changed:
                    screenshot_count += 1
                    await page.screenshot(path=f"{output_dir}/{screenshot_count:02d}_form_filled.png", full_page=True)
                
                # Save periodic state
                if screenshot_count % 5 == 0:
                    with open(f"{output_dir}/state_{screenshot_count:02d}.json", "w", encoding="utf-8") as f:
                        json.dump(current_state, f, indent=2, ensure_ascii=False)
                
        except KeyboardInterrupt:
            logger.info("\nMonitoring stopped by user")
        except Exception as e:
            logger.error(f"Error: {e}", exc_info=True)
            await page.screenshot(path=f"{output_dir}/error.png", full_page=True)
        
        finally:
            log_file.close()
            
            # Save final state
            try:
                final_state = await page.evaluate('''() => {
                    return {
                        url: window.location.href,
                        html: document.documentElement.outerHTML,
                        cookies: document.cookie
                    };
                }''')
                
                with open(f"{output_dir}/final_state.json", "w", encoding="utf-8") as f:
                    json.dump(final_state, f, indent=2, ensure_ascii=False)
                
                await page.screenshot(path=f"{output_dir}/final.png", full_page=True)
            except:
                pass
            
            # Close video recording
            await context.close()
            
            logger.info(f"\nMonitoring complete. Results saved to: {output_dir}")
            logger.info("Video saved in: debugging/manual_booking_video/")
            
            input("\nPress Enter to close browser...")
            await browser.close()

if __name__ == "__main__":
    print("Manual Booking Monitor")
    print("=====================")
    print("This script will:")
    print("1. Open a browser window")
    print("2. Navigate to the booking form")
    print("3. Log all events while you manually complete the booking")
    print("4. Save screenshots and a video of the process")
    print("\nPress Ctrl+C to stop monitoring")
    print()
    
    asyncio.run(monitor_manual_booking())
