#!/usr/bin/env python3
"""
Script to analyze the Acuity booking form that appears after clicking a time slot.
This follows LVBOT principles: modular, reusable, and focused on one task.
"""
from utils.tracking import t
import pathlib
import sys

ROOT_DIR = pathlib.Path(__file__).resolve().parents[2]
if str(ROOT_DIR) not in sys.path:
    sys.path.insert(0, str(ROOT_DIR))


import asyncio
import logging
from datetime import datetime
from pathlib import Path
from playwright.async_api import async_playwright, Frame, Page

# Ensure repository root is on the import path
from lvbot.logging_config import setup_logging
from lvbot.utils.acuity_page_validator import AcuityPageValidator
from lvbot.utils.time_order_extraction import AcuityTimeParser

class AcuityFormAnalyzer:
    """Analyze the booking form that appears after clicking a time slot"""
    
    def __init__(self):
        """Initialize the analyzer with logging"""
        t('archive.scripts.analysis.analyze_booking_form.AcuityFormAnalyzer.__init__')
        setup_logging()
        self.logger = logging.getLogger(self.__class__.__name__)
        self.screenshots_dir = Path("debugging/booking_form_analysis")
        self.screenshots_dir.mkdir(parents=True, exist_ok=True)
        
    async def analyze_booking_flow(self, court_number: int = 3) -> None:
        """
        Analyze what happens when clicking a time slot
        
        Args:
            court_number: Which court to test (default 3 as it usually has availability)
        """
        t('archive.scripts.analysis.analyze_booking_form.AcuityFormAnalyzer.analyze_booking_flow')
        self.logger.info(f"🔍 Starting booking form analysis for Court {court_number}")
        
        async with async_playwright() as playwright:
            # Launch browser in visible mode with slow motion
            browser = await playwright.chromium.launch(
                headless=False, 
                slow_mo=500  # Slow down actions for visibility
            )
            
            page = await browser.new_page()
            
            try:
                # Navigate to court URL (use the correct URL format from browser pool)
                court_urls = {
                    1: "https://clublavilla.as.me/?appointmentType=15970897",
                    2: "https://clublavilla.as.me/?appointmentType=16021953", 
                    3: "https://clublavilla.as.me/?appointmentType=16120442"
                }
                court_url = court_urls.get(court_number, court_urls[3])
                self.logger.info(f"📍 Navigating to: {court_url}")
                await page.goto(court_url, wait_until='domcontentloaded')
                
                # Wait for page to stabilize
                await page.wait_for_timeout(3000)
                
                # Get the scheduling frame
                frame = await AcuityPageValidator._get_extraction_frame(page)
                if not frame:
                    self.logger.error("❌ Could not find scheduling frame")
                    return
                
                # Extract available times
                parser = AcuityTimeParser()
                times_by_day = await parser.extract_times_by_day(frame)
                self.logger.info(f"📅 Found times: {times_by_day}")
                
                # Find first available time button
                time_button = await self._find_first_time_button(frame)
                if not time_button:
                    self.logger.error("❌ No time buttons found")
                    return
                
                # Take screenshot before clicking
                await page.screenshot(
                    path=self.screenshots_dir / f"1_before_click_{datetime.now().strftime('%Y%m%d_%H%M%S')}.png",
                    full_page=True
                )
                
                # Click the time button
                button_text = await time_button.text_content()
                self.logger.info(f"🖱️ Clicking time button: {button_text}")
                await time_button.click()
                
                # Wait for form to appear
                await page.wait_for_timeout(2000)
                
                # Take screenshot after clicking
                await page.screenshot(
                    path=self.screenshots_dir / f"2_after_click_{datetime.now().strftime('%Y%m%d_%H%M%S')}.png",
                    full_page=True
                )
                
                # Analyze what appeared
                await self._analyze_form_structure(page, frame)
                
                # Keep browser open for manual inspection
                self.logger.info("🔍 Keeping browser open for 30 seconds for manual inspection...")
                await page.wait_for_timeout(30000)
                
            except Exception as e:
                self.logger.error(f"❌ Error during analysis: {e}")
                # Take error screenshot
                await page.screenshot(
                    path=self.screenshots_dir / f"error_{datetime.now().strftime('%Y%m%d_%H%M%S')}.png",
                    full_page=True
                )
                
            finally:
                await browser.close()
                self.logger.info("✅ Analysis complete. Check screenshots in debugging/booking_form_analysis/")
    
    async def _find_first_time_button(self, frame: Frame):
        """Find the first available time button"""
        t('archive.scripts.analysis.analyze_booking_form.AcuityFormAnalyzer._find_first_time_button')
        selectors = [
            'button.css-tq4fs9',  # Acuity time button class
            'button:has-text(":")',  # Any button with time format
            '[role="button"]:has-text(":")',  # Role-based selector
        ]
        
        for selector in selectors:
            buttons = await frame.query_selector_all(selector)
            if buttons:
                self.logger.info(f"✅ Found {len(buttons)} time buttons using selector: {selector}")
                return buttons[0]
        
        return None
    
    async def _analyze_form_structure(self, page: Page, frame: Frame) -> None:
        """Analyze the structure of the booking form"""
        t('archive.scripts.analysis.analyze_booking_form.AcuityFormAnalyzer._analyze_form_structure')
        self.logger.info("📋 Analyzing form structure...")
        
        # Check for modal/popup
        modal_selectors = [
            '[role="dialog"]',
            '.modal',
            '.popup',
            '[class*="overlay"]',
            '[class*="modal"]'
        ]
        
        for selector in modal_selectors:
            modal = await page.query_selector(selector)
            if modal:
                self.logger.info(f"🔲 Found modal/popup with selector: {selector}")
                break
        
        # Check for form elements
        form_selectors = [
            'form',
            'input[type="text"]',
            'input[type="email"]',
            'input[type="tel"]',
            'input[name*="name"]',
            'input[name*="email"]',
            'input[name*="phone"]',
            'button[type="submit"]'
        ]
        
        self.logger.info("📝 Form elements found:")
        for selector in form_selectors:
            elements = await page.query_selector_all(selector)
            if elements:
                self.logger.info(f"   ✓ {selector}: {len(elements)} element(s)")
                
                # Get more details for input fields
                if 'input' in selector:
                    for elem in elements[:3]:  # First 3 elements
                        name = await elem.get_attribute('name')
                        placeholder = await elem.get_attribute('placeholder')
                        label = await self._find_label_for_input(page, elem)
                        self.logger.info(f"      - name='{name}', placeholder='{placeholder}', label='{label}'")
        
        # Check if we're still in the same frame or navigated
        current_url = page.url
        self.logger.info(f"📍 Current URL: {current_url}")
        
        # Get all frames
        frames = page.frames
        self.logger.info(f"🖼️ Total frames on page: {len(frames)}")
        for i, f in enumerate(frames):
            self.logger.info(f"   Frame {i}: {f.url}")
    
    async def _find_label_for_input(self, page: Page, input_elem) -> str:
        """Find label text for an input element"""
        t('archive.scripts.analysis.analyze_booking_form.AcuityFormAnalyzer._find_label_for_input')
        try:
            # Get input id
            input_id = await input_elem.get_attribute('id')
            if input_id:
                # Look for label with for attribute
                label = await page.query_selector(f'label[for="{input_id}"]')
                if label:
                    return await label.text_content()
            
            # Check for parent label
            parent = await input_elem.evaluate_handle('el => el.closest("label")')
            if parent:
                return await parent.text_content()
                
            return ""
        except:
            return ""


async def main():
    """Run the booking form analysis"""
    t('archive.scripts.analysis.analyze_booking_form.main')
    analyzer = AcuityFormAnalyzer()
    await analyzer.analyze_booking_flow(court_number=3)


if __name__ == "__main__":
    asyncio.run(main())
