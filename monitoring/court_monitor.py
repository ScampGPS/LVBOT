"""Simplified court monitor built on the shared availability poller."""

from __future__ import annotations

import asyncio
import logging
from datetime import datetime, timedelta
from typing import Dict, Iterable, List, Optional

import pytz

from tracking import t

from automation.availability import AvailabilityChecker
from automation.browser.async_browser_pool import AsyncBrowserPool
from infrastructure.constants import WEEKDAY_COURT_HOURS, WEEKEND_COURT_HOURS
from monitoring.availability_poller import AvailabilityPoller


class CourtMonitor:
    """Polls availability for specific courts and slots."""

    def __init__(self, poll_interval: int = 5, *, logger: Optional[logging.Logger] = None) -> None:
        t('monitoring.court_monitor.CourtMonitor.__init__')
        self.poll_interval = poll_interval
        self.logger = logger or logging.getLogger('CourtMonitor')
        self.timezone = pytz.timezone('America/Guatemala')

        self.browser_pool: Optional[AsyncBrowserPool] = None
        self.checker: Optional[AvailabilityChecker] = None
        self.poller: Optional[AvailabilityPoller] = None
        self._started = False

    async def start(self) -> None:
        if self._started:
            return

        self.browser_pool = AsyncBrowserPool()
        await self.browser_pool.start()
        self.checker = AvailabilityChecker(self.browser_pool)
        self.poller = AvailabilityPoller(self.checker.check_availability, logger=self.logger)
        self._started = True

    async def stop(self) -> None:
        if not self._started:
            return

        if self.browser_pool:
            await self.browser_pool.stop()
        self.browser_pool = None
        self.checker = None
        self.poller = None
        self._started = False

    async def monitor_slot(
        self,
        court_number: int,
        target_datetime: datetime,
        *,
        timeout_seconds: int = 120,
    ) -> Dict[str, object]:
        """Poll for a specific court/time until timeout or availability."""

        await self.start()
        if not self.poller:
            raise RuntimeError("Monitor not initialised")

        target_local = self._to_timezone(target_datetime)
        date_key = target_local.strftime('%Y-%m-%d')
        slot_time = target_local.strftime('%H:%M')
        deadline = datetime.now(self.timezone) + timedelta(seconds=timeout_seconds)

        self.logger.info(
            "Monitoring court %s for %s at %s",
            court_number,
            date_key,
            slot_time,
        )

        while datetime.now(self.timezone) < deadline:
            snapshot = await self.poller.poll()
            court_data = snapshot.results.get(court_number, {})
            if isinstance(court_data, dict) and "error" not in court_data:
                if slot_time in set(court_data.get(date_key, [])):
                    self.logger.info(
                        "Slot available for court %s on %s at %s",
                        court_number,
                        date_key,
                        slot_time,
                    )
                    return {
                        'status': 'available',
                        'court': court_number,
                        'date': date_key,
                        'time': slot_time,
                        'snapshot_time': snapshot.timestamp.isoformat(),
                    }
            await asyncio.sleep(self.poll_interval)

        self.logger.info(
            "Timed out waiting for court %s on %s at %s",
            court_number,
            date_key,
            slot_time,
        )
        return {'status': 'timeout', 'court': court_number, 'date': date_key, 'time': slot_time}

    async def monitor_all_day(
        self,
        court_numbers: Iterable[int],
        *,
        advance_seconds: int = 30,
    ) -> None:
        """Continuously monitor upcoming slots 48 hours in advance."""

        await self.start()
        try:
            while True:
                now = datetime.now(self.timezone)
                target_play_date = now + timedelta(hours=48)
                slots = self.get_slots_for_date(target_play_date)

                next_slot = self._next_slot(slots, target_play_date, advance_seconds)
                if not next_slot:
                    self.logger.info("No upcoming slots in range; sleeping 30 minutes")
                    await asyncio.sleep(1800)
                    continue

                slot_time, start_monitor_at, playing_datetime = next_slot
                wait_seconds = max((start_monitor_at - now).total_seconds(), 0)
                if wait_seconds > 0:
                    self.logger.info(
                        "Next slot %s at %s. Waiting %.0f seconds before polling",
                        slot_time,
                        playing_datetime,
                        wait_seconds,
                    )
                    await asyncio.sleep(wait_seconds)

                for court in court_numbers:
                    await self.monitor_slot(
                        court,
                        playing_datetime,
                        timeout_seconds=advance_seconds + 120,
                    )
        finally:
            await self.stop()

    # ------------------------------------------------------------------
    # Helpers
    # ------------------------------------------------------------------
    def get_slots_for_date(self, candidate: datetime) -> List[str]:
        t('monitoring.court_monitor.CourtMonitor.get_slots_for_date')
        return WEEKEND_COURT_HOURS if candidate.weekday() >= 5 else WEEKDAY_COURT_HOURS

    def _next_slot(
        self,
        slots: List[str],
        play_date: datetime,
        advance_seconds: int,
    ) -> Optional[tuple[str, datetime, datetime]]:
        now = datetime.now(self.timezone)
        for slot in slots:
            hour, minute = map(int, slot.split(':'))
            playing_datetime = play_date.replace(hour=hour, minute=minute, second=0, microsecond=0)
            monitor_start = playing_datetime - timedelta(hours=48, seconds=advance_seconds)
            if monitor_start > now:
                return slot, monitor_start, playing_datetime
        return None

    def _to_timezone(self, dt: datetime) -> datetime:
        if dt.tzinfo is None:
            return self.timezone.localize(dt)
        return dt.astimezone(self.timezone)

    async def __aenter__(self):
        await self.start()
        return self

    async def __aexit__(self, exc_type, exc, tb):
        await self.stop()
