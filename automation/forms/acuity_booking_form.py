"""High-level helpers for interacting with the Acuity booking form."""

from __future__ import annotations

from tracking import t

import asyncio
import logging
from typing import Dict, List, Tuple

from playwright.async_api import Page

from automation.forms.actions import AcuityFormService

DEFAULT_LOGGER = logging.getLogger(__name__)


def _build_service(
    *,
    logger: logging.Logger | None = None,
    use_javascript: bool = True,
    enable_tracing: bool = True,
) -> AcuityFormService:
    return AcuityFormService(
        logger=logger or DEFAULT_LOGGER,
        use_javascript=use_javascript,
        enable_tracing=enable_tracing,
    )


async def check_form_validation_errors(page: Page, *, logger: logging.Logger | None = None) -> Tuple[bool, List[str]]:
    """Proxy helper to access validation errors."""

    t('automation.forms.acuity_booking_form.check_form_validation_errors')
    has_errors, errors = await _build_service(logger=logger).check_validation(page)
    return has_errors, list(errors)


async def submit_form(page: Page, *, logger: logging.Logger | None = None) -> bool:
    """Submit the booking form using the shared service."""

    t('automation.forms.acuity_booking_form.submit_form')
    return await _build_service(logger=logger).submit(page)


async def check_booking_success(page: Page, *, logger: logging.Logger | None = None) -> Tuple[bool, str]:
    """Check whether the booking was successful after submission."""

    t('automation.forms.acuity_booking_form.check_booking_success')
    return await _build_service(logger=logger).check_success(page)


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
    service = _build_service(logger=logger, use_javascript=use_javascript)
    return await service.fill_and_submit(page, user_data)


async def fill_form(
    page: Page,
    user_info: Dict[str, str],
    *,
    use_javascript: bool = True,
    logger: logging.Logger | None = None,
) -> bool:
    """Fill the form without submission for external callers."""

    t('automation.forms.acuity_booking_form.fill_form')

    service = _build_service(logger=logger, use_javascript=use_javascript)
    user_data = service.map_user_info(user_info)

    filled_count = await service.fill_form(page, user_data)

    await asyncio.sleep(2)
    has_errors, _ = await service.check_validation(page)
    if has_errors:
        service.logger.error("❌ Form validation failed after filling")
        return False

    service.logger.info("✅ Successfully filled %s/%s fields", filled_count, len(user_data))
    return filled_count > 0


class AcuityBookingForm:
    """Compatibility wrapper around the service-centric booking-form helpers."""

    def __init__(
        self,
        use_javascript: bool = True,
        logger: logging.Logger | None = None,
        *,
        enable_tracing: bool = True,
        service: AcuityFormService | None = None,
    ) -> None:
        t('automation.forms.acuity_booking_form.AcuityBookingForm.__init__')
        self.logger = logger or DEFAULT_LOGGER
        self.service = service or AcuityFormService(
            logger=self.logger,
            use_javascript=use_javascript,
            enable_tracing=enable_tracing,
        )

    async def check_form_validation_errors(self, page: Page) -> Tuple[bool, List[str]]:
        has_errors, errors = await self.service.check_validation(page)
        return has_errors, list(errors)

    async def fill_booking_form(
        self,
        page: Page,
        user_data: Dict[str, str],
        wait_for_navigation: bool = True,
    ) -> Tuple[bool, str]:
        return await self.service.fill_and_submit(page, user_data)

    async def fill_form(self, page: Page, user_info: Dict[str, str]) -> bool:
        mapped = self.service.map_user_info(user_info)
        filled_count = await self.service.fill_form(page, mapped)

        await asyncio.sleep(2)
        has_errors, _ = await self.service.check_validation(page)
        if has_errors:
            self.logger.error("❌ Form validation failed after filling")
            return False

        self.logger.info("✅ Successfully filled %s/%s fields", filled_count, len(mapped))
        return filled_count > 0

    async def _submit_form_simple(self, page: Page) -> bool:
        return await self.service.submit(page)

    async def check_booking_success(self, page: Page) -> Tuple[bool, str]:
        return await self.service.check_success(page)
