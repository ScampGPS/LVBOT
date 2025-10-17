"""Time parsing helpers for availability extraction."""

from __future__ import annotations

from datetime import date, datetime, timedelta
from typing import Dict, List, Optional, Tuple

from tracking import t


def convert_day_labels_to_dates(
    times_by_day: Dict[str, List[str]],
    reference_date: Optional[date] = None,
) -> Dict[str, List[str]]:
    """Convert relative day labels to ISO date strings."""

    t('automation.availability.time_utils.convert_day_labels_to_dates')

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


def filter_future_times_for_today(
    times: List[str],
    current_time: Optional[datetime] = None,
) -> List[str]:
    """Filter out times that have already passed for the current day."""

    t('automation.availability.time_utils.filter_future_times_for_today')

    reference = current_time or datetime.now()
    current_hour = reference.hour
    current_minute = reference.minute

    future_times: List[str] = []

    for time_str in times:
        try:
            hour, minute = _parse_time_string(time_str)
        except ValueError:
            future_times.append(time_str)
            continue

        if hour > current_hour or (hour == current_hour and minute > current_minute):
            future_times.append(time_str)

    return future_times


def _parse_time_string(time_str: str) -> Tuple[int, int]:
    t('automation.availability.time_utils._parse_time_string')

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
