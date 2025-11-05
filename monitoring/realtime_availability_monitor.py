#!/usr/bin/env python3
"""Real-time court availability monitor backed by the bot poller."""

from __future__ import annotations

import asyncio
import json
import logging
from datetime import datetime
from pathlib import Path
from typing import Dict, List, Optional

from tracking import t
from playwright.async_api import async_playwright, Page

from automation.availability import AvailabilityChecker
from automation.browser.async_browser_pool import AsyncBrowserPool
from infrastructure.constants import COURT_CONFIG
from monitoring.availability_poller import AvailabilityChange, AvailabilityPoller, PollSnapshot

# ----------------------------------------------------------------------------
# Logging with optional colours for easier CLI reading
# ----------------------------------------------------------------------------

class ColouredFormatter(logging.Formatter):
    COLORS = {
        'DEBUG': '\033[36m',
        'INFO': '\033[32m',
        'WARNING': '\033[33m',
        'ERROR': '\033[31m',
        'CRITICAL': '\033[35m',
    }
    RESET = '\033[0m'

    def format(self, record):  # pragma: no cover - cosmetics only
        t('monitoring.realtime_availability_monitor.ColouredFormatter.format')
        colour = self.COLORS.get(record.levelname, self.RESET)
        record.levelname = f"{colour}{record.levelname}{self.RESET}"
        return super().format(record)


_handler = logging.StreamHandler()
_handler.setFormatter(ColouredFormatter('%(asctime)s - %(levelname)s - %(message)s'))
logger = logging.getLogger(__name__)
logger.setLevel(logging.INFO)
logger.addHandler(_handler)


# ----------------------------------------------------------------------------
# Monitor implementation
# ----------------------------------------------------------------------------


class RealtimeAvailabilityMonitor:
    """Polls availability at a fixed interval and records changes."""

    def __init__(self, refresh_interval: int = 5) -> None:
        t('monitoring.realtime_availability_monitor.RealtimeAvailabilityMonitor.__init__')
        self.refresh_interval = refresh_interval
        self.browser_pool: Optional[AsyncBrowserPool] = None
        self.checker: Optional[AvailabilityChecker] = None
        self.poller: Optional[AvailabilityPoller] = None
        self.playwright = None
        self.browser = None
        self.monitoring_page: Optional[Page] = None
        self.session_dir: Optional[Path] = None
        self.last_snapshot: Optional[PollSnapshot] = None
        self.change_history: List[Dict[str, object]] = []

    # ------------------------------------------------------------------
    # Lifecycle helpers
    # ------------------------------------------------------------------
    async def initialize(self) -> None:
        t('monitoring.realtime_availability_monitor.RealtimeAvailabilityMonitor.initialize')
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        self.session_dir = Path(f"realtime_monitor_{timestamp}")
        self.session_dir.mkdir(exist_ok=True)

        logger.info("Initializing browser pool...")
        self.browser_pool = AsyncBrowserPool()
        await self.browser_pool.start()

        self.checker = AvailabilityChecker(self.browser_pool)
        self.poller = AvailabilityPoller(self.checker.check_availability, logger=logger)

        self.playwright = await async_playwright().start()
        self.browser = await self.playwright.chromium.launch(
            headless=False,
            args=['--window-size=1920,1080', '--window-position=0,0'],
        )
        logger.info("✅ Monitor initialized successfully")

    async def cleanup(self) -> None:
        t('monitoring.realtime_availability_monitor.RealtimeAvailabilityMonitor.cleanup')
        if self.monitoring_page:
            await self.monitoring_page.close()
        if self.browser:
            await self.browser.close()
        if self.playwright:
            await self.playwright.stop()
        if self.browser_pool:
            await self.browser_pool.stop()

    # ------------------------------------------------------------------
    # Core monitoring loop
    # ------------------------------------------------------------------
    async def monitor_loop(self) -> None:
        t('monitoring.realtime_availability_monitor.RealtimeAvailabilityMonitor.monitor_loop')
        if not self.poller:
            raise RuntimeError("Monitor not initialised")

        iteration = 0
        while True:
            iteration += 1
            logger.info("\n%s", '=' * 60)
            logger.info("🔄 Checking availability (iteration %s)", iteration)

            try:
                snapshot = await self.poller.poll()
                self.last_snapshot = snapshot
                await self._log_snapshot(snapshot)
                await self.save_state()
            except Exception as exc:  # pragma: no cover - defensive logging
                logger.error("Error in monitoring loop: %s", exc, exc_info=True)

            logger.info("\n⏳ Next check in %s seconds...", self.refresh_interval)
            await asyncio.sleep(self.refresh_interval)

    # ------------------------------------------------------------------
    # Snapshot logging & change handling
    # ------------------------------------------------------------------
    async def _log_snapshot(self, snapshot: PollSnapshot) -> None:
        for court in sorted(snapshot.results.keys()):
            data = snapshot.results[court]
            if isinstance(data, dict) and "error" in data:
                logger.error("Court %s: ❌ %s", court, data['error'])
                continue

            total_slots = sum(len(times) for times in data.values()) if isinstance(data, dict) else 0
            all_times = sorted({time for times in data.values() for time in times}) if isinstance(data, dict) else []
            change = snapshot.changes.get(court)
            emoji = "🆕" if change else "✅"
            logger.info(
                "Court %s: %s %s slots - %s",
                court,
                emoji,
                total_slots,
                ', '.join(all_times),
            )

            if change:
                description = self.format_availability_change(change)
                logger.warning("  └─ Changes detected: %s", description)
                await self._record_change(court, change, snapshot)

        total_slots_all = sum(
            sum(len(times) for times in data.values())
            for data in snapshot.results.values()
            if isinstance(data, dict) and "error" not in data
        )
        logger.info("\n📊 Total slots across all courts: %s", total_slots_all)

        for court, data in snapshot.results.items():
            if isinstance(data, dict) and "error" not in data:
                slot_count = sum(len(times) for times in data.values())
                if slot_count > 5:
                    logger.warning("⚠️  Court %s has HIGH availability (%s slots)!", court, slot_count)

    async def _record_change(self, court: int, change: AvailabilityChange, snapshot: PollSnapshot) -> None:
        screenshot_path = await self.take_court_screenshot(court)
        previous = snapshot.previous.get(court, {})
        current = snapshot.results.get(court, {})

        self.change_history.append({
            'timestamp': datetime.now().isoformat(),
            'court': court,
            'change': {
                'added': change.added,
                'removed': change.removed,
                'error': change.error,
            },
            'previous': previous,
            'current': current,
            'screenshot': str(screenshot_path) if screenshot_path else None,
            'description': self.format_availability_change(change),
        })

    # ------------------------------------------------------------------
    # Reporting helpers
    # ------------------------------------------------------------------
    async def take_court_screenshot(self, court_num: int) -> Optional[Path]:
        t('monitoring.realtime_availability_monitor.RealtimeAvailabilityMonitor.take_court_screenshot')
        if not self.browser or not self.session_dir:
            return None
        try:
            if not self.monitoring_page:
                self.monitoring_page = await self.browser.new_page()

            court_url = COURT_CONFIG[court_num]["direct_url"]
            await self.monitoring_page.goto(court_url, wait_until='domcontentloaded')
            await asyncio.sleep(2)

            timestamp = datetime.now().strftime("%H%M%S")
            screenshot_path = self.session_dir / f"court_{court_num}_{timestamp}.png"
            await self.monitoring_page.screenshot(path=str(screenshot_path))
            return screenshot_path
        except Exception as exc:  # pragma: no cover - best effort logging
            logger.error("Failed to screenshot court %s: %s", court_num, exc)
            return None

    def format_availability_change(self, change: AvailabilityChange) -> str:
        t('monitoring.realtime_availability_monitor.RealtimeAvailabilityMonitor.format_availability_change')
        parts: List[str] = []
        for date_str, slots in sorted(change.added.items()):
            if slots:
                parts.append(f"➕ {date_str}: {', '.join(slots)}")
        for date_str, slots in sorted(change.removed.items()):
            if slots:
                parts.append(f"➖ {date_str}: {', '.join(slots)}")
        if change.error:
            parts.append(f"⚠️ {change.error}")
        return " | ".join(parts) if parts else "No changes"

    async def save_state(self) -> None:
        t('monitoring.realtime_availability_monitor.RealtimeAvailabilityMonitor.save_state')
        if not self.session_dir:
            return
        snapshot = self.last_snapshot
        state = {
            'last_update': datetime.now().isoformat(),
            'current_availability': snapshot.results if snapshot else {},
            'change_history': self.change_history[-50:],
        }
        state_file = self.session_dir / 'monitor_state.json'
        state_file.write_text(json.dumps(state, indent=2), encoding='utf-8')

    async def create_final_report(self) -> None:
        t('monitoring.realtime_availability_monitor.RealtimeAvailabilityMonitor.create_final_report')
        if not self.session_dir:
            return

        final_results = self.last_snapshot.results if self.last_snapshot else {}
        report = {
            'session_start': self.change_history[0]['timestamp'] if self.change_history else None,
            'session_end': datetime.now().isoformat(),
            'total_changes': len(self.change_history),
            'final_availability': final_results,
            'change_summary': self._summarize_changes(),
        }

        report_path = self.session_dir / 'final_report.json'
        report_path.write_text(json.dumps(report, indent=2), encoding='utf-8')

        md_report = self._create_markdown_report(report)
        (self.session_dir / 'session_summary.md').write_text(md_report, encoding='utf-8')
        logger.info("\n📄 Final report saved to: %s", self.session_dir)

    def _summarize_changes(self) -> Dict[int, Dict[str, int]]:
        t('monitoring.realtime_availability_monitor.RealtimeAvailabilityMonitor._summarize_changes')
        summary: Dict[int, Dict[str, int]] = {}
        for entry in self.change_history:
            court = entry['court']
            summary.setdefault(court, {'total_changes': 0, 'slots_added': 0, 'slots_removed': 0})
            summary[court]['total_changes'] += 1

            change_data = entry.get('change', {})
            for slots in change_data.get('added', {}).values():
                summary[court]['slots_added'] += len(slots)
            for slots in change_data.get('removed', {}).values():
                summary[court]['slots_removed'] += len(slots)
        return summary

    def _create_markdown_report(self, report: Dict[str, object]) -> str:
        t('monitoring.realtime_availability_monitor.RealtimeAvailabilityMonitor._create_markdown_report')
        lines = [
            "# LVBOT Real-time Monitoring Session Report",
            f"\n**Session Duration**: {report['session_start']} to {report['session_end']}",
            f"\n**Total Changes Detected**: {report['total_changes']}",
            "\n## Final Availability\n",
        ]

        final_availability: Dict[int, Dict[str, List[str]]] = report['final_availability']  # type: ignore[assignment]
        for court_num in sorted(final_availability.keys()):
            data = final_availability[court_num]
            if isinstance(data, dict) and "error" not in data:
                total_slots = sum(len(times) for times in data.values())
                lines.append(f"- **Court {court_num}**: {total_slots} slots")
                for date_str, times in sorted(data.items()):
                    if times:
                        lines.append(f"  - {date_str}: {', '.join(sorted(times))}")

        lines.append("\n## Change Summary by Court\n")
        change_summary: Dict[int, Dict[str, int]] = report['change_summary']  # type: ignore[assignment]
        for court_num, stats in sorted(change_summary.items()):
            lines.append(f"\n### Court {court_num}")
            lines.append(f"- Total changes: {stats['total_changes']}")
            lines.append(f"- Slots added: {stats['slots_added']}")
            lines.append(f"- Slots removed: {stats['slots_removed']}")

        return '\n'.join(lines)

    # ------------------------------------------------------------------
    # Public runner
    # ------------------------------------------------------------------
    async def run(self, duration_minutes: Optional[int] = None) -> None:
        t('monitoring.realtime_availability_monitor.RealtimeAvailabilityMonitor.run')
        await self.initialize()
        try:
            if duration_minutes:
                logger.info("🚀 Starting monitor for %s minutes", duration_minutes)
                await asyncio.wait_for(self.monitor_loop(), timeout=duration_minutes * 60)
            else:
                logger.info("🚀 Starting monitor (press Ctrl+C to stop)")
                await self.monitor_loop()
        except asyncio.TimeoutError:
            logger.info("⏱️  Monitoring duration completed")
        except KeyboardInterrupt:
            logger.info("\n⛔ Monitor stopped by user")
        finally:
            await self.create_final_report()
            await self.cleanup()


async def main():
    t('monitoring.realtime_availability_monitor.main')
    monitor = RealtimeAvailabilityMonitor()
    await monitor.run()


if __name__ == '__main__':
    asyncio.run(main())
