"""Form action helpers for Acuity booking."""

from __future__ import annotations

import asyncio
from typing import Any, Dict, List, Mapping, Tuple

from playwright.async_api import Page

from tracking import t

from automation.forms.fields import FORM_SELECTORS, REQUIRED_FIELDS, fill_fields_javascript, fill_fields_playwright
from automation.shared.booking_contracts import BookingUser

TRACE_PATH_TEMPLATE = "/mnt/c/Documents/code/python/LVBot/debugging/form_fill_trace_{timestamp}.zip"


async def check_validation_errors(page: Page, *, logger) -> Tuple[bool, List[str]]:
    """Check the form for validation errors returned by the page."""

    t('automation.forms.actions.check_validation_errors')

    try:
        validation_result = await page.evaluate(
            """
            () => {
                const errors = [];

                const redTextElements = Array.from(document.querySelectorAll('*')).filter(el => {
                    const style = window.getComputedStyle(el);
                    const text = el.textContent.trim();
                    return (
                        style.color.includes('red') ||
                        style.color === 'rgb(255, 0, 0)' ||
                        style.color === 'rgba(255, 0, 0, 1)'
                    ) && text.includes('obligatorio');
                });

                redTextElements.forEach(el => {
                    const text = el.textContent.trim();
                    if (text && !errors.includes(text)) {
                        errors.push(text);
                    }
                });

                const requiredFields = document.querySelectorAll('input[name*="client"]');
                requiredFields.forEach(field => {
                    if (!field.value.trim()) {
                        errors.push(`${field.name} is empty`);
                    }
                });

                return {
                    hasErrors: errors.length > 0,
                    errors,
                };
            }
            """
        )

        has_errors = validation_result.get('hasErrors', True)
        errors = list(validation_result.get('errors', []))

        if has_errors:
            logger.warning("⚠️ Form validation errors detected:")
            for error in errors:
                logger.warning("   • %s", error)
        else:
            logger.info("✅ No form validation errors found")

        return has_errors, errors

    except Exception as exc:  # pragma: no cover - defensive guard
        logger.error("❌ Error checking form validation: %s", exc)
        return True, [f"Error checking validation: {exc}"]


async def submit_form(page: Page, *, logger) -> bool:
    """Submit the booking form via JavaScript."""

    t('automation.forms.actions.submit_form')

    try:
        logger.info("🚀 Submitting form with JavaScript...")

        result = await page.evaluate(
            """
            () => {
                const buttons = Array.from(document.querySelectorAll('button'));
                const confirmButton = buttons.find(btn =>
                    btn.textContent.includes('Confirmar') && btn.offsetParent !== null
                );

                if (confirmButton) {
                    confirmButton.click();
                    return { success: true, buttonText: confirmButton.textContent.trim() };
                }

                const submitButton = document.querySelector('button[type="submit"]');
                if (submitButton) {
                    submitButton.click();
                    return { success: true, buttonText: 'submit button' };
                }

                return { success: false, error: 'No submit button found' };
            }
            """
        )

        if result.get('success'):
            logger.info("✅ Form submitted using: %s", result.get('buttonText'))
            await asyncio.sleep(2)
            return True

        logger.error("❌ Could not submit form: %s", result.get('error'))
        return False

    except Exception as exc:  # pragma: no cover - defensive guard
        logger.error("❌ Error submitting form: %s", exc)
        return False


async def check_booking_success(page: Page, *, logger) -> Tuple[bool, str]:
    """Determine if the booking succeeded after submission."""

    t('automation.forms.actions.check_booking_success')

    try:
        logger.info("🔍 Checking booking success...")
        await asyncio.sleep(2)

        result = await page.evaluate(
            r"""
            () => {
                const url = window.location.href;
                const text = document.body.innerText || '';
                const textLower = text.toLowerCase();

                if (text.includes('Se detectó un uso irregular del sitio') ||
                    text.includes('uso irregular') ||
                    text.includes('Comunícate con el negocio')) {
                    return {
                        success: false,
                        error: 'bot_detected',
                        message: 'Sistema detectó uso automatizado - contactar negocio para reservar'
                    };
                }

                const errorElements = document.querySelectorAll('.error, .field-error, [class*="error"]');
                if (errorElements.length > 0) {
                    const errors = Array.from(errorElements)
                        .map(el => el.textContent.trim())
                        .filter(text => text);
                    if (errors.length > 0) {
                        return {
                            success: false,
                            error: 'validation_error',
                            message: `Errores de validación: ${errors.join(', ')}`,
                        };
                    }
                }

                const confirmMatch = url.match(/\/confirmation\/([a-zA-Z0-9]+)/);
                if (confirmMatch) {
                    const confirmationId = confirmMatch[1];
                    const nameMatch = text.match(/([A-Za-z]+),\s*¡Tu cita está confirmada!/);
                    return {
                        success: true,
                        type: 'confirmation',
                        confirmationId,
                        name: nameMatch ? nameMatch[1] : null,
                        message: 'Reserva confirmada',
                    };
                }

                if (textLower.includes('gracias') && textLower.includes('reserva')) {
                    return {
                        success: true,
                        type: 'thank_you',
                        message: 'Reserva completada',
                    };
                }

                return {
                    success: false,
                    error: 'unknown',
                    message: 'No confirmation detected',
                };
            }
            """
        )

        if result.get('success'):
            logger.info("✅ Booking success: %s", result.get('message'))
            return True, result.get('message', 'Reserva confirmada')

        error = result.get('error', 'unknown')
        message = result.get('message', 'Error desconocido')
        logger.warning("❌ Booking failed (%s): %s", error, message)
        return False, message

    except Exception as exc:  # pragma: no cover - defensive guard
        logger.error("❌ Error checking booking success: %s", exc)
        return False, f"Error checking booking success: {exc}"


async def fill_booking_form(
    page: Page,
    user_data: Dict[str, str],
    *,
    use_javascript: bool,
    logger,
) -> int:
    """Fill booking form fields using either JavaScript or Playwright."""

    t('automation.forms.actions.fill_booking_form')

    if use_javascript:
        filled_count, messages = await fill_fields_javascript(page, user_data)
        for message in messages:
            logger.info("  %s", message)
        return filled_count

    return await fill_fields_playwright(page, user_data, logger=logger)



def map_user_info(user_info: Mapping[str, Any] | BookingUser) -> Dict[str, str]:
    """Map external user info to the form field structure."""

    t('automation.forms.actions.map_user_info')

    if isinstance(user_info, BookingUser):
        source = user_info.as_executor_payload(include_tier_when_none=True)
    else:
        source = dict(user_info)

    return {
        'client.firstName': source.get('first_name', ''),
        'client.lastName': source.get('last_name', ''),
        'client.phone': source.get('phone', ''),
        'client.email': source.get('email', ''),
    }


def validate_required_fields(user_data: Dict[str, str]) -> List[str]:
    """Return missing required field names."""

    t('automation.forms.actions.validate_required_fields')
    return [field for field in REQUIRED_FIELDS if not user_data.get(field)]
