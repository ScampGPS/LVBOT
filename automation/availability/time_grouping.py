"""Grouping helpers for availability times."""

from __future__ import annotations

from typing import Dict, List

from tracking import t


def group_times_by_order_logic(
    time_buttons: List[Dict[str, str]],
    available_days: List[str],
) -> Dict[str, List[str]]:
    """Group time strings by day labels based on DOM order."""

    t('automation.availability.time_grouping.group_times_by_order_logic')

    if not time_buttons or not available_days:
        return {}

    grouped: Dict[str, List[str]] = {day: [] for day in available_days}
    day_keys = list(grouped.keys())

    current_day_index = 0
    previous_hour = -1

    for button in time_buttons:
        time_str = button.get("time")
        if not time_str:
            continue

        current_hour = _time_to_hour(time_str)

        if current_hour <= previous_hour and current_day_index < len(day_keys) - 1:
            current_day_index += 1

        grouped[day_keys[current_day_index]].append(time_str)
        previous_hour = current_hour

    return grouped


def _time_to_hour(time_str: str) -> int:
    t('automation.availability.time_grouping._time_to_hour')
    try:
        return int(time_str.split(":")[0])
    except (ValueError, IndexError):
        return 0
