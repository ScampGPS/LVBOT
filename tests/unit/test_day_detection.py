from tracking import t
import pytest

from automation.availability.day_detection import get_available_days


def test_get_available_days_detects_known_labels():
    t('tests.unit.test_day_detection.test_get_available_days_detects_known_labels')
    text = "Hoy tenemos cupos disponibles y también la próxima semana."
    days = get_available_days(text)
    assert "hoy" in days
    assert "la próxima semana" in days


def test_get_available_days_handles_empty_text():
    t('tests.unit.test_day_detection.test_get_available_days_handles_empty_text')
    assert get_available_days("") == []
