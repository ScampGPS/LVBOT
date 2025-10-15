#!/usr/bin/env python3
"""
Script to record manual booking flow - launches browser and records what happens
"""
import pathlib
from pathlib import Path
import sys

ROOT_DIR = pathlib.Path(__file__).resolve().parents[2]
if str(ROOT_DIR) not in sys.path:
    sys.path.insert(0, str(ROOT_DIR))


import asyncio
import logging
from datetime import datetime
from playwright.async_api import async_playwright
import json
import os

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

async def record_manual_booking():
    """Launch browser and record manual interactions"""
    async with async_playwright() as p:
        browser = await p.chromium.launch(
            headless=False,  # Show browser
            slow_mo=500,     # Slow down actions for visibility
            args=['--start-maximized']
        )
        context = await browser.new_context(
            viewport={'width': 1280, 'height': 800},
            record_video_dir="debugging/manual_recording"
        )
        page = await context.new_page()
        
        screenshots_dir = "debugging/manual_booking_flow"
        os.makedirs(screenshots_dir, exist_ok=True)
        
        # Enable console logging
        page.on('console', lambda msg: logger.info(f"Browser console: {msg.text}"))
        
        # Track navigation
        page.on('framenavigated', lambda frame: logger.info(f"Navigated to: {frame.url}"))
        
        try:
            # Go to Court 2
            court_url = "https://clublavilla.as.me/?appointmentType=16021953"
            logger.info(f"Navigating to {court_url}")
            await page.goto(court_url, wait_until='networkidle', timeout=30000)
            
            logger.info("\n" + "="*60)
            logger.info("BROWSER IS READY - Please perform the booking manually")
            logger.info("I will record everything that happens")
            logger.info("="*60 + "\n")
            
            step_count = 0
            
            # Monitor for changes
            while True:
                step_count += 1
                
                # Take periodic screenshots
                await page.screenshot(path=f"{screenshots_dir}/step_{step_count:02d}.png", full_page=True)
                
                # Log current state
                current_url = page.url
                page_title = await page.title()
                
                logger.info(f"\nStep {step_count}:")
                logger.info(f"  URL: {current_url}")
                logger.info(f"  Title: {page_title}")
                
                # Check for form fields
                form_inputs = await page.evaluate('''() => {
                    const inputs = Array.from(document.querySelectorAll('input:not([type="hidden"]), textarea, select'));
                    return inputs.map(input => ({
                        tagName: input.tagName,
                        type: input.type || 'text',
                        name: input.name,
                        id: input.id,
                        placeholder: input.placeholder,
                        value: input.value,
                        className: input.className,
                        isVisible: input.offsetParent !== null
                    }));
                }''')
                
                if form_inputs:
                    logger.info(f"  Found {len(form_inputs)} form fields:")
                    for field in form_inputs:
                        if field['isVisible']:
                            logger.info(f"    - {field['tagName']} ({field['type']}): name='{field['name']}', id='{field['id']}', placeholder='{field['placeholder']}'")
                
                # Check for buttons
                buttons = await page.evaluate('''() => {
                    const buttons = Array.from(document.querySelectorAll('button:not([disabled]), input[type="submit"], [role="button"]'));
                    return buttons.map(btn => ({
                        tagName: btn.tagName,
                        text: btn.textContent?.trim() || btn.value || '',
                        type: btn.type,
                        className: btn.className,
                        isVisible: btn.offsetParent !== null
                    })).filter(btn => btn.isVisible && btn.text);
                }''')
                
                if buttons:
                    logger.info(f"  Found {len(buttons)} visible buttons:")
                    for btn in buttons[:10]:  # Limit to first 10
                        logger.info(f"    - {btn['text']} (class: {btn['className']})")
                
                # Save page state
                state_file = f"{screenshots_dir}/state_{step_count:02d}.json"
                state_data = {
                    'url': current_url,
                    'title': page_title,
                    'form_inputs': form_inputs,
                    'buttons': buttons,
                    'timestamp': datetime.now().isoformat()
                }
                
                with open(state_file, 'w', encoding='utf-8') as f:
                    json.dump(state_data, f, indent=2, ensure_ascii=False)
                
                # Wait a bit before next check
                await asyncio.sleep(3)
                
                # Check if user wants to stop (by navigating away or closing)
                if "schedule" not in current_url and "acuity" not in current_url:
                    logger.info("\nNavigated away from booking site, stopping recording...")
                    break
                
        except KeyboardInterrupt:
            logger.info("\nRecording stopped by user")
        except Exception as e:
            logger.error(f"Error during recording: {e}")
        
        finally:
            logger.info("\nSaving final state...")
            await page.screenshot(path=f"{screenshots_dir}/final_state.png", full_page=True)
            
            # Save video if available
            await context.close()
            
            logger.info(f"\nRecording complete! Check {screenshots_dir} for screenshots and state files")
            
            input("\nPress Enter to close the browser...")
            await browser.close()

if __name__ == "__main__":
    print("Starting manual booking recorder...")
    print("Please perform the booking steps manually in the browser")
    print("Press Ctrl+C to stop recording")
    asyncio.run(record_manual_booking())
