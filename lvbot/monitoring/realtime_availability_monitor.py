#!/usr/bin/env python3
"""
Real-time Availability Monitor for LVBOT
======================================

Purpose: Monitor in real-time what the bot detects vs what's actually available.
Shows live updates and takes periodic screenshots for comparison.
"""

import asyncio
import logging
from datetime import datetime
from pathlib import Path
from typing import Dict, List, Optional
import json
from playwright.async_api import async_playwright, Page

# Import existing modules
from lvbot.utils.constants import COURT_CONFIG
from lvbot.automation.browser.async_browser_pool import AsyncBrowserPool
from lvbot.automation.availability.availability_checker_v3 import AvailabilityCheckerV3

# Configure logging with colors for better visibility
class ColoredFormatter(logging.Formatter):
    """Custom formatter with colors"""
    
    COLORS = {
        'DEBUG': '\033[36m',    # Cyan
        'INFO': '\033[32m',     # Green
        'WARNING': '\033[33m',  # Yellow
        'ERROR': '\033[31m',    # Red
        'CRITICAL': '\033[35m', # Magenta
    }
    RESET = '\033[0m'
    
    def format(self, record):
        log_color = self.COLORS.get(record.levelname, self.RESET)
        record.levelname = f"{log_color}{record.levelname}{self.RESET}"
        return super().format(record)

# Set up colored logging
handler = logging.StreamHandler()
handler.setFormatter(ColoredFormatter('%(asctime)s - %(levelname)s - %(message)s'))
logger = logging.getLogger(__name__)
logger.setLevel(logging.INFO)
logger.addHandler(handler)


class RealtimeAvailabilityMonitor:
    """Monitor court availability in real-time"""
    
    def __init__(self, refresh_interval: int = 5):
        self.refresh_interval = refresh_interval
        self.browser_pool = None
        self.checker = None
        self.playwright = None
        self.browser = None
        self.monitoring_page = None
        self.last_results = {}
        self.change_history = []
        self.session_dir = None
        
    async def initialize(self):
        """Initialize monitoring session"""
        # Create session directory
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        self.session_dir = Path(f"realtime_monitor_{timestamp}")
        self.session_dir.mkdir(exist_ok=True)
        
        # Initialize browser pool (as bot would)
        logger.info("Initializing browser pool...")
        self.browser_pool = AsyncBrowserPool()
        await self.browser_pool.start()
        
        # Initialize availability checker
        self.checker = AvailabilityCheckerV3(self.browser_pool)
        
        # Initialize separate browser for monitoring/screenshots
        self.playwright = await async_playwright().start()
        self.browser = await self.playwright.chromium.launch(
            headless=False,
            args=['--window-size=1920,1080', '--window-position=0,0']
        )
        
        logger.info("✅ Monitor initialized successfully")
        
    async def cleanup(self):
        """Clean up resources"""
        if self.monitoring_page:
            await self.monitoring_page.close()
        if self.browser:
            await self.browser.close()
        if self.playwright:
            await self.playwright.stop()
        if self.browser_pool:
            await self.browser_pool.stop()
            
    async def take_court_screenshot(self, court_num: int) -> Optional[Path]:
        """Take a screenshot of a specific court page"""
        try:
            if not self.monitoring_page:
                self.monitoring_page = await self.browser.new_page()
                
            court_url = COURT_CONFIG[court_num]["direct_url"]
            await self.monitoring_page.goto(court_url, wait_until='domcontentloaded')
            await asyncio.sleep(2)  # Let page stabilize
            
            timestamp = datetime.now().strftime("%H%M%S")
            screenshot_path = self.session_dir / f"court_{court_num}_{timestamp}.png"
            await self.monitoring_page.screenshot(path=str(screenshot_path))
            
            return screenshot_path
            
        except Exception as e:
            logger.error(f"Failed to screenshot court {court_num}: {e}")
            return None
            
    def format_availability_change(self, court_num: int, old_data: Dict, new_data: Dict) -> str:
        """Format availability changes for logging"""
        old_times = []
        new_times = []
        
        # Extract times from old data
        if isinstance(old_data, dict) and "error" not in old_data:
            for times in old_data.values():
                old_times.extend(times)
                
        # Extract times from new data
        if isinstance(new_data, dict) and "error" not in new_data:
            for times in new_data.values():
                new_times.extend(times)
                
        old_set = set(old_times)
        new_set = set(new_times)
        
        added = new_set - old_set
        removed = old_set - new_set
        
        changes = []
        if added:
            changes.append(f"➕ Added: {', '.join(sorted(added))}")
        if removed:
            changes.append(f"➖ Removed: {', '.join(sorted(removed))}")
            
        return " | ".join(changes) if changes else "No changes"
        
    async def monitor_loop(self):
        """Main monitoring loop"""
        iteration = 0
        
        while True:
            iteration += 1
            logger.info(f"\n{'='*60}")
            logger.info(f"🔄 Checking availability (iteration {iteration})")
            
            try:
                # Check availability using bot's method
                current_results = await self.checker.check_availability()
                
                # Process and display results
                for court_num in sorted(current_results.keys()):
                    court_data = current_results[court_num]
                    
                    if isinstance(court_data, dict) and "error" in court_data:
                        logger.error(f"Court {court_num}: ❌ {court_data['error']}")
                        continue
                        
                    # Count total slots
                    total_slots = 0
                    all_times = []
                    for date_str, times in court_data.items():
                        total_slots += len(times)
                        all_times.extend(times)
                        
                    # Check for changes
                    old_data = self.last_results.get(court_num, {})
                    has_changed = old_data != court_data
                    
                    # Log status
                    status_emoji = "🆕" if has_changed else "✅"
                    logger.info(f"Court {court_num}: {status_emoji} {total_slots} slots - {', '.join(sorted(set(all_times)))}")
                    
                    # If changed, log details and take screenshot
                    if has_changed and old_data:
                        change_desc = self.format_availability_change(court_num, old_data, court_data)
                        logger.warning(f"  └─ Changes detected: {change_desc}")
                        
                        # Take screenshot of changed court
                        screenshot = await self.take_court_screenshot(court_num)
                        if screenshot:
                            logger.info(f"  └─ Screenshot saved: {screenshot.name}")
                            
                        # Record change
                        self.change_history.append({
                            'timestamp': datetime.now().isoformat(),
                            'court': court_num,
                            'change': change_desc,
                            'old_data': old_data,
                            'new_data': court_data,
                            'screenshot': str(screenshot) if screenshot else None
                        })
                        
                # Update last results
                self.last_results = current_results
                
                # Save current state
                await self.save_state()
                
                # Display summary
                total_slots_all = sum(
                    sum(len(times) for times in data.values())
                    for data in current_results.values()
                    if isinstance(data, dict) and "error" not in data
                )
                logger.info(f"\n📊 Total slots across all courts: {total_slots_all}")
                
                # Check if any court has high availability
                for court_num, data in current_results.items():
                    if isinstance(data, dict) and "error" not in data:
                        slot_count = sum(len(times) for times in data.values())
                        if slot_count > 5:
                            logger.warning(f"⚠️  Court {court_num} has HIGH availability ({slot_count} slots)!")
                            
            except Exception as e:
                logger.error(f"Error in monitoring loop: {e}", exc_info=True)
                
            # Wait before next check
            logger.info(f"\n⏳ Next check in {self.refresh_interval} seconds...")
            await asyncio.sleep(self.refresh_interval)
            
    async def save_state(self):
        """Save current monitoring state"""
        state = {
            'last_update': datetime.now().isoformat(),
            'current_availability': self.last_results,
            'change_history': self.change_history[-50:]  # Keep last 50 changes
        }
        
        state_file = self.session_dir / 'monitor_state.json'
        with open(state_file, 'w') as f:
            json.dump(state, f, indent=2)
            
    async def run(self, duration_minutes: Optional[int] = None):
        """Run the monitor for specified duration or indefinitely"""
        await self.initialize()
        
        try:
            if duration_minutes:
                logger.info(f"🚀 Starting monitor for {duration_minutes} minutes")
                await asyncio.wait_for(
                    self.monitor_loop(),
                    timeout=duration_minutes * 60
                )
            else:
                logger.info("🚀 Starting monitor (press Ctrl+C to stop)")
                await self.monitor_loop()
                
        except asyncio.TimeoutError:
            logger.info("⏱️  Monitoring duration completed")
        except KeyboardInterrupt:
            logger.info("\n⛔ Monitor stopped by user")
        finally:
            # Save final report
            await self.create_final_report()
            await self.cleanup()
            
    async def create_final_report(self):
        """Create a final report of the monitoring session"""
        report = {
            'session_start': self.change_history[0]['timestamp'] if self.change_history else None,
            'session_end': datetime.now().isoformat(),
            'total_changes': len(self.change_history),
            'final_availability': self.last_results,
            'change_summary': self._summarize_changes()
        }
        
        report_path = self.session_dir / 'final_report.json'
        with open(report_path, 'w') as f:
            json.dump(report, f, indent=2)
            
        # Create markdown summary
        md_report = self._create_markdown_report(report)
        md_path = self.session_dir / 'session_summary.md'
        md_path.write_text(md_report, encoding='utf-8')
        
        logger.info(f"\n📄 Final report saved to: {self.session_dir}")
        
    def _summarize_changes(self) -> Dict:
        """Summarize all changes by court"""
        summary = {}
        
        for change in self.change_history:
            court = change['court']
            if court not in summary:
                summary[court] = {
                    'total_changes': 0,
                    'slots_added': 0,
                    'slots_removed': 0
                }
                
            summary[court]['total_changes'] += 1
            
            # Parse change description
            change_desc = change['change']
            if 'Added:' in change_desc:
                added_count = len(change_desc.split('Added:')[1].split(','))
                summary[court]['slots_added'] += added_count
            if 'Removed:' in change_desc:
                removed_count = len(change_desc.split('Removed:')[1].split(','))
                summary[court]['slots_removed'] += removed_count
                
        return summary
        
    def _create_markdown_report(self, report: Dict) -> str:
        """Create a markdown report"""
        lines = [
            "# LVBOT Real-time Monitoring Session Report",
            f"\n**Session Duration**: {report['session_start']} to {report['session_end']}",
            f"\n**Total Changes Detected**: {report['total_changes']}",
            "\n## Final Availability\n"
        ]
        
        # Add final availability
        for court_num in sorted(report['final_availability'].keys()):
            data = report['final_availability'][court_num]
            if isinstance(data, dict) and "error" not in data:
                total_slots = sum(len(times) for times in data.values())
                lines.append(f"- **Court {court_num}**: {total_slots} slots")
                for date_str, times in sorted(data.items()):
                    if times:
                        lines.append(f"  - {date_str}: {', '.join(sorted(times))}")
                        
        # Add change summary
        lines.append("\n## Change Summary by Court\n")
        
        for court_num, stats in report['change_summary'].items():
            lines.append(f"\n### Court {court_num}")
            lines.append(f"- Total changes: {stats['total_changes']}")
            lines.append(f"- Slots added: {stats['slots_added']}")
            lines.append(f"- Slots removed: {stats['slots_removed']}")
            
        return '\n'.join(lines)


async def main():
    """Main entry point"""
    import argparse
    
    parser = argparse.ArgumentParser(description='Real-time LVBOT availability monitor')
    parser.add_argument('--interval', type=int, default=5, 
                       help='Refresh interval in seconds (default: 5)')
    parser.add_argument('--duration', type=int, 
                       help='Duration to run in minutes (omit for indefinite)')
    
    args = parser.parse_args()
    
    monitor = RealtimeAvailabilityMonitor(refresh_interval=args.interval)
    await monitor.run(duration_minutes=args.duration)


if __name__ == "__main__":
    asyncio.run(main())
