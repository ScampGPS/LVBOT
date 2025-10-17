"""High-level helpers for interacting with the Acuity booking form."""

from __future__ import annotations

from tracking import t

import asyncio
import logging
import time
from typing import Dict, List, Tuple

from playwright.async_api import Page

from automation.forms.actions import (
    check_booking_success as actions_check_booking_success,
    check_validation_errors as actions_check_validation_errors,
    fill_booking_form as actions_fill_booking_form,
    map_user_info,
    submit_form as actions_submit_form,
    validate_required_fields,
)

DEFAULT_LOGGER = logging.getLogger(__name__)
TRACE_PATH_TEMPLATE = "/mnt/c/Documents/code/python/LVBot/debugging/form_fill_trace_{timestamp}.zip"


async def check_form_validation_errors(page: Page, *, logger: logging.Logger | None = None) -> Tuple[bool, List[str]]:
    """Proxy helper to access validation errors."""

    logger = logger or DEFAULT_LOGGER
    return await actions_check_validation_errors(page, logger=logger)


async def submit_form(page: Page, *, logger: logging.Logger | None = None) -> bool:
    """Submit the booking form using the shared actions module."""

    logger = logger or DEFAULT_LOGGER
    return await actions_submit_form(page, logger=logger)


async def check_booking_success(page: Page, *, logger: logging.Logger | None = None) -> Tuple[bool, str]:
    """Check whether the booking was successful after submission."""

    logger = logger or DEFAULT_LOGGER
    return await actions_check_booking_success(page, logger=logger)


async def fill_booking_form(
    page: Page,
    user_data: Dict[str, str],
    *,
    use_javascript: bool = True,
    wait_for_navigation: bool = True,  # retained for compatibility
    logger: logging.Logger | None = None,
) -> Tuple[bool, str]:
    """Fill and submit the Acuity booking form with the provided user data."""

    t('automation.forms.acuity_booking_form.fill_booking_form')

    logger = logger or DEFAULT_LOGGER

    missing_fields = validate_required_fields(user_data)
    if missing_fields:
        logger.error("❌ Missing required fields: %s", ', '.join(missing_fields))
        return False, f"Missing required fields: {', '.join(missing_fields)}"

    context = page.context
    trace_enabled = False

    try:
        await context.tracing.start(screenshots=True, snapshots=True, sources=True)
        trace_enabled = True
        logger.info("🎥 Started trace recording for form filling debugging")
    except Exception as trace_error:  # pragma: no cover - best effort
        logger.warning("⚠️ Could not start tracing: %s", trace_error)

    try:
        filled_count = await actions_fill_booking_form(
            page,
            user_data,
            use_javascript=use_javascript,
            logger=logger,
        )
    finally:
        if trace_enabled:
            try:
                trace_path = TRACE_PATH_TEMPLATE.format(timestamp=int(time.time()))
                await context.tracing.stop(path=trace_path)
                logger.info("💾 Saved form filling trace to: %s", trace_path)
            except Exception as trace_error:  # pragma: no cover - best effort
                logger.warning("⚠️ Could not save trace: %s", trace_error)

    if filled_count == 0:
        return False, "❌ Could not fill any form fields"

    logger.info("✅ Filled %s fields successfully", filled_count)
    await asyncio.sleep(2)

    has_errors, errors = await check_form_validation_errors(page, logger=logger)
    if has_errors:
        logger.error("❌ Form has validation errors, cannot submit:")
        for error in errors:
            logger.error("   • %s", error)
        return False, f"Form validation failed: {'; '.join(errors)}"

    submit_success = await submit_form(page, logger=logger)
    if not submit_success:
        return False, "❌ Form submission failed"

    success, message = await check_booking_success(page, logger=logger)
    if not success and 'bot_detected' in message:
        logger.warning("🚫 Bot detection triggered - sistema bloqueó uso automatizado")
        return False, "❌ Sistema detectó bot - usar navegador manual para reservar"

    return success, message


async def fill_form(
    page: Page,
    user_info: Dict[str, str],
    *,
    use_javascript: bool = True,
    logger: logging.Logger | None = None,
) -> bool:
    """Fill the form without submission for external callers."""

    t('automation.forms.acuity_booking_form.fill_form')

    logger = logger or DEFAULT_LOGGER
    user_data = map_user_info(user_info)

    filled_count = await actions_fill_booking_form(
        page,
        user_data,
        use_javascript=use_javascript,
        logger=logger,
    )

    await asyncio.sleep(2)
    has_errors, _ = await check_form_validation_errors(page, logger=logger)
    if has_errors:
        logger.error("❌ Form validation failed after filling")
        return False

    logger.info("✅ Successfully filled %s/%s fields", filled_count, len(user_data))
    return filled_count > 0


class AcuityBookingForm:
    """Compatibility wrapper around stateless booking-form helpers."""

    def __init__(self, use_javascript: bool = True, logger: logging.Logger | None = None) -> None:
        t('automation.forms.acuity_booking_form.AcuityBookingForm.__init__')
        self.use_javascript = use_javascript
        self.logger = logger or DEFAULT_LOGGER

    async def check_form_validation_errors(self, page: Page) -> Tuple[bool, List[str]]:
        return await check_form_validation_errors(page, logger=self.logger)

    async def fill_booking_form(
        self,
        page: Page,
        user_data: Dict[str, str],
        wait_for_navigation: bool = True,
    ) -> Tuple[bool, str]:
        return await fill_booking_form(
            page,
            user_data,
            use_javascript=self.use_javascript,
            wait_for_navigation=wait_for_navigation,
            logger=self.logger,
        )

    async def fill_form(self, page: Page, user_info: Dict[str, str]) -> bool:
        return await fill_form(
            page,
            user_info,
            use_javascript=self.use_javascript,
            logger=self.logger,
        )

    async def _submit_form_simple(self, page: Page) -> bool:
        return await submit_form(page, logger=self.logger)

    async def check_booking_success(self, page: Page) -> Tuple[bool, str]:
        return await check_booking_success(page, logger=self.logger)
