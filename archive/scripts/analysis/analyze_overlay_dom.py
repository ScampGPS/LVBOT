"""
Analyze the DOM structure of the rules overlay to find a way to bypass it
"""
from utils.tracking import t
import pathlib
from pathlib import Path
import sys

ROOT_DIR = pathlib.Path(__file__).resolve().parents[2]
if str(ROOT_DIR) not in sys.path:
    sys.path.insert(0, str(ROOT_DIR))

import asyncio
import time
import logging
from playwright.async_api import async_playwright

logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

async def analyze_overlay_dom():
    """Analyze the DOM structure in detail"""
    t('archive.scripts.analysis.analyze_overlay_dom.analyze_overlay_dom')
    
    async with async_playwright() as p:
        # Launch browser
        browser = await p.chromium.launch(
            headless=False,  # Show browser for visual debugging
            args=['--disable-blink-features=AutomationControlled']
        )
        
        page = await browser.new_page()
        
        # Navigate to the calendar URL
        url = "https://clublavilla.as.me/schedule/7d558012/appointment/15970897/calendar/4282490?appointmentTypeIds[]=15970897"
        logger.info(f"Navigating to: {url}")
        
        await page.goto(url, wait_until='networkidle')
        await page.wait_for_timeout(2000)
        
        # Analyze the DOM structure
        logger.info("\n=== DOM Structure Analysis ===")
        
        # Get the full page HTML structure
        dom_info = await page.evaluate('''() => {
            const info = {
                bodyChildren: [],
                overlayElements: [],
                calendarElements: [],
                timeButtons: []
            };
            
            // Get direct children of body
            Array.from(document.body.children).forEach(child => {
                info.bodyChildren.push({
                    tag: child.tagName,
                    id: child.id,
                    class: child.className,
                    zIndex: window.getComputedStyle(child).zIndex,
                    position: window.getComputedStyle(child).position,
                    display: window.getComputedStyle(child).display,
                    visible: child.offsetParent !== null
                });
            });
            
            // Find elements with high z-index or fixed position
            document.querySelectorAll('*').forEach(el => {
                const style = window.getComputedStyle(el);
                const zIndex = parseInt(style.zIndex) || 0;
                
                if (zIndex > 100 || style.position === 'fixed' || style.position === 'absolute') {
                    if (el.offsetWidth > 200 && el.offsetHeight > 200) {
                        info.overlayElements.push({
                            tag: el.tagName,
                            id: el.id,
                            class: el.className,
                            zIndex: zIndex,
                            position: style.position,
                            width: el.offsetWidth,
                            height: el.offsetHeight,
                            textContent: el.textContent.substring(0, 50)
                        });
                    }
                }
            });
            
            // Find calendar/time elements
            document.querySelectorAll('[class*="calendar"], [class*="time"], button').forEach(el => {
                if (el.textContent && el.textContent.match(/\\d{1,2}:\\d{2}|AM|PM/)) {
                    info.timeButtons.push({
                        tag: el.tagName,
                        class: el.className,
                        text: el.textContent.trim(),
                        clickable: !el.disabled && el.offsetParent !== null,
                        zIndex: window.getComputedStyle(el).zIndex
                    });
                }
            });
            
            return info;
        }''')
        
        logger.info(f"\n=== Body Children ({len(dom_info['bodyChildren'])}) ===")
        for child in dom_info['bodyChildren']:
            logger.info(f"  {child['tag']}#{child['id']}.{child['class'][:50]} - z:{child['zIndex']}, pos:{child['position']}, visible:{child['visible']}")
        
        logger.info(f"\n=== Overlay Elements ({len(dom_info['overlayElements'])}) ===")
        for el in dom_info['overlayElements']:
            logger.info(f"  {el['tag']}#{el['id']}.{el['class'][:50]} - z:{el['zIndex']}, {el['width']}x{el['height']}")
            logger.info(f"    Text: {el['textContent'][:50]}...")
        
        logger.info(f"\n=== Time Buttons ({len(dom_info['timeButtons'])}) ===")
        for btn in dom_info['timeButtons'][:10]:
            logger.info(f"  {btn['tag']}.{btn['class'][:30]} - '{btn['text']}' clickable:{btn['clickable']}")
        
        # Try a more targeted approach
        logger.info("\n=== Attempting targeted overlay removal ===")
        
        # Find the specific overlay element
        overlay_removed = await page.evaluate('''() => {
            let removed = false;
            
            // Look for the element containing "Reglamento"
            const elements = Array.from(document.querySelectorAll('*'));
            for (const el of elements) {
                if (el.textContent && el.textContent.includes('Reglamento del sistema de citas')) {
                    // Find the root container of this overlay
                    let parent = el;
                    while (parent && parent.parentElement && parent.parentElement !== document.body) {
                        parent = parent.parentElement;
                    }
                    
                    console.log('Found overlay root:', parent);
                    
                    // Remove it
                    if (parent && parent.parentElement) {
                        parent.parentElement.removeChild(parent);
                        removed = true;
                        console.log('Overlay removed!');
                    }
                    break;
                }
            }
            
            return removed;
        }''')
        
        if overlay_removed:
            logger.info("Successfully removed overlay!")
            await page.screenshot(path="overlay_removed.png")
            
            # Now try clicking a time button
            time_button = await page.query_selector('button:has-text("11:00")')
            if time_button:
                logger.info("Clicking time button 11:00")
                await time_button.click()
                await page.wait_for_timeout(2000)
                await page.screenshot(path="after_time_click.png")
                
                # Check if we reached the form
                form_fields = await page.query_selector_all('input[type="text"], input[type="email"], input[type="tel"]')
                logger.info(f"Form fields found: {len(form_fields)}")
                
                if form_fields:
                    logger.info("SUCCESS! We can now interact with the booking form!")
                    
                    for field in form_fields:
                        field_name = await field.get_attribute('name')
                        field_id = await field.get_attribute('id')
                        logger.info(f"  Field: name='{field_name}', id='{field_id}'")
        
        # Alternative: Check if we can interact with elements behind the overlay
        logger.info("\n=== Testing force interaction ===")
        
        # Get all time buttons and their positions
        button_positions = await page.evaluate('''() => {
            const buttons = [];
            document.querySelectorAll('button').forEach(btn => {
                if (btn.textContent && btn.textContent.match(/\\d{1,2}:\\d{2}/)) {
                    const rect = btn.getBoundingClientRect();
                    buttons.push({
                        text: btn.textContent.trim(),
                        x: rect.left + rect.width / 2,
                        y: rect.top + rect.height / 2,
                        clickable: !btn.disabled
                    });
                }
            });
            return buttons;
        }''')
        
        logger.info(f"\nFound {len(button_positions)} time buttons with positions")
        if button_positions:
            first_button = button_positions[0]
            logger.info(f"Attempting to click at position ({first_button['x']}, {first_button['y']}) for button: {first_button['text']}")
            
            # Force click at the position
            await page.mouse.click(first_button['x'], first_button['y'])
            await page.wait_for_timeout(2000)
            await page.screenshot(path="force_position_click.png")
        
        logger.info("\nBrowser will stay open for 30 seconds for manual inspection...")
        await page.wait_for_timeout(30000)
        
        await browser.close()

if __name__ == "__main__":
    asyncio.run(analyze_overlay_dom())
