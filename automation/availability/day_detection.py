"""Day detection helpers for availability extraction."""

from __future__ import annotations

from typing import List

from tracking import t

DAY_PATTERNS = {
    "hoy": ["hoy"],
    "mañana": ["mañana", "manana"],
    "esta semana": ["esta semana", "estasemana"],
    "la próxima semana": ["la próxima semana", "próxima semana"],
}


def get_available_days(text_content: str) -> List[str]:
    """Return normalized day labels detected in the page text."""

    t('automation.availability.day_detection.get_available_days')

    if not text_content:
        return []

    text_lower = text_content.lower()
    available_days: List[str] = []

    for day_key, patterns in DAY_PATTERNS.items():
        if any(pattern in text_lower for pattern in patterns):
            available_days.append(day_key)

    return available_days
