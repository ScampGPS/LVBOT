"""Shared helpers for booking flow executions."""

from __future__ import annotations
from tracking import t

import logging
import time
from typing import Dict, Optional

from playwright.async_api import Page

from automation.executors.core import ExecutionResult


def safe_sleep(seconds: float) -> None:
    """Sleep helper that clamps to non-negative durations."""
    t('automation.executors.flows.helpers.safe_sleep')
    if seconds > 0:
        time.sleep(seconds)


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
) -> ExecutionResult:
    """Build a booking execution result by inspecting page confirmation text."""
    t('automation.executors.flows.helpers.confirmation_result')
    confirmation_text = await page.text_content("body")
    if confirmation_text and "confirm" in confirmation_text.lower():
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

    return ExecutionResult(
        success=False,
        error_message=failure_message,
        court_number=court_number,
    )


__all__ = ["safe_sleep", "confirmation_result"]
