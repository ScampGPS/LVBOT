"""DOM extraction helpers for availability pages."""

from __future__ import annotations

from typing import Any, Dict, List

from playwright.async_api import Frame

from tracking import t


async def extract_page_text_content(frame: Frame) -> str:
    """Return the text content of the frame's body."""

    t('automation.availability.dom_extraction.extract_page_text_content')
    try:
        text_content = await frame.evaluate("() => document.body.textContent || ''")
        return text_content.strip()
    except Exception:  # pragma: no cover - defensive guard
        return ""


async def extract_time_buttons(frame: Frame) -> List[Dict[str, Any]]:
    """Return time button metadata from the Acuity DOM."""

    t('automation.availability.dom_extraction.extract_time_buttons')
    try:
        return await frame.evaluate(
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
        ) or []
    except Exception:  # pragma: no cover - defensive guard
        return []
