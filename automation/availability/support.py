"""Compatibility helpers for availability extraction (legacy interface)."""

from __future__ import annotations

from datetime import date, datetime
from typing import Dict, List, Optional

from playwright.async_api import Frame

from tracking import t

from automation.availability.api import fetch_available_slots
from automation.availability.day_detection import get_available_days
from automation.availability.dom_extraction import extract_page_text_content, extract_time_buttons
from automation.availability.time_grouping import group_times_by_order_logic
from automation.availability.time_utils import convert_day_labels_to_dates, filter_future_times_for_today
from automation.availability.datetime_helpers import DateTimeHelpers

__all__ = [
    "DayDetector",
    "TimeOrderExtractor",
    "AcuityTimeParser",
    "DateTimeHelpers",
    "fetch_available_slots",
]


class DayDetector:
    """Legacy day detector facade."""

    async def extract_page_text_content(self, frame: Frame) -> str:
        t('automation.availability.support.DayDetector.extract_page_text_content')
        return await extract_page_text_content(frame)

    def get_available_days(self, text_content: str) -> List[str]:
        t('automation.availability.support.DayDetector.get_available_days')
        return get_available_days(text_content)


class TimeOrderExtractor:
    """Legacy time grouping facade."""

    async def extract_raw_time_buttons(self, frame: Frame) -> List[Dict[str, str]]:
        t('automation.availability.support.TimeOrderExtractor.extract_raw_time_buttons')
        return await extract_time_buttons(frame)

    def group_times_by_order_logic(
        self,
        time_buttons: List[Dict[str, str]],
        available_days: List[str],
    ) -> Dict[str, List[str]]:
        t('automation.availability.support.TimeOrderExtractor.group_times_by_order_logic')
        return group_times_by_order_logic(time_buttons, available_days)


class AcuityTimeParser:
    """Legacy parser using the new helper modules under the hood."""

    def __init__(self, day_detector: Optional[DayDetector] = None, time_extractor: Optional[TimeOrderExtractor] = None) -> None:
        t('automation.availability.support.AcuityTimeParser.__init__')
        self.day_detector = day_detector or DayDetector()
        self.time_extractor = time_extractor or TimeOrderExtractor()

    async def extract_times_by_day(
        self,
        frame: Frame,
        reference_date: Optional[date] = None,
        current_time: Optional[datetime] = None,
    ) -> Dict[str, List[str]]:
        t('automation.availability.support.AcuityTimeParser.extract_times_by_day')
        text_content = await self.day_detector.extract_page_text_content(frame)
        available_days = self.day_detector.get_available_days(text_content)
        if not available_days:
            return {}

        time_buttons = await self.time_extractor.extract_raw_time_buttons(frame)
        grouped = self.time_extractor.group_times_by_order_logic(time_buttons, available_days)
        dated = convert_day_labels_to_dates(grouped, reference_date=reference_date)

        if not dated:
            return {}

        today_key = (reference_date or date.today()).strftime("%Y-%m-%d")
        if today_key in dated:
            dated[today_key] = filter_future_times_for_today(
                dated[today_key], current_time=current_time
            )

        return dated
