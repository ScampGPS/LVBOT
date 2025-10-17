"""Date/time helper utilities for availability processing."""

from __future__ import annotations

from datetime import date, datetime, timedelta
from typing import List, Optional, Tuple

import pytz

from tracking import t


class DateTimeHelpers:
    """Utility methods for timezone-aware date parsing and formatting."""

    DEFAULT_TZ = "America/Guatemala"

    @staticmethod
    def parse_slot_date(value: str, timezone_str: str = DEFAULT_TZ) -> Optional[datetime]:
        t('automation.availability.datetime_helpers.DateTimeHelpers.parse_slot_date')
        try:
            parsed = datetime.strptime(value, "%Y-%m-%d")
        except ValueError:
            return None
        return pytz.timezone(timezone_str).localize(parsed)

    @staticmethod
    def _parse_date_with_formats(value: str) -> Optional[datetime]:
        t('automation.availability.datetime_helpers.DateTimeHelpers._parse_date_with_formats')
        if not value:
            return None

        formats = ("%Y-%m-%d", "%Y/%m/%d", "%d/%m/%Y", "%m/%d/%Y")
        for fmt in formats:
            try:
                return datetime.strptime(value, fmt)
            except ValueError:
                continue
        return None

    @classmethod
    def parse_reservation_datetime(
        cls, date_str: str, time_str: str, timezone_str: str = DEFAULT_TZ
    ) -> Optional[datetime]:
        t('automation.availability.datetime_helpers.DateTimeHelpers.parse_reservation_datetime')
        date_obj = cls._parse_date_with_formats(date_str)
        if not date_obj or ":" not in time_str:
            return None

        hour, minute = map(int, time_str.split(":"))
        base = datetime.combine(date_obj.date(), datetime.min.time())
        localized = base.replace(hour=hour, minute=minute)
        return pytz.timezone(timezone_str).localize(localized)

    @classmethod
    def parse_callback_date(cls, callback_data: str) -> Optional[date]:
        t('automation.availability.datetime_helpers.DateTimeHelpers.parse_callback_date')
        if not callback_data or not callback_data.startswith("date_"):
            return None
        try:
            return datetime.strptime(callback_data[5:], "%Y-%m-%d").date()
        except ValueError:
            return None

    @classmethod
    def parse_date_string(
        cls, value: str, timezone_str: str = DEFAULT_TZ
    ) -> Optional[datetime]:
        t('automation.availability.datetime_helpers.DateTimeHelpers.parse_date_string')
        parsed = cls._parse_date_with_formats(value)
        if not parsed:
            return None
        return pytz.timezone(timezone_str).localize(parsed)

    @classmethod
    def get_day_label(cls, value: date, timezone_str: str = DEFAULT_TZ) -> str:
        t('automation.availability.datetime_helpers.DateTimeHelpers.get_day_label')
        tz = pytz.timezone(timezone_str)
        today = datetime.now(tz).date()
        target_date = value if isinstance(value, date) else value.date()
        delta = (target_date - today).days

        if delta == 0:
            return "Today"
        if delta == 1:
            return "Tomorrow"
        if delta == 2:
            return "Day After Tomorrow"
        if 0 < delta <= 6:
            return target_date.strftime("%A")
        return target_date.strftime("%B %d")

    @staticmethod
    def get_available_slots_for_date(target: datetime, config) -> List[str]:
        t('automation.availability.datetime_helpers.DateTimeHelpers.get_available_slots_for_date')
        weekday = target.weekday()
        if weekday in {5, 6}:
            return getattr(config, "weekend_times", [])
        return getattr(config, "available_times", [])

    @staticmethod
    def format_duration(seconds: float) -> str:
        t('automation.availability.datetime_helpers.DateTimeHelpers.format_duration')
        if seconds < 60:
            return f"{seconds:.1f} seconds"
        if seconds < 3600:
            return f"{seconds / 60:.1f} minutes"
        hours = int(seconds // 3600)
        minutes = int((seconds % 3600) // 60)
        return f"{hours}h {minutes}m"

    @classmethod
    def is_past_time(cls, target_date: datetime, time_str: str) -> bool:
        t('automation.availability.datetime_helpers.DateTimeHelpers.is_past_time')
        target = cls.parse_reservation_datetime(
            target_date.strftime("%Y-%m-%d"), time_str
        )
        if not target:
            return True
        tz = pytz.timezone(cls.DEFAULT_TZ)
        return target < datetime.now(tz)

    @classmethod
    def get_next_valid_booking_date(
        cls, timezone_str: str = DEFAULT_TZ, booking_window: int = 48
    ) -> datetime:
        t('automation.availability.datetime_helpers.DateTimeHelpers.get_next_valid_booking_date')
        tz = pytz.timezone(timezone_str)
        return datetime.now(tz) + timedelta(hours=1)

    @staticmethod
    def format_countdown(target: datetime, reference: Optional[datetime] = None) -> str:
        t('automation.availability.datetime_helpers.DateTimeHelpers.format_countdown')
        ref = reference or datetime.now(target.tzinfo)
        diff = target - ref
        if diff.total_seconds() < 0:
            return "Passed"

        days = diff.days
        hours = diff.seconds // 3600
        minutes = (diff.seconds % 3600) // 60

        parts: List[str] = []
        if days:
            parts.append(f"{days}d")
        if hours:
            parts.append(f"{hours}h")
        if minutes or not parts:
            parts.append(f"{minutes}m")
        return " ".join(parts)

    @staticmethod
    def get_week_range(value: datetime) -> Tuple[datetime, datetime]:
        t('automation.availability.datetime_helpers.DateTimeHelpers.get_week_range')
        start = value - timedelta(days=value.weekday())
        end = start + timedelta(days=6)
        return start, end
