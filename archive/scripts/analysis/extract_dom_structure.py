#!/usr/bin/env python3
"""
DOM Structure Extractor for Acuity Scheduling
==============================================

This script creates a browser and extracts the raw DOM structure
around day headers and time buttons to understand the day-specific extraction issue.
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
import json
from datetime import datetime
from playwright.async_api import async_playwright
from lvbot.utils.constants import BOOKING_URL, SCHEDULING_IFRAME_URL_PATTERN

# Set up logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger('DOMExtractor')

async def extract_dom_structure():
    """Extract DOM structure from Acuity scheduling page"""
    t('archive.scripts.analysis.extract_dom_structure.extract_dom_structure')
    
    logger.info("Starting DOM structure extraction")
    
    # Create playwright instance
    playwright = await async_playwright().start()
    
    try:
        # Launch browser
        logger.info("Launching browser...")
        browser = await playwright.chromium.launch(
            headless=False,  # Show browser for visual inspection
            args=[
                '--disable-gpu',
                '--no-sandbox',
                '--disable-setuid-sandbox',
                '--disable-web-security'
            ]
        )
        
        # Create context and page
        context = await browser.new_context(
            viewport={'width': 1280, 'height': 720},
            user_agent='Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36'
        )
        page = await context.new_page()
        
        # Navigate to booking page
        logger.info(f"Navigating to {BOOKING_URL}")
        await page.goto(BOOKING_URL, wait_until='domcontentloaded', timeout=30000)
        
        # Wait for iframe to load
        logger.info("Waiting for scheduling iframe...")
        booking_frame = None
        start_time = asyncio.get_event_loop().time()
        
        while asyncio.get_event_loop().time() - start_time < 30:
            frames = page.frames
            for frame in frames:
                if SCHEDULING_IFRAME_URL_PATTERN in frame.url:
                    booking_frame = frame
                    break
            if booking_frame:
                break
            await asyncio.sleep(0.5)
        
        if not booking_frame:
            logger.error("Could not find booking iframe")
            # List all frames for debugging
            logger.info("Available frames:")
            for i, frame in enumerate(page.frames):
                logger.info(f"  Frame {i}: {frame.url}")
            return
        
        logger.info(f"Found booking frame: {booking_frame.url}")
        
        # Wait a bit more for the iframe to fully load
        await asyncio.sleep(3)
        
        # First, let's explore what's available on the page
        logger.info("Exploring available content on the page...")
        page_content = await booking_frame.evaluate("""
        () => {
            const buttons = Array.from(document.querySelectorAll('button'));
            const allText = document.body ? document.body.innerText.substring(0, 1000) : document.documentElement.textContent.substring(0, 1000);
            
            return {
                buttonCount: buttons.length,
                buttonTexts: buttons.slice(0, 10).map(btn => btn.innerText ? btn.innerText.trim() : ''),
                pageText: allText || '',
                hasReservarButtons: buttons.some(btn => (btn.innerText || '').includes('Reservar') || (btn.innerText || '').includes('RESERVAR')),
                hasCourtText: (allText || '').includes('CANCHA') || (allText || '').includes('COURT'),
                allButtonsInfo: buttons.map(btn => ({
                    text: btn.innerText ? btn.innerText.trim() : '',
                    parent: btn.parentElement && btn.parentElement.textContent ? btn.parentElement.textContent.substring(0, 100) : ''
                }))
            };
        }
        """)
        
        logger.info(f"Page exploration results:")
        logger.info(f"  Button count: {page_content['buttonCount']}")
        logger.info(f"  Has Reservar buttons: {page_content['hasReservarButtons']}")
        logger.info(f"  Has court text: {page_content['hasCourtText']}")
        logger.info(f"  Page text sample: {page_content['pageText'][:200]}...")
        
        # Try to click on any court
        logger.info("Attempting to click on any available court...")
        court_clicked = await booking_frame.evaluate("""
        () => {
            const buttons = Array.from(document.querySelectorAll('button'));
            
            // First try exact match for tennis courts
            for (const btn of buttons) {
                const btnText = (btn.innerText || '').trim();
                if (btnText === 'Reservar' || btnText === 'RESERVAR') {
                    let parent = btn.parentElement;
                    let depth = 5;
                    
                    while (parent && depth > 0) {
                        const parentText = parent.textContent || '';
                        if (parentText.includes('TENNIS') || parentText.includes('CANCHA')) {
                            console.log('Found tennis court button:', parentText.substring(0, 100));
                            btn.click();
                            return true;
                        }
                        parent = parent.parentElement;
                        depth--;
                    }
                }
            }
            
            // If no tennis court found, try any Reservar button
            for (const btn of buttons) {
                const btnText = (btn.innerText || '').trim();
                if (btnText === 'Reservar' || btnText === 'RESERVAR') {
                    console.log('Clicking general Reservar button');
                    btn.click();
                    return true;
                }
            }
            
            return false;
        }
        """)
        
        if not court_clicked:
            logger.warning("Could not find any RESERVAR button, proceeding with current page")
        else:
            logger.info("Successfully clicked a court button, waiting for calendar...")
            await asyncio.sleep(5)  # Wait for calendar to load
        
        # Take a screenshot first
        logger.info("Taking screenshot for visual reference...")
        await page.screenshot(path='acuity_page_screenshot.png', full_page=True)
        logger.info("Screenshot saved as acuity_page_screenshot.png")
        
        # Extract the DOM structure around day headers and time buttons
        logger.info("Extracting DOM structure...")
        
        dom_extraction_js = """
        () => {
            // Function to get element hierarchy info
            function getElementInfo(el) {
                return {
                    tagName: el.tagName.toLowerCase(),
                    className: el.className || '',
                    id: el.id || '',
                    textContent: el.textContent ? el.textContent.trim().substring(0, 100) : '',
                    innerHTML: el.innerHTML ? el.innerHTML.substring(0, 200) : '',
                    attributes: Array.from(el.attributes).reduce((acc, attr) => {
                        acc[attr.name] = attr.value;
                        return acc;
                    }, {})
                };
            }
            
            // Function to get element tree with children
            function getElementTree(el, maxDepth = 3, currentDepth = 0) {
                if (currentDepth >= maxDepth) return null;
                
                const info = getElementInfo(el);
                info.children = [];
                
                for (let child of el.children) {
                    const childInfo = getElementTree(child, maxDepth, currentDepth + 1);
                    if (childInfo) {
                        info.children.push(childInfo);
                    }
                }
                
                return info;
            }
            
            const results = {
                dayHeaders: [],
                timeButtons: [],
                containerStructure: null,
                fullDOMExtract: null
            };
            
            // Look for day labels (HOY, MAÑANA, ESTA SEMANA, etc.)
            const dayLabelTexts = ['HOY', 'MAÑANA', 'ESTA SEMANA', 'LA PRÓXIMA SEMANA', 'PRÓXIMA SEMANA'];
            const allElements = document.querySelectorAll('*');
            
            console.log('Total elements found:', allElements.length);
            
            allElements.forEach((el, index) => {
                const text = el.textContent ? el.textContent.trim() : '';
                
                // Check for day labels
                dayLabelTexts.forEach(dayLabel => {
                    if (text === dayLabel) {
                        results.dayHeaders.push({
                            index: index,
                            dayLabel: dayLabel,
                            element: getElementInfo(el),
                            parent: el.parentElement ? getElementInfo(el.parentElement) : null,
                            grandparent: el.parentElement && el.parentElement.parentElement ? 
                                getElementInfo(el.parentElement.parentElement) : null,
                            siblings: Array.from(el.parentElement ? el.parentElement.children : [])
                                .map(sibling => getElementInfo(sibling)),
                            elementTree: getElementTree(el.parentElement || el, 4)
                        });
                    }
                });
                
                // Check for time buttons (HH:MM pattern)
                if (el.tagName && el.tagName.toLowerCase() === 'button') {
                    const timeMatch = text.match(/\\d{1,2}:\\d{2}/);
                    if (timeMatch) {
                        results.timeButtons.push({
                            index: index,
                            time: timeMatch[0],
                            fullText: text,
                            element: getElementInfo(el),
                            parent: el.parentElement ? getElementInfo(el.parentElement) : null,
                            grandparent: el.parentElement && el.parentElement.parentElement ? 
                                getElementInfo(el.parentElement.parentElement) : null,
                            elementTree: getElementTree(el.parentElement || el, 4)
                        });
                    }
                }
            });
            
            // Find the main container that holds both day headers and time buttons
            if (results.dayHeaders.length > 0 && results.timeButtons.length > 0) {
                // Find common ancestor
                const dayElement = document.querySelectorAll('*')[results.dayHeaders[0].index];
                const timeElement = document.querySelectorAll('*')[results.timeButtons[0].index];
                
                // Walk up to find common container
                let container = dayElement;
                while (container && !container.contains(timeElement)) {
                    container = container.parentElement;
                }
                
                if (container) {
                    results.containerStructure = getElementTree(container, 5);
                }
            }
            
            // Get a full DOM extract of the area around scheduling
            const schedulingContainer = document.querySelector('[class*="scheduling"], [class*="calendar"], [class*="appointment"]') ||
                                      document.querySelector('.acuity-embed-container') ||
                                      document.body;
            
            if (schedulingContainer) {
                results.fullDOMExtract = getElementTree(schedulingContainer, 6);
            }
            
            console.log('Day headers found:', results.dayHeaders.length);
            console.log('Time buttons found:', results.timeButtons.length);
            
            return results;
        }
        """
        
        dom_structure = await booking_frame.evaluate(dom_extraction_js)
        
        # Save the DOM structure to a file
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        dom_file = f'dom_structure_{timestamp}.json'
        
        with open(dom_file, 'w') as f:
            json.dump(dom_structure, f, indent=2)
        
        logger.info(f"DOM structure saved to {dom_file}")
        
        # Print summary
        print("\n" + "="*60)
        print("DOM STRUCTURE ANALYSIS SUMMARY")
        print("="*60)
        print(f"Day headers found: {len(dom_structure['dayHeaders'])}")
        print(f"Time buttons found: {len(dom_structure['timeButtons'])}")
        
        if dom_structure['dayHeaders']:
            print("\nDAY HEADERS:")
            for i, header in enumerate(dom_structure['dayHeaders']):
                print(f"  {i+1}. {header['dayLabel']}")
                print(f"     Element: <{header['element']['tagName']} class='{header['element']['className']}'>")
                print(f"     Parent: <{header['parent']['tagName']} class='{header['parent']['className']}'>" if header['parent'] else "     Parent: None")
        
        if dom_structure['timeButtons']:
            print(f"\nTIME BUTTONS (showing first 10 of {len(dom_structure['timeButtons'])}):")
            for i, button in enumerate(dom_structure['timeButtons'][:10]):
                print(f"  {i+1}. {button['time']} - '{button['fullText']}'")
                print(f"     Element: <{button['element']['tagName']} class='{button['element']['className']}'>")
                print(f"     Parent: <{button['parent']['tagName']} class='{button['parent']['className']}'>" if button['parent'] else "     Parent: None")
        
        print(f"\nContainer structure: {'Found' if dom_structure['containerStructure'] else 'Not found'}")
        print(f"Full DOM extract: {'Found' if dom_structure['fullDOMExtract'] else 'Not found'}")
        
        print(f"\nDetailed analysis saved to: {dom_file}")
        print("Screenshot saved to: acuity_page_screenshot.png")
        print("\n" + "="*60)
        
        # Keep browser open for 30 seconds for manual inspection
        logger.info("Browser will stay open for 30 seconds for manual inspection...")
        await asyncio.sleep(30)
        
    except Exception as e:
        logger.error(f"Error during extraction: {e}", exc_info=True)
    
    finally:
        # Cleanup
        logger.info("Cleaning up...")
        try:
            await context.close()
            await browser.close()
            await playwright.stop()
        except Exception as e:
            logger.error(f"Error during cleanup: {e}")

if __name__ == "__main__":
    asyncio.run(extract_dom_structure())
