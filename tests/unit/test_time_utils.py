from tracking import t
from datetime import date, datetime

from automation.availability.time_utils import (
    convert_day_labels_to_dates,
    filter_future_times_for_today,
)


def test_convert_day_labels_to_dates_maps_known_labels():
    t('tests.unit.test_time_utils.test_convert_day_labels_to_dates_maps_known_labels')
    reference = date(2025, 1, 5)
    result = convert_day_labels_to_dates(
        {
            "hoy": ["08:00"],
            "mañana": ["09:00"],
            "2025-01-10": ["10:00"],
        },
        reference_date=reference,
    )

    assert result["2025-01-05"] == ["08:00"]
    assert result["2025-01-06"] == ["09:00"]
    assert result["2025-01-10"] == ["10:00"]


def test_filter_future_times_for_today_filters_past():
    t('tests.unit.test_time_utils.test_filter_future_times_for_today_filters_past')
    current = datetime(2025, 1, 5, 10, 30)
    times = ["09:00", "10:15", "10:45", "11:00"]

    filtered = filter_future_times_for_today(times, current_time=current)

    assert filtered == ["10:45", "11:00"]
