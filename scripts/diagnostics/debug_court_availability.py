#!/usr/bin/env python3
"""
LVBOT Court Availability Debugging Tool
======================================

Purpose: Navigate to each court page, take screenshots, and compare
what's displayed vs what the bot detects.

This tool:
1. Navigates to each court page
2. Takes screenshots of what's displayed
3. Shows what time slots are actually available vs what the bot detects
4. Saves screenshots with timestamps and court numbers
5. Compares detected slots with visible slots
"""
import pathlib
import sys

ROOT_DIR = pathlib.Path(__file__).resolve().parents[2]
if str(ROOT_DIR) not in sys.path:
    sys.path.insert(0, str(ROOT_DIR))


import asyncio
import logging
import json
from datetime import datetime
from pathlib import Path
from typing import Dict, List, Optional, Tuple
from playwright.async_api import async_playwright, Page

# Import existing modules for consistency
from lvbot.utils.constants import COURT_CONFIG, TIME_BUTTON_SELECTOR, TIME_SLOT_SELECTORS
from lvbot.utils.time_slot_extractor import TimeSlotExtractor
from lvbot.utils.day_mapper import DayMapper
from lvbot.utils.availability_checker_v3 import AvailabilityCheckerV3
from lvbot.utils.async_browser_pool import AsyncBrowserPool

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)


class CourtAvailabilityDebugger:
    """Debug tool for comparing visible vs detected court availability"""
    
    def __init__(self):
        self.time_extractor = TimeSlotExtractor()
        self.day_mapper = DayMapper()
        self.debug_dir = None
        self.playwright = None
        self.browser = None
        
    async def initialize(self):
        """Initialize playwright and browser"""
        self.playwright = await async_playwright().start()
        self.browser = await self.playwright.chromium.launch(
            headless=False,
            args=[
                '--window-size=1920,1080',
                '--start-maximized'
            ]
        )
        
        # Create debug directory with timestamp
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        self.debug_dir = Path(f"debug_court_availability_{timestamp}")
        self.debug_dir.mkdir(exist_ok=True)
        logger.info(f"Created debug directory: {self.debug_dir}")
        
    async def cleanup(self):
        """Clean up browser and playwright"""
        if self.browser:
            await self.browser.close()
        if self.playwright:
            await self.playwright.stop()
            
    async def analyze_court_page(self, court_num: int) -> Dict:
        """
        Analyze a single court page - navigate, screenshot, and extract data
        
        Returns:
            Dict with analysis results
        """
        court_config = COURT_CONFIG.get(court_num)
        if not court_config:
            logger.error(f"Invalid court number: {court_num}")
            return {"error": f"Invalid court number: {court_num}"}
            
        court_url = court_config["direct_url"]
        logger.info(f"\n{'='*60}")
        logger.info(f"Analyzing Court {court_num}")
        logger.info(f"URL: {court_url}")
        logger.info(f"{'='*60}")
        
        # Create new page for this court
        page = await self.browser.new_page()
        
        try:
            # Navigate to court page
            logger.info(f"Navigating to Court {court_num}...")
            await page.goto(court_url, wait_until='domcontentloaded', timeout=30000)
            
            # Wait for page to stabilize
            await asyncio.sleep(3)
            
            # Take initial screenshot
            screenshot_path = self.debug_dir / f"court_{court_num}_initial.png"
            await page.screenshot(path=str(screenshot_path), full_page=True)
            logger.info(f"Saved initial screenshot: {screenshot_path}")
            
            # Check for no availability message
            no_availability = await self._check_no_availability(page)
            if no_availability:
                logger.warning(f"Court {court_num}: No availability message detected")
                return {
                    "court": court_num,
                    "url": court_url,
                    "no_availability": True,
                    "screenshot": str(screenshot_path),
                    "detected_slots": [],
                    "visible_elements": []
                }
            
            # Extract time slots using bot's method
            logger.info("Extracting time slots using bot method...")
            detected_buttons = await self.time_extractor.extract_all_time_buttons(page)
            detected_times = []
            for button in detected_buttons:
                time_text = await self.time_extractor.extract_time_text(button)
                if time_text:
                    detected_times.append(time_text)
                    
            logger.info(f"Bot detected {len(detected_times)} time slots: {detected_times}")
            
            # Also try to find all visible elements that might be time slots
            logger.info("Searching for all visible time-like elements...")
            visible_elements = await self._find_all_time_elements(page)
            logger.info(f"Found {len(visible_elements)} visible time-like elements")
            
            # Highlight detected slots and take screenshot
            if detected_buttons:
                logger.info("Highlighting detected time slots...")
                for button in detected_buttons:
                    await self._highlight_element(page, button)
                    
            highlighted_path = self.debug_dir / f"court_{court_num}_highlighted.png"
            await page.screenshot(path=str(highlighted_path), full_page=True)
            logger.info(f"Saved highlighted screenshot: {highlighted_path}")
            
            # Extract day labels
            day_labels = await self.day_mapper.extract_day_labels(page)
            logger.info(f"Detected day labels: {[label.text for label in day_labels]}")
            
            # Save page HTML for further analysis
            html_path = self.debug_dir / f"court_{court_num}_page.html"
            html_content = await page.content()
            html_path.write_text(html_content, encoding='utf-8')
            logger.info(f"Saved page HTML: {html_path}")
            
            # Create analysis result
            result = {
                "court": court_num,
                "url": court_url,
                "no_availability": False,
                "screenshots": {
                    "initial": str(screenshot_path),
                    "highlighted": str(highlighted_path)
                },
                "html_file": str(html_path),
                "detected_slots": detected_times,
                "visible_elements": visible_elements,
                "day_labels": [label.text for label in day_labels],
                "selector_results": await self._test_all_selectors(page),
                "analysis_time": datetime.now().isoformat()
            }
            
            return result
            
        except Exception as e:
            logger.error(f"Error analyzing Court {court_num}: {e}", exc_info=True)
            error_screenshot = self.debug_dir / f"court_{court_num}_error.png"
            await page.screenshot(path=str(error_screenshot))
            return {
                "court": court_num,
                "url": court_url,
                "error": str(e),
                "screenshot": str(error_screenshot)
            }
            
        finally:
            await page.close()
            
    async def _check_no_availability(self, page: Page) -> bool:
        """Check if page shows no availability message"""
        patterns = [
            'No hay citas disponibles',
            'no hay horarios disponibles',
            'sin disponibilidad',
            'No hay disponibilidad',
            'no availability',
            'no available times',
            'No times available',
            'No appointments available'
        ]
        
        for pattern in patterns:
            elements = await page.query_selector_all(f'*:has-text("{pattern}")')
            if elements:
                return True
        return False
        
    async def _find_all_time_elements(self, page: Page) -> List[Dict]:
        """Find all elements that might contain time information"""
        visible_elements = []
        
        # Search for elements containing time patterns
        time_patterns = [
            # 24-hour format
            r'\b([01]?[0-9]|2[0-3]):[0-5][0-9]\b',
            # 12-hour format with AM/PM
            r'\b(1[0-2]|0?[1-9]):[0-5][0-9]\s*(AM|PM|am|pm)\b',
            # Simple hour format
            r'\b(1[0-2]|0?[1-9])\s*(AM|PM|am|pm)\b'
        ]
        
        # Find all text elements
        all_elements = await page.query_selector_all('*')
        
        for element in all_elements:
            try:
                text = await element.text_content()
                if not text:
                    continue
                    
                # Check if element contains time-like text
                import re
                for pattern in time_patterns:
                    if re.search(pattern, text.strip()):
                        tag_name = await element.evaluate('el => el.tagName')
                        class_name = await element.get_attribute('class') or ''
                        is_visible = await element.is_visible()
                        is_button = tag_name.lower() == 'button'
                        
                        visible_elements.append({
                            'text': text.strip(),
                            'tag': tag_name,
                            'class': class_name,
                            'is_visible': is_visible,
                            'is_button': is_button,
                            'selector': await self._get_element_selector(element)
                        })
                        break
                        
            except Exception as e:
                # Skip elements that cause errors
                continue
                
        return visible_elements
        
    async def _get_element_selector(self, element) -> str:
        """Try to get a useful selector for an element"""
        try:
            # Try to get a unique selector
            tag = await element.evaluate('el => el.tagName.toLowerCase()')
            class_attr = await element.get_attribute('class')
            id_attr = await element.get_attribute('id')
            
            if id_attr:
                return f"#{id_attr}"
            elif class_attr:
                classes = class_attr.split()[:2]  # Use first 2 classes
                return f"{tag}.{'.'.join(classes)}"
            else:
                return tag
        except:
            return "unknown"
            
    async def _highlight_element(self, page: Page, element):
        """Highlight an element on the page"""
        try:
            await page.evaluate('''
                element => {
                    element.style.border = "3px solid red";
                    element.style.backgroundColor = "rgba(255, 0, 0, 0.2)";
                    element.style.boxShadow = "0 0 10px red";
                }
            ''', element)
        except:
            pass  # Ignore errors in highlighting
            
    async def _test_all_selectors(self, page: Page) -> Dict:
        """Test all configured selectors and see what they find"""
        selector_results = {}
        
        for selector in TIME_SLOT_SELECTORS:
            try:
                elements = await page.query_selector_all(selector)
                if elements:
                    # Get text from first few elements as sample
                    sample_texts = []
                    for i, elem in enumerate(elements[:3]):
                        text = await elem.text_content()
                        if text:
                            sample_texts.append(text.strip())
                            
                    selector_results[selector] = {
                        "count": len(elements),
                        "sample_texts": sample_texts
                    }
                else:
                    selector_results[selector] = {"count": 0}
                    
            except Exception as e:
                selector_results[selector] = {"error": str(e)}
                
        return selector_results
        
    async def compare_with_bot(self) -> Dict:
        """Compare debug results with what the actual bot sees"""
        logger.info("\n" + "="*60)
        logger.info("Comparing with actual bot detection...")
        logger.info("="*60)
        
        # Initialize browser pool as the bot would
        browser_pool = AsyncBrowserPool()
        await browser_pool.start()
        
        try:
            # Use the bot's availability checker
            checker = AvailabilityCheckerV3(browser_pool)
            bot_results = await checker.check_availability()
            
            # Format for comparison
            comparison = {}
            for court_num, dates_data in bot_results.items():
                if isinstance(dates_data, dict) and "error" in dates_data:
                    comparison[court_num] = {
                        "bot_detected": "error",
                        "error": dates_data["error"]
                    }
                else:
                    # Flatten all times from all dates
                    all_times = []
                    for date_str, times in dates_data.items():
                        all_times.extend(times)
                    comparison[court_num] = {
                        "bot_detected": sorted(list(set(all_times))),
                        "dates": dates_data
                    }
                    
            return comparison
            
        finally:
            await browser_pool.stop()
            
    async def run_full_debug(self):
        """Run complete debugging analysis"""
        await self.initialize()
        
        try:
            # Analyze each court
            court_results = {}
            for court_num in [1, 2, 3]:
                result = await self.analyze_court_page(court_num)
                court_results[court_num] = result
                
            # Compare with bot detection
            bot_comparison = await self.compare_with_bot()
            
            # Create summary report
            summary = {
                "debug_time": datetime.now().isoformat(),
                "court_analysis": court_results,
                "bot_comparison": bot_comparison,
                "summary": self._create_summary(court_results, bot_comparison)
            }
            
            # Save results
            results_path = self.debug_dir / "debug_results.json"
            with open(results_path, 'w', encoding='utf-8') as f:
                json.dump(summary, f, indent=2, ensure_ascii=False)
                
            # Create markdown report
            report_path = self.debug_dir / "debug_report.md"
            self._create_markdown_report(summary, report_path)
            
            logger.info(f"\n{'='*60}")
            logger.info(f"Debug analysis complete!")
            logger.info(f"Results saved to: {self.debug_dir}")
            logger.info(f"Report: {report_path}")
            logger.info(f"{'='*60}")
            
        finally:
            await self.cleanup()
            
    def _create_summary(self, court_results: Dict, bot_comparison: Dict) -> Dict:
        """Create summary of findings"""
        summary = {}
        
        for court_num in [1, 2, 3]:
            court_data = court_results.get(court_num, {})
            bot_data = bot_comparison.get(court_num, {})
            
            if "error" in court_data:
                summary[f"court_{court_num}"] = {
                    "status": "error",
                    "error": court_data["error"]
                }
            else:
                debug_slots = court_data.get("detected_slots", [])
                bot_slots = bot_data.get("bot_detected", [])
                
                summary[f"court_{court_num}"] = {
                    "debug_detected": len(debug_slots),
                    "bot_detected": len(bot_slots) if isinstance(bot_slots, list) else bot_slots,
                    "match": debug_slots == bot_slots if isinstance(bot_slots, list) else False,
                    "debug_slots": debug_slots,
                    "bot_slots": bot_slots if isinstance(bot_slots, list) else [],
                    "visible_elements": len(court_data.get("visible_elements", []))
                }
                
        return summary
        
    def _create_markdown_report(self, summary: Dict, report_path: Path):
        """Create a markdown report of the findings"""
        lines = [
            "# LVBOT Court Availability Debug Report",
            f"\nGenerated: {summary['debug_time']}",
            "\n## Summary\n"
        ]
        
        # Add summary table
        lines.append("| Court | Debug Detected | Bot Detected | Match | Visible Elements |")
        lines.append("|-------|----------------|--------------|-------|------------------|")
        
        for court_num in [1, 2, 3]:
            s = summary['summary'].get(f'court_{court_num}', {})
            if s.get('status') == 'error':
                lines.append(f"| {court_num} | ERROR | - | - | - |")
            else:
                match = "✅" if s.get('match') else "❌"
                lines.append(f"| {court_num} | {s.get('debug_detected', 0)} | {s.get('bot_detected', 0)} | {match} | {s.get('visible_elements', 0)} |")
                
        # Add detailed findings
        lines.append("\n## Detailed Findings\n")
        
        for court_num in [1, 2, 3]:
            court_data = summary['court_analysis'].get(court_num, {})
            lines.append(f"\n### Court {court_num}")
            
            if "error" in court_data:
                lines.append(f"\n**Error**: {court_data['error']}")
            else:
                lines.append(f"\n**URL**: {court_data.get('url', 'N/A')}")
                lines.append(f"\n**Screenshots**:")
                lines.append(f"- Initial: {court_data.get('screenshots', {}).get('initial', 'N/A')}")
                lines.append(f"- Highlighted: {court_data.get('screenshots', {}).get('highlighted', 'N/A')}")
                
                detected = court_data.get('detected_slots', [])
                lines.append(f"\n**Detected Slots** ({len(detected)}): {', '.join(detected) if detected else 'None'}")
                
                # Add selector results
                selector_results = court_data.get('selector_results', {})
                if selector_results:
                    lines.append("\n**Selector Test Results**:")
                    for selector, result in selector_results.items():
                        if isinstance(result, dict) and result.get('count', 0) > 0:
                            lines.append(f"- `{selector}`: {result['count']} elements")
                            if result.get('sample_texts'):
                                lines.append(f"  - Samples: {', '.join(result['sample_texts'][:3])}")
                                
        # Save report
        report_path.write_text('\n'.join(lines), encoding='utf-8')
        

async def main():
    """Main entry point"""
    debugger = CourtAvailabilityDebugger()
    await debugger.run_full_debug()


if __name__ == "__main__":
    asyncio.run(main())
