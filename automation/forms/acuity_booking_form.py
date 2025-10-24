"""Thin facade around `AcuityFormService` for legacy callers."""

from __future__ import annotations
from tracking import t

import asyncio
import logging
from typing import Dict, List, Tuple

from playwright.async_api import Page

from automation.forms.actions import AcuityFormService

DEFAULT_LOGGER = logging.getLogger(__name__)
_VALIDATION_DELAY_SECONDS = 2.0


class AcuityBookingForm:
    """Facade that delegates to :class:`AcuityFormService`."""

    def __init__(
        self,
        use_javascript: bool = True,
        logger: logging.Logger | None = None,
        *,
        enable_tracing: bool = True,
        service: AcuityFormService | None = None,
    ) -> None:
        t('automation.forms.acuity_booking_form.AcuityBookingForm.__init__')
        base_logger = logger or DEFAULT_LOGGER
        self.service = service or AcuityFormService(
            logger=base_logger,
            use_javascript=use_javascript,
            enable_tracing=enable_tracing,
        )
        self.logger = self.service.logger

    async def fill_booking_form(self, page: Page, user_data: Dict[str, str]) -> Tuple[bool, str]:
        t('automation.forms.acuity_booking_form.AcuityBookingForm.fill_booking_form')
        return await self.service.fill_and_submit(page, user_data)

    async def fill_form(
        self,
        page: Page,
        user_info: Dict[str, str],
        *,
        validate: bool = True,
    ) -> bool:
        t('automation.forms.acuity_booking_form.AcuityBookingForm.fill_form')

        mapped = self.service.map_user_info(user_info)
        filled_count = await self.service.fill_form(page, mapped)

        if not validate:
            return filled_count > 0

        await asyncio.sleep(_VALIDATION_DELAY_SECONDS)
        has_errors, errors = await self.service.check_validation(page)
        if has_errors:
            self.logger.error("❌ Form validation failed after filling")
            for error in errors:
                self.logger.error("Form error: %s", error)
            return False

        self.logger.info("✅ Successfully filled %s/%s fields", filled_count, len(mapped))
        return filled_count > 0

    async def check_form_validation_errors(self, page: Page) -> Tuple[bool, List[str]]:
        t('automation.forms.acuity_booking_form.AcuityBookingForm.check_form_validation_errors')
        has_errors, errors = await self.service.check_validation(page)
        return has_errors, list(errors)

    async def submit(self, page: Page) -> bool:
        t('automation.forms.acuity_booking_form.AcuityBookingForm.submit')
        return await self.service.submit(page)

    async def _submit_form_simple(self, page: Page) -> bool:
        t('automation.forms.acuity_booking_form.AcuityBookingForm._submit_form_simple')
        return await self.submit(page)

    async def check_booking_success(self, page: Page) -> Tuple[bool, str]:
        t('automation.forms.acuity_booking_form.AcuityBookingForm.check_booking_success')
        return await self.service.check_success(page)


def _build_form(
    *,
    logger: logging.Logger | None = None,
    use_javascript: bool = True,
    enable_tracing: bool = True,
) -> AcuityBookingForm:
    return AcuityBookingForm(
        use_javascript=use_javascript,
        logger=logger,
        enable_tracing=enable_tracing,
    )


async def _invoke_form_method(
    method_name: str,
    page: Page,
    *,
    logger: logging.Logger | None = None,
    use_javascript: bool = True,
    enable_tracing: bool = True,
    **kwargs,
):
    form = _build_form(
        logger=logger,
        use_javascript=use_javascript,
        enable_tracing=enable_tracing,
    )
    method = getattr(form, method_name)
    return await method(page, **kwargs)


def _make_simple_form_proxy(
    proxy_name: str,
    method_name: str,
    tracking_id: str,
    doc: str,
):
    async def _call(
        page: Page,
        *,
        logger: logging.Logger | None = None,
        use_javascript: bool = True,
        enable_tracing: bool = True,
    ):
        t(tracking_id)
        return await _invoke_form_method(
            method_name,
            page,
            logger=logger,
            use_javascript=use_javascript,
            enable_tracing=enable_tracing,
        )

    _call.__name__ = proxy_name
    _call.__doc__ = doc
    return _call


check_form_validation_errors = _make_simple_form_proxy(
    "check_form_validation_errors",
    "check_form_validation_errors",
    "automation.forms.acuity_booking_form.check_form_validation_errors",
    "Proxy helper to access validation errors.",
)

submit_form = _make_simple_form_proxy(
    "submit_form",
    "submit",
    "automation.forms.acuity_booking_form.submit_form",
    "Submit the booking form using the shared service.",
)

check_booking_success = _make_simple_form_proxy(
    "check_booking_success",
    "check_booking_success",
    "automation.forms.acuity_booking_form.check_booking_success",
    "Check whether the booking was successful after submission.",
)


async def fill_booking_form(
    page: Page,
    user_data: Dict[str, str],
    *,
    use_javascript: bool = True,
    logger: logging.Logger | None = None,
    enable_tracing: bool = True,
) -> Tuple[bool, str]:
    """Fill and submit the Acuity booking form with the provided user data."""

    t('automation.forms.acuity_booking_form.fill_booking_form')
    return await _invoke_form_method(
        "fill_booking_form",
        page,
        logger=logger,
        use_javascript=use_javascript,
        enable_tracing=enable_tracing,
        user_data=user_data,
    )


async def fill_form(
    page: Page,
    user_info: Dict[str, str],
    *,
    use_javascript: bool = True,
    wait_for_navigation: bool = True,  # retained for compatibility
    logger: logging.Logger | None = None,
    enable_tracing: bool = True,
) -> bool:
    """Fill the form without submission for external callers."""

    _ = wait_for_navigation  # compatibility no-op
    t('automation.forms.acuity_booking_form.fill_form')
    return await _invoke_form_method(
        "fill_form",
        page,
        logger=logger,
        use_javascript=use_javascript,
        enable_tracing=enable_tracing,
        user_info=user_info,
    )


__all__ = [
    'AcuityBookingForm',
    'check_form_validation_errors',
    'submit_form',
    'check_booking_success',
    'fill_booking_form',
    'fill_form',
]
