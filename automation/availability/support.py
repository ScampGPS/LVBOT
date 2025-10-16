"""Consolidated helpers for availability extraction and date utilities."""

from __future__ import annotations
from utils.tracking import t

import logging
from datetime import date, datetime, timedelta
from typing import Dict, List, Optional, Tuple

import pytz
from playwright.async_api import Frame

logger = logging.getLogger(__name__)


class DayDetector:
    """Detect available day labels from Acuity pages."""

    DAY_PATTERNS = {
        "hoy": ["hoy"],
        "mañana": ["mañana", "manana"],
        "esta semana": ["esta semana", "estasemana"],
        "la próxima semana": ["la próxima semana", "próxima semana"],
    }

    @staticmethod
    async def extract_page_text_content(frame: Frame) -> str:
        t('automation.availability.support.DayDetector.extract_page_text_content')
        try:
            text_content = await frame.evaluate("() => document.body.textContent || ''")
            return text_content.strip()
        except Exception as exc:  # pragma: no cover - defensive guard
            logger.warning("Failed to extract page text content: %s", exc)
            return ""

    @classmethod
    def get_available_days(cls, text_content: str) -> List[str]:
        t('automation.availability.support.DayDetector.get_available_days')
        if not text_content:
            return []

        text_lower = text_content.lower()
        available_days: List[str] = []

        for day_key, patterns in cls.DAY_PATTERNS.items():
            if any(pattern in text_lower for pattern in patterns):
                available_days.append(day_key)

        return available_days


class TimeOrderExtractor:
    """Extract and group Acuity time buttons based on DOM order."""

    async def extract_raw_time_buttons(self, frame: Frame) -> List[Dict[str, str]]:
        t('automation.availability.support.TimeOrderExtractor.extract_raw_time_buttons')
        try:
            time_buttons = await frame.evaluate(
                r"""() => {
                    const buttons = document.querySelectorAll('button.time-selection');
                    const results = [];

                    buttons.forEach((button, index) => {
                        const timeText = button.textContent?.trim();
                        if (timeText && /^\d{1,2}:\d{2}$/.test(timeText)) {
                            results.push({ time: timeText, order: index });
                        }
                    });

                    return results;
                }
                """
            )
            return time_buttons or []
        except Exception as exc:  # pragma: no cover - defensive guard
            logger.error("Failed to extract time buttons: %s", exc)
            return []

    def group_times_by_order_logic(
        self, time_buttons: List[Dict[str, str]], available_days: List[str]
    ) -> Dict[str, List[str]]:
        t('automation.availability.support.TimeOrderExtractor.group_times_by_order_logic')
        if not time_buttons or not available_days:
            return {}

        grouped: Dict[str, List[str]] = {day: [] for day in available_days}
        day_keys = list(grouped.keys())

        current_day_index = 0
        previous_hour = -1

        for button in time_buttons:
            time_str = button["time"]
            current_hour = self._time_to_hour(time_str)

            if current_hour <= previous_hour and current_day_index < len(day_keys) - 1:
                current_day_index += 1

            grouped[day_keys[current_day_index]].append(time_str)
            previous_hour = current_hour

        return grouped

    @staticmethod
    def _time_to_hour(time_str: str) -> int:
        t('automation.availability.support.TimeOrderExtractor._time_to_hour')
        try:
            return int(time_str.split(":")[0])
        except (ValueError, IndexError):
            logger.debug("Failed to parse hour from time string: %s", time_str)
            return 0


def convert_day_labels_to_dates(
    times_by_day: Dict[str, List[str]], reference_date: Optional[date] = None
) -> Dict[str, List[str]]:
    t('automation.availability.support.convert_day_labels_to_dates')
    reference = reference_date or date.today()
    mapped: Dict[str, List[str]] = {}

    for label, times in times_by_day.items():
        label_upper = label.upper()
        if label_upper == "HOY":
            target_date = reference
        elif label_upper == "MAÑANA":
            target_date = reference + timedelta(days=1)
        elif label_upper in {"ESTA SEMANA", "LA PRÓXIMA SEMANA"}:
            target_date = reference + timedelta(days=2)
        else:
            mapped[label] = times
            continue

        mapped[target_date.strftime("%Y-%m-%d")] = times

    return mapped


def _parse_time_string(time_str: str) -> Tuple[int, int]:
    t('automation.availability.support._parse_time_string')
    if ":" not in time_str:
        raise ValueError(f"Time string '{time_str}' missing colon separator")

    hour_str, minute_str = time_str.strip().split(":")
    hour = int(hour_str)
    minute = int(minute_str)

    if not (0 <= hour <= 23):
        raise ValueError(f"Hour {hour} out of valid range 0-23")
    if not (0 <= minute <= 59):
        raise ValueError(f"Minute {minute} out of valid range 0-59")

    return hour, minute


def filter_future_times_for_today(
    times: List[str], current_time: Optional[datetime] = None
) -> List[str]:
    t('automation.availability.support.filter_future_times_for_today')
    reference = current_time or datetime.now()
    current_hour = reference.hour
    current_minute = reference.minute

    future_times: List[str] = []

    for time_str in times:
        try:
            hour, minute = _parse_time_string(time_str)
        except ValueError as exc:
            logger.warning("Could not parse time '%s': %s. Including anyway.", time_str, exc)
            future_times.append(time_str)
            continue

        if hour > current_hour or (hour == current_hour and minute > current_minute):
            future_times.append(time_str)

    return future_times


class AcuityTimeParser:
    """High-level orchestration for Acuity time extraction."""

    def __init__(
        self,
        day_detector: Optional[DayDetector] = None,
        time_extractor: Optional[TimeOrderExtractor] = None,
    ) -> None:
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
        if not time_buttons:
            return {}

        grouped = self.time_extractor.group_times_by_order_logic(time_buttons, available_days)
        if not grouped:
            return {}

        mapped = convert_day_labels_to_dates(grouped, reference_date)
        if not mapped:
            return {}

        now = current_time or datetime.now()
        today_key = (reference_date or now.date()).strftime("%Y-%m-%d")

        filtered: Dict[str, List[str]] = {}
        for key, values in mapped.items():
            unique_values = sorted({value.strip() for value in values if value})
            if not unique_values:
                continue

            if key == today_key:
                future_times = filter_future_times_for_today(unique_values, now)
                if future_times:
                    filtered[key] = future_times
            else:
                filtered[key] = unique_values

        return filtered


class DateTimeHelpers:
    """Shared date/time utilities used across Telegram handlers and executors."""

    DEFAULT_TZ = "America/Guatemala"

    @staticmethod
    def format_date_for_display(value: datetime) -> str:
        t('automation.availability.support.DateTimeHelpers.format_date_for_display')
        return value.strftime("%A, %B %d")

    @staticmethod
    def format_time_for_display(time_str: str, use_12h: bool = True) -> str:
        t('automation.availability.support.DateTimeHelpers.format_time_for_display')
        if not use_12h:
            return time_str

        try:
            hour, minute = map(int, time_str.split(":"))
        except (ValueError, AttributeError):
            return time_str

        period = "AM" if hour < 12 else "PM"
        display_hour = hour % 12 or 12
        return f"{display_hour}:{minute:02d} {period}"

    @staticmethod
    def get_hours_until(target: datetime, reference: Optional[datetime] = None) -> float:
        t('automation.availability.support.DateTimeHelpers.get_hours_until')
        ref = reference or datetime.now(target.tzinfo)
        return (target - ref).total_seconds() / 3600

    @staticmethod
    def is_within_booking_window(target: datetime, window_hours: int = 48) -> bool:
        t('automation.availability.support.DateTimeHelpers.is_within_booking_window')
        return 0 <= DateTimeHelpers.get_hours_until(target) <= window_hours

    @staticmethod
    def get_booking_window_open_time(target: datetime, window_hours: int = 48) -> datetime:
        t('automation.availability.support.DateTimeHelpers.get_booking_window_open_time')
        return target - timedelta(hours=window_hours)

    @staticmethod
    def _parse_date_with_formats(value: str) -> Optional[datetime]:
        t('automation.availability.support.DateTimeHelpers._parse_date_with_formats')
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
        t('automation.availability.support.DateTimeHelpers.parse_reservation_datetime')
        date_obj = cls._parse_date_with_formats(date_str)
        if not date_obj or ":" not in time_str:
            return None

        hour, minute = map(int, time_str.split(":"))
        base = datetime.combine(date_obj.date(), datetime.min.time())
        localized = base.replace(hour=hour, minute=minute)
        return pytz.timezone(timezone_str).localize(localized)

    @classmethod
    def parse_callback_date(cls, callback_data: str) -> Optional[date]:
        t('automation.availability.support.DateTimeHelpers.parse_callback_date')
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
        t('automation.availability.support.DateTimeHelpers.parse_date_string')
        parsed = cls._parse_date_with_formats(value)
        if not parsed:
            return None
        return pytz.timezone(timezone_str).localize(parsed)

    @classmethod
    def get_day_label(cls, value: date, timezone_str: str = DEFAULT_TZ) -> str:
        t('automation.availability.support.DateTimeHelpers.get_day_label')
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
        t('automation.availability.support.DateTimeHelpers.get_available_slots_for_date')
        weekday = target.weekday()
        if weekday in {5, 6}:
            return getattr(config, "weekend_times", [])
        return getattr(config, "available_times", [])

    @staticmethod
    def format_duration(seconds: float) -> str:
        t('automation.availability.support.DateTimeHelpers.format_duration')
        if seconds < 60:
            return f"{seconds:.1f} seconds"
        if seconds < 3600:
            return f"{seconds / 60:.1f} minutes"
        hours = int(seconds // 3600)
        minutes = int((seconds % 3600) // 60)
        return f"{hours}h {minutes}m"

    @classmethod
    def is_past_time(cls, target_date: datetime, time_str: str) -> bool:
        t('automation.availability.support.DateTimeHelpers.is_past_time')
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
        t('automation.availability.support.DateTimeHelpers.get_next_valid_booking_date')
        tz = pytz.timezone(timezone_str)
        return datetime.now(tz) + timedelta(hours=1)

    @staticmethod
    def format_countdown(target: datetime, reference: Optional[datetime] = None) -> str:
        t('automation.availability.support.DateTimeHelpers.format_countdown')
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
        t('automation.availability.support.DateTimeHelpers.get_week_range')
        start = value - timedelta(days=value.weekday())
        end = start + timedelta(days=6)
        return start, end
