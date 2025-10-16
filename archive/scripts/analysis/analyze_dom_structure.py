#!/usr/bin/env python3
"""
Analyze the DOM structure to understand how to find courts
"""
from utils.tracking import t
import pathlib
from pathlib import Path
import sys

ROOT_DIR = pathlib.Path(__file__).resolve().parents[2]
if str(ROOT_DIR) not in sys.path:
    sys.path.insert(0, str(ROOT_DIR))


import time
from playwright.sync_api import sync_playwright
import logging
import json

logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(message)s')
logger = logging.getLogger(__name__)

def analyze_dom():
    """Analyze DOM structure of the booking page"""
    t('archive.scripts.analysis.analyze_dom_structure.analyze_dom')
    
    with sync_playwright() as p:
        browser = p.chromium.launch(headless=False)
        page = browser.new_page()
        
        logger.info("Navigating to booking page...")
        page.goto("https://www.clublavilla.com/haz-tu-reserva", wait_until='networkidle')
        
        # Wait for iframe
        page.wait_for_selector('iframe')
        time.sleep(5)
        
        # Find the scheduling iframe
        scheduling_frame = None
        for frame in page.frames:
            if 'squarespacescheduling' in frame.url:
                scheduling_frame = frame
                logger.info(f"Found scheduling frame: {frame.url}")
                break
        
        if not scheduling_frame:
            logger.error("No scheduling frame found")
            return
        
        # Analyze DOM structure
        dom_analysis = scheduling_frame.evaluate('''
            () => {
                const analysis = {
                    buttons: [],
                    divs_with_tennis: [],
                    links: [],
                    clickable_elements: [],
                    dom_structure: []
                };
                
                // Get all buttons
                const buttons = document.querySelectorAll('button');
                buttons.forEach((btn, idx) => {
                    const parent = btn.parentElement;
                    const grandparent = parent ? parent.parentElement : null;
                    const greatGrandparent = grandparent ? grandparent.parentElement : null;
                    
                    analysis.buttons.push({
                        index: idx,
                        text: btn.textContent.trim(),
                        className: btn.className,
                        id: btn.id,
                        onclick: btn.onclick ? 'has onclick' : 'no onclick',
                        parentText: parent ? parent.textContent.trim().substring(0, 100) : '',
                        grandparentText: grandparent ? grandparent.textContent.trim().substring(0, 100) : '',
                        greatGrandparentText: greatGrandparent ? greatGrandparent.textContent.trim().substring(0, 100) : ''
                    });
                });
                
                // Find all elements containing "TENNIS CANCHA"
                const allElements = document.querySelectorAll('*');
                allElements.forEach(el => {
                    const text = el.textContent || '';
                    if (text.includes('TENNIS CANCHA') && !text.includes('RAQUET') && !text.includes('SQUASH')) {
                        // Check if this element has a RESERVAR button as descendant
                        const button = el.querySelector('button');
                        if (button) {
                            analysis.divs_with_tennis.push({
                                tagName: el.tagName,
                                className: el.className,
                                text: text.substring(0, 200),
                                hasButton: true,
                                buttonText: button.textContent.trim(),
                                buttonPath: getPath(button)
                            });
                        }
                    }
                });
                
                // Function to get element path
                function getPath(el) {
                    const path = [];
                    while (el && el.nodeType === Node.ELEMENT_NODE) {
                        let selector = el.nodeName.toLowerCase();
                        if (el.id) {
                            selector += '#' + el.id;
                        } else if (el.className) {
                            selector += '.' + el.className.split(' ').join('.');
                        }
                        path.unshift(selector);
                        el = el.parentNode;
                    }
                    return path.join(' > ');
                }
                
                // Get clickable elements
                const clickables = document.querySelectorAll('button, a, [onclick], [role="button"]');
                clickables.forEach(el => {
                    if (el.textContent.includes('RESERVAR') || el.textContent.includes('TENNIS')) {
                        analysis.clickable_elements.push({
                            tagName: el.tagName,
                            text: el.textContent.trim(),
                            href: el.href || '',
                            onclick: el.onclick ? 'has onclick' : 'no onclick',
                            path: getPath(el)
                        });
                    }
                });
                
                // Analyze specific structure for tennis courts
                // Try to find pattern - looking for TENNIS CANCHA X followed by RESERVAR button
                const containers = document.querySelectorAll('div, article, section, li');
                containers.forEach(container => {
                    const text = container.textContent || '';
                    if (text.includes('TENNIS CANCHA') && text.includes('RESERVAR')) {
                        const lines = text.split('\\n').map(l => l.trim()).filter(l => l);
                        
                        // Check if this looks like a court listing
                        let courtName = '';
                        let hasReservar = false;
                        for (let i = 0; i < lines.length; i++) {
                            if (lines[i].includes('TENNIS CANCHA')) {
                                courtName = lines[i];
                            }
                            if (lines[i] === 'RESERVAR') {
                                hasReservar = true;
                            }
                        }
                        
                        if (courtName && hasReservar) {
                            const button = container.querySelector('button');
                            if (button) {
                                analysis.dom_structure.push({
                                    courtName: courtName,
                                    containerTag: container.tagName,
                                    containerClass: container.className,
                                    buttonFound: true,
                                    buttonSelector: getPath(button).split(' > ').slice(-3).join(' > ')
                                });
                            }
                        }
                    }
                });
                
                return analysis;
            }
        ''')
        
        # Print analysis
        logger.info("\n=== DOM ANALYSIS ===")
        
        logger.info(f"\nButtons found: {len(dom_analysis['buttons'])}")
        for i, btn in enumerate(dom_analysis['buttons'][:10]):  # First 10 buttons
            logger.info(f"\nButton {i}:")
            logger.info(f"  Text: '{btn['text']}'")
            logger.info(f"  Parent text: '{btn['parentText'][:50]}...'")
            if 'TENNIS' in btn['grandparentText']:
                logger.info(f"  Grandparent: '{btn['grandparentText'][:50]}...'")
            if 'TENNIS' in btn['greatGrandparentText']:
                logger.info(f"  Great-grandparent: '{btn['greatGrandparentText'][:50]}...'")
        
        logger.info(f"\n\nElements with TENNIS CANCHA: {len(dom_analysis['divs_with_tennis'])}")
        for elem in dom_analysis['divs_with_tennis']:
            logger.info(f"\n{elem['tagName']} with tennis court:")
            logger.info(f"  Text: '{elem['text'][:100]}...'")
            logger.info(f"  Has button: {elem['hasButton']}")
            logger.info(f"  Button text: '{elem['buttonText']}'")
            logger.info(f"  Button path: {elem['buttonPath']}")
        
        logger.info(f"\n\nDOM Structure patterns: {len(dom_analysis['dom_structure'])}")
        for pattern in dom_analysis['dom_structure']:
            logger.info(f"\nCourt pattern found:")
            logger.info(f"  Court: {pattern['courtName']}")
            logger.info(f"  Container: <{pattern['containerTag']} class='{pattern['containerClass']}'>")
            logger.info(f"  Button selector: {pattern['buttonSelector']}")
        
        # Save full analysis to file
        with open('dom_analysis.json', 'w') as f:
            json.dump(dom_analysis, f, indent=2)
        logger.info("\nFull analysis saved to dom_analysis.json")
        
        # Try a simpler approach - click by index
        logger.info("\n\n=== TRYING SIMPLE CLICK ===")
        
        # Find RESERVAR buttons for tennis courts
        tennis_buttons = scheduling_frame.evaluate('''
            () => {
                const results = [];
                const buttons = Array.from(document.querySelectorAll('button'));
                
                // Get text content around each button to identify tennis courts
                buttons.forEach((btn, idx) => {
                    if (btn.textContent.trim() === 'RESERVAR') {
                        // Get surrounding text
                        let container = btn.parentElement;
                        let searchDepth = 5;
                        let surroundingText = '';
                        
                        while (container && searchDepth > 0) {
                            surroundingText = container.textContent || '';
                            if (surroundingText.includes('TENNIS CANCHA')) {
                                break;
                            }
                            container = container.parentElement;
                            searchDepth--;
                        }
                        
                        if (surroundingText.includes('TENNIS CANCHA')) {
                            // Extract court number
                            const match = surroundingText.match(/TENNIS CANCHA (\\d)/);
                            if (match) {
                                results.push({
                                    buttonIndex: idx,
                                    courtNumber: parseInt(match[1]),
                                    courtName: `TENNIS CANCHA ${match[1]}`
                                });
                            }
                        }
                    }
                });
                
                return results.sort((a, b) => a.courtNumber - b.courtNumber);
            }
        ''')
        
        logger.info(f"\nFound {len(tennis_buttons)} tennis court buttons:")
        for btn in tennis_buttons:
            logger.info(f"  {btn}")
        
        # Click on court 1 if found
        if tennis_buttons and len(tennis_buttons) > 0:
            court1 = tennis_buttons[0]
            logger.info(f"\nClicking on {court1['courtName']} (button index {court1['buttonIndex']})...")
            
            # Click the button
            clicked = scheduling_frame.evaluate(f'''
                () => {{
                    const buttons = Array.from(document.querySelectorAll('button'));
                    const button = buttons[{court1['buttonIndex']}];
                    if (button) {{
                        button.click();
                        return true;
                    }}
                    return false;
                }}
            ''')
            
            if clicked:
                logger.info("Click successful! Waiting for navigation...")
                time.sleep(3)
                
                # Check new URL
                new_url = scheduling_frame.url
                logger.info(f"New frame URL: {new_url}")
                
                page.screenshot(path="after_tennis_court_click.png")
                logger.info("Screenshot saved")
        
        input("Press Enter to close...")
        browser.close()

if __name__ == "__main__":
    analyze_dom()
