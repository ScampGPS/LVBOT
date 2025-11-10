from tracking import t
from automation.availability.time_grouping import group_times_by_order_logic


def test_group_times_respects_order_wrap():
    t('tests.unit.test_time_grouping.test_group_times_respects_order_wrap')
    buttons = [
        {"time": "08:00", "order": 0},
        {"time": "09:00", "order": 1},
        {"time": "07:30", "order": 2},
    ]
    grouped = group_times_by_order_logic(buttons, ["hoy", "mañana"])
    assert grouped["hoy"] == ["08:00", "09:00"]
    assert grouped["mañana"] == ["07:30"]


def test_group_times_handles_missing_data():
    t('tests.unit.test_time_grouping.test_group_times_handles_missing_data')
    assert group_times_by_order_logic([], ["hoy"]) == {}
