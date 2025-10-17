"""Public availability API for fetching slot data."""

from __future__ import annotations

from datetime import date, datetime
from typing import Dict, List, Optional

from playwright.async_api import Page

from tracking import t

from automation.availability.day_detection import get_available_days
from automation.availability.dom_extraction import extract_page_text_content, extract_time_buttons
from automation.availability.time_grouping import group_times_by_order_logic
from automation.availability.time_utils import convert_day_labels_to_dates, filter_future_times_for_today


async def fetch_available_slots(
    page: Page,
    *,
    reference_date: Optional[date] = None,
    current_time: Optional[datetime] = None,
) -> Dict[str, List[str]]:
    """Return a mapping of ISO date strings to available time slots."""

    t('automation.availability.api.fetch_available_slots')

    frame = page.main_frame
    text_content = await extract_page_text_content(frame)
    available_days = get_available_days(text_content)
    time_buttons = await extract_time_buttons(frame)

    grouped = group_times_by_order_logic(time_buttons, available_days)
    dated = convert_day_labels_to_dates(grouped, reference_date=reference_date)

    if not dated:
        return {}

    today_key = (reference_date or date.today()).strftime("%Y-%m-%d")
    if today_key in dated:
        dated[today_key] = filter_future_times_for_today(
            dated[today_key], current_time=current_time
        )

    return dated
