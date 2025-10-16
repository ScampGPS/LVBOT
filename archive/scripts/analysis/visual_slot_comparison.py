#!/usr/bin/env python3
"""
Visual Slot Comparison Tool for LVBOT
====================================

Purpose: Visually compare what slots are shown on screen vs what the bot detects.
Creates side-by-side comparisons and detailed analysis.
"""
from tracking import t
import pathlib
import sys

ROOT_DIR = pathlib.Path(__file__).resolve().parents[2]
if str(ROOT_DIR) not in sys.path:
    sys.path.insert(0, str(ROOT_DIR))


import asyncio
import logging
from datetime import datetime
from pathlib import Path
from typing import Dict, List, Optional
from playwright.async_api import async_playwright, Page
from PIL import Image, ImageDraw, ImageFont
import json

# Import existing modules
from lvbot.utils.constants import COURT_CONFIG, TIME_BUTTON_SELECTOR, TIME_SLOT_SELECTORS
from lvbot.utils.time_slot_extractor import TimeSlotExtractor

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)


class VisualSlotComparison:
    """Tool for visual comparison of available slots"""
    
    def __init__(self):
        t('archive.scripts.analysis.visual_slot_comparison.VisualSlotComparison.__init__')
        self.time_extractor = TimeSlotExtractor()
        self.playwright = None
        self.browser = None
        self.timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        self.output_dir = Path(f"visual_comparison_{self.timestamp}")
        self.output_dir.mkdir(exist_ok=True)
        
    async def initialize(self):
        """Initialize browser"""
        t('archive.scripts.analysis.visual_slot_comparison.VisualSlotComparison.initialize')
        self.playwright = await async_playwright().start()
        self.browser = await self.playwright.chromium.launch(
            headless=False,
            args=['--window-size=1920,1080']
        )
        
    async def cleanup(self):
        """Clean up resources"""
        t('archive.scripts.analysis.visual_slot_comparison.VisualSlotComparison.cleanup')
        if self.browser:
            await self.browser.close()
        if self.playwright:
            await self.playwright.stop()
            
    async def analyze_and_annotate_court(self, court_num: int) -> Dict:
        """
        Analyze a court page and create annotated screenshots
        """
        t('archive.scripts.analysis.visual_slot_comparison.VisualSlotComparison.analyze_and_annotate_court')
        court_config = COURT_CONFIG.get(court_num)
        if not court_config:
            return {"error": f"Invalid court number: {court_num}"}
            
        logger.info(f"\nAnalyzing Court {court_num}")
        logger.info(f"URL: {court_config['direct_url']}")
        
        page = await self.browser.new_page()
        
        try:
            # Navigate to court
            await page.goto(court_config['direct_url'], wait_until='domcontentloaded')
            await asyncio.sleep(3)  # Let page stabilize
            
            # Take clean screenshot
            clean_screenshot = self.output_dir / f"court_{court_num}_clean.png"
            await page.screenshot(path=str(clean_screenshot), full_page=True)
            
            # Find all time buttons using bot's method
            detected_buttons = await self.time_extractor.extract_all_time_buttons(page)
            detected_times = []
            button_bounds = []
            
            for button in detected_buttons:
                time_text = await self.time_extractor.extract_time_text(button)
                if time_text:
                    detected_times.append(time_text)
                    # Get button position for annotation
                    try:
                        bounds = await button.bounding_box()
                        if bounds:
                            button_bounds.append({
                                'time': time_text,
                                'bounds': bounds
                            })
                    except:
                        pass
                        
            # Find all clickable elements for comparison
            all_buttons = await page.query_selector_all('button')
            all_clickable = []
            
            for button in all_buttons:
                try:
                    text = await button.text_content()
                    if text and ':' in text:  # Likely a time
                        bounds = await button.bounding_box()
                        if bounds:
                            all_clickable.append({
                                'text': text.strip(),
                                'bounds': bounds,
                                'detected': text.strip() in detected_times
                            })
                except:
                    continue
                    
            # Create annotated screenshot
            annotated_path = await self._create_annotated_screenshot(
                clean_screenshot,
                button_bounds,
                all_clickable,
                court_num
            )
            
            # Test each selector individually and document results
            selector_results = await self._test_selectors_with_screenshots(page, court_num)
            
            # Create comparison data
            result = {
                'court': court_num,
                'url': court_config['direct_url'],
                'detected_count': len(detected_times),
                'detected_times': detected_times,
                'all_clickable_count': len(all_clickable),
                'screenshots': {
                    'clean': str(clean_screenshot),
                    'annotated': str(annotated_path)
                },
                'selector_results': selector_results,
                'button_analysis': {
                    'detected_by_bot': len(button_bounds),
                    'total_time_buttons': len([b for b in all_clickable if b.get('detected')]),
                    'missed_buttons': len([b for b in all_clickable if not b.get('detected')])
                }
            }
            
            # Log findings
            logger.info(f"Court {court_num} Results:")
            logger.info(f"  - Bot detected: {len(detected_times)} slots")
            logger.info(f"  - Times found: {detected_times}")
            logger.info(f"  - Total clickable time elements: {len(all_clickable)}")
            
            return result
            
        except Exception as e:
            logger.error(f"Error analyzing court {court_num}: {e}")
            return {'court': court_num, 'error': str(e)}
            
        finally:
            await page.close()
            
    async def _create_annotated_screenshot(self, screenshot_path: Path, 
                                         detected_buttons: List[Dict],
                                         all_buttons: List[Dict],
                                         court_num: int) -> Path:
        """Create an annotated screenshot showing detected vs missed slots"""
        t('archive.scripts.analysis.visual_slot_comparison.VisualSlotComparison._create_annotated_screenshot')
        try:
            # Open the screenshot
            img = Image.open(screenshot_path)
            draw = ImageDraw.Draw(img)
            
            # Try to load a font, fall back to default if not available
            try:
                font = ImageFont.truetype("arial.ttf", 16)
                small_font = ImageFont.truetype("arial.ttf", 12)
            except:
                font = ImageFont.load_default()
                small_font = font
                
            # Draw rectangles around detected buttons (green)
            for button_info in detected_buttons:
                bounds = button_info['bounds']
                x, y, w, h = bounds['x'], bounds['y'], bounds['width'], bounds['height']
                draw.rectangle([x, y, x + w, y + h], outline='green', width=3)
                draw.text((x, y - 20), f"✓ {button_info['time']}", fill='green', font=font)
                
            # Draw rectangles around missed buttons (red)
            for button in all_buttons:
                if not button.get('detected'):
                    bounds = button['bounds']
                    x, y, w, h = bounds['x'], bounds['y'], bounds['width'], bounds['height']
                    draw.rectangle([x, y, x + w, y + h], outline='red', width=2)
                    draw.text((x, y - 20), f"✗ {button['text']}", fill='red', font=small_font)
                    
            # Add legend
            legend_y = 10
            draw.rectangle([10, legend_y, 300, legend_y + 80], fill='white', outline='black')
            draw.text((20, legend_y + 10), f"Court {court_num} Analysis", fill='black', font=font)
            draw.text((20, legend_y + 30), "Green = Bot Detected", fill='green', font=small_font)
            draw.text((20, legend_y + 45), "Red = Missed by Bot", fill='red', font=small_font)
            draw.text((20, legend_y + 60), f"Detected: {len(detected_buttons)} slots", fill='black', font=small_font)
            
            # Save annotated image
            annotated_path = self.output_dir / f"court_{court_num}_annotated.png"
            img.save(annotated_path)
            
            return annotated_path
            
        except Exception as e:
            logger.error(f"Error creating annotated screenshot: {e}")
            return screenshot_path
            
    async def _test_selectors_with_screenshots(self, page: Page, court_num: int) -> Dict:
        """Test each selector and document what it finds"""
        t('archive.scripts.analysis.visual_slot_comparison.VisualSlotComparison._test_selectors_with_screenshots')
        selector_results = {}
        
        for i, selector in enumerate(TIME_SLOT_SELECTORS[:5]):  # Test first 5 selectors
            try:
                # Find elements with this selector
                elements = await page.query_selector_all(selector)
                
                if elements:
                    # Highlight elements found by this selector
                    for elem in elements:
                        await page.evaluate('''
                            (element) => {
                                element.style.border = "2px solid blue";
                                element.style.backgroundColor = "rgba(0, 0, 255, 0.1)";
                            }
                        ''', elem)
                        
                    # Take screenshot
                    selector_screenshot = self.output_dir / f"court_{court_num}_selector_{i}.png"
                    await page.screenshot(path=str(selector_screenshot))
                    
                    # Get sample texts
                    sample_texts = []
                    for elem in elements[:3]:
                        text = await elem.text_content()
                        if text:
                            sample_texts.append(text.strip())
                            
                    selector_results[selector] = {
                        'count': len(elements),
                        'samples': sample_texts,
                        'screenshot': str(selector_screenshot)
                    }
                    
                    # Reset styles
                    for elem in elements:
                        await page.evaluate('''
                            (element) => {
                                element.style.border = "";
                                element.style.backgroundColor = "";
                            }
                        ''', elem)
                        
                else:
                    selector_results[selector] = {'count': 0}
                    
            except Exception as e:
                selector_results[selector] = {'error': str(e)}
                
        return selector_results
        
    async def create_comparison_report(self):
        """Create a comprehensive comparison report"""
        t('archive.scripts.analysis.visual_slot_comparison.VisualSlotComparison.create_comparison_report')
        await self.initialize()
        
        try:
            # Analyze all courts
            results = {}
            for court_num in [1, 2, 3]:
                results[court_num] = await self.analyze_and_annotate_court(court_num)
                
            # Create summary report
            report = {
                'timestamp': self.timestamp,
                'courts': results,
                'summary': self._create_summary(results)
            }
            
            # Save JSON report
            report_path = self.output_dir / 'comparison_report.json'
            with open(report_path, 'w') as f:
                json.dump(report, f, indent=2)
                
            # Create HTML report for easy viewing
            html_report = self._create_html_report(report)
            html_path = self.output_dir / 'comparison_report.html'
            html_path.write_text(html_report, encoding='utf-8')
            
            logger.info(f"\n{'='*60}")
            logger.info(f"Visual comparison complete!")
            logger.info(f"Results saved to: {self.output_dir}")
            logger.info(f"Open {html_path} to view the report")
            logger.info(f"{'='*60}")
            
        finally:
            await self.cleanup()
            
    def _create_summary(self, results: Dict) -> Dict:
        """Create summary statistics"""
        t('archive.scripts.analysis.visual_slot_comparison.VisualSlotComparison._create_summary')
        summary = {
            'total_detected': 0,
            'courts': {}
        }
        
        for court_num, data in results.items():
            if 'error' not in data:
                detected = data.get('detected_count', 0)
                summary['total_detected'] += detected
                summary['courts'][court_num] = {
                    'detected': detected,
                    'times': data.get('detected_times', [])
                }
                
        return summary
        
    def _create_html_report(self, report: Dict) -> str:
        """Create an HTML report for easy viewing"""
        t('archive.scripts.analysis.visual_slot_comparison.VisualSlotComparison._create_html_report')
        html = f"""
        <!DOCTYPE html>
        <html>
        <head>
            <title>LVBOT Visual Comparison Report</title>
            <style>
                body {{ font-family: Arial, sans-serif; margin: 20px; }}
                .court {{ margin: 20px 0; padding: 20px; border: 1px solid #ccc; }}
                .screenshots {{ display: flex; gap: 20px; margin: 20px 0; }}
                .screenshot {{ text-align: center; }}
                .screenshot img {{ max-width: 400px; border: 1px solid #ddd; }}
                .stats {{ background: #f0f0f0; padding: 10px; margin: 10px 0; }}
                .detected {{ color: green; font-weight: bold; }}
                .missed {{ color: red; font-weight: bold; }}
            </style>
        </head>
        <body>
            <h1>LVBOT Visual Slot Comparison Report</h1>
            <p>Generated: {report['timestamp']}</p>
            
            <div class="stats">
                <h2>Summary</h2>
                <p>Total slots detected across all courts: <span class="detected">{report['summary']['total_detected']}</span></p>
            </div>
        """
        
        for court_num in [1, 2, 3]:
            court_data = report['courts'].get(court_num, {})
            if 'error' in court_data:
                html += f"""
                <div class="court">
                    <h2>Court {court_num}</h2>
                    <p class="missed">Error: {court_data['error']}</p>
                </div>
                """
            else:
                html += f"""
                <div class="court">
                    <h2>Court {court_num}</h2>
                    <p>URL: {court_data.get('url', 'N/A')}</p>
                    <div class="stats">
                        <p>Detected by bot: <span class="detected">{court_data.get('detected_count', 0)}</span> slots</p>
                        <p>Times: {', '.join(court_data.get('detected_times', []))}</p>
                        <p>Total clickable time elements: {court_data.get('all_clickable_count', 0)}</p>
                    </div>
                    
                    <div class="screenshots">
                        <div class="screenshot">
                            <h3>Clean Screenshot</h3>
                            <img src="{Path(court_data['screenshots']['clean']).name}" />
                        </div>
                        <div class="screenshot">
                            <h3>Annotated Screenshot</h3>
                            <img src="{Path(court_data['screenshots']['annotated']).name}" />
                        </div>
                    </div>
                </div>
                """
                
        html += """
        </body>
        </html>
        """
        
        return html


async def main():
    """Main entry point"""
    t('archive.scripts.analysis.visual_slot_comparison.main')
    tool = VisualSlotComparison()
    await tool.create_comparison_report()


if __name__ == "__main__":
    asyncio.run(main())
