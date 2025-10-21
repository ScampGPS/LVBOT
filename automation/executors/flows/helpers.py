"""Shared helpers for booking flow executions."""

from __future__ import annotations
from tracking import t

import logging
import time
from typing import Dict, Optional

from playwright.async_api import Page

from automation.executors.core import ExecutionResult
from datetime import datetime
from pathlib import Path


def safe_sleep(seconds: float) -> None:
    """Sleep helper that clamps to non-negative durations."""
    t('automation.executors.flows.helpers.safe_sleep')
    if seconds > 0:
        time.sleep(seconds)


_ARTIFACT_DIR = Path('logs/latest_log/booking_artifacts')


async def confirmation_result(
    page: Page,
    court_number: int,
    time_slot: str,
    user_info: Dict[str, str],
    *,
    logger: Optional[logging.Logger] = None,
    success_log: Optional[str] = None,
    failure_log: Optional[str] = None,
    failure_message: str = "Booking confirmation not detected",
    capture_on_failure: bool = True,
) -> ExecutionResult:
    """Build a booking execution result by inspecting page confirmation text."""
    t('automation.executors.flows.helpers.confirmation_result')
    confirmation_text = await page.text_content("body")
    normalized = (confirmation_text or "").lower()

    success_tokens = (
        "reserva confirmada",
        "reserva completada",
        "reserva exitosa",
        "¡gracias por reservar",
        "gracias por reservar",
    )

    if confirmation_text and any(token in normalized for token in success_tokens):
        if logger and success_log:
            logger.info(success_log, court_number)
        return ExecutionResult(
            success=True,
            court_number=court_number,
            court_reserved=court_number,
            time_reserved=time_slot,
            user_name=user_info.get("first_name"),
        )

    if logger and failure_log:
        logger.warning(failure_log, court_number)

    if capture_on_failure:
        await _capture_failure_artifacts(
            page,
            court_number=court_number,
            time_slot=time_slot,
            logger=logger,
        )

    return ExecutionResult(
        success=False,
        error_message=failure_message,
        court_number=court_number,
    )


async def _capture_failure_artifacts(
    page: Page,
    *,
    court_number: int,
    time_slot: str,
    logger: Optional[logging.Logger] = None,
) -> None:
    """Persist a screenshot and HTML snapshot when confirmation detection fails."""

    timestamp = datetime.utcnow().strftime("%Y%m%d_%H%M%S")
    slot_label = time_slot.replace(":", "-") or "unspecified"

    _ARTIFACT_DIR.mkdir(parents=True, exist_ok=True)

    screenshot_path = _ARTIFACT_DIR / f"court{court_number}_{slot_label}_{timestamp}.png"
    html_path = _ARTIFACT_DIR / f"court{court_number}_{slot_label}_{timestamp}.html"

    try:
        await page.screenshot(path=str(screenshot_path), full_page=True)
    except Exception as exc:  # pragma: no cover - best effort logging
        if logger:
            logger.debug("Failed to capture screenshot: %s", exc)

    try:
        html_content = await page.content()
        html_path.write_text(html_content or "", encoding="utf-8")
    except Exception as exc:  # pragma: no cover - best effort logging
        if logger:
            logger.debug("Failed to write HTML artifact: %s", exc)

    if logger:
        logger.warning(
            "Stored booking artifacts for court %s slot %s at %s",
            court_number,
            time_slot,
            screenshot_path,
        )


__all__ = ["safe_sleep", "confirmation_result"]
