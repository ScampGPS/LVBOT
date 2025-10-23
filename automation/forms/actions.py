"""Service-centric helpers for interacting with Acuity booking forms."""

from __future__ import annotations

import asyncio
import logging
import time
from contextlib import asynccontextmanager
from typing import Any, Dict, Mapping, Tuple

from playwright.async_api import Page

from tracking import t

from automation.forms.fields import FORM_SELECTORS, REQUIRED_FIELDS
from automation.shared.booking_contracts import BookingUser

TRACE_PATH_TEMPLATE = "/mnt/c/Documents/code/python/LVBot/debugging/form_fill_trace_{timestamp}.zip"

_UserInfo = Mapping[str, Any] | BookingUser | Dict[str, Any]


class AcuityFormService:
    """Stateful service that consolidates Acuity form interactions."""

    def __init__(
        self,
        *,
        logger: logging.Logger | None = None,
        use_javascript: bool = True,
        enable_tracing: bool = True,
        trace_path_template: str = TRACE_PATH_TEMPLATE,
    ) -> None:
        t('automation.forms.actions.AcuityFormService.__init__')
        self.logger = logger or logging.getLogger(__name__)
        self.use_javascript = use_javascript
        self.enable_tracing = enable_tracing
        self.trace_path_template = trace_path_template

    # ------------------------------------------------------------------
    # Public API
    # ------------------------------------------------------------------
    def map_user_info(self, user_info: _UserInfo) -> Dict[str, str]:
        """Map incoming user info into Acuity form field keys."""

        t('automation.forms.actions.AcuityFormService.map_user_info')

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

    def validate(self, user_data: Mapping[str, str]) -> Tuple[str, ...]:
        """Return tuple of missing required fields."""

        t('automation.forms.actions.AcuityFormService.validate')
        return tuple(field for field in REQUIRED_FIELDS if not user_data.get(field))

    async def fill_form(self, page: Page, user_data: Mapping[str, str]) -> int:
        """Fill the Acuity form using the configured strategy."""

        t('automation.forms.actions.AcuityFormService.fill_form')

        if self.use_javascript:
            filled_count, messages = await self._fill_via_js(page, user_data)
            for message in messages:
                self.logger.info("  %s", message)
            return filled_count

        return await self._fill_via_playwright(page, user_data)

    async def check_validation(self, page: Page) -> Tuple[bool, Tuple[str, ...]]:
        """Inspect the page for validation errors."""

        t('automation.forms.actions.AcuityFormService.check_validation')

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
            errors = tuple(validation_result.get('errors', ()))

            if has_errors:
                self.logger.warning("⚠️ Form validation errors detected:")
                for error in errors:
                    self.logger.warning("   • %s", error)
            else:
                self.logger.info("✅ No form validation errors found")

            return has_errors, errors

        except Exception as exc:  # pragma: no cover - defensive guard
            self.logger.error("❌ Error checking form validation: %s", exc)
            return True, (f"Error checking validation: {exc}",)

    async def submit(self, page: Page) -> bool:
        """Submit the form."""

        t('automation.forms.actions.AcuityFormService.submit')

        try:
            self.logger.info("🚀 Submitting form with JavaScript...")

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
                self.logger.info("✅ Form submitted using: %s", result.get('buttonText'))
                await asyncio.sleep(2)
                return True

            self.logger.error("❌ Could not submit form: %s", result.get('error'))
            return False

        except Exception as exc:  # pragma: no cover - defensive guard
            self.logger.error("❌ Error submitting form: %s", exc)
            return False

    async def check_success(self, page: Page) -> Tuple[bool, str]:
        """Determine if the booking succeeded after submission."""

        t('automation.forms.actions.AcuityFormService.check_success')

        try:
            self.logger.info("🔍 Checking booking success...")
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

                    const confirmMatch = url.match(/\\/confirmation\\/([a-zA-Z0-9]+)/);
                    if (confirmMatch) {
                        const confirmationId = confirmMatch[1];
                        const nameMatch = text.match(/([A-Za-z]+),\\s*¡Tu cita está confirmada!/);
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
                self.logger.info("✅ Booking success: %s", result.get('message'))
                return True, result.get('message', 'Reserva confirmada')

            error = result.get('error', 'unknown')
            message = result.get('message', 'Error desconocido')
            self.logger.warning("❌ Booking failed (%s): %s", error, message)
            return False, message

        except Exception as exc:  # pragma: no cover - defensive guard
            self.logger.error("❌ Error checking booking success: %s", exc)
            return False, f"Error checking booking success: {exc}"

    async def fill_and_submit(self, page: Page, user_info: _UserInfo) -> Tuple[bool, str]:
        """High-level helper that fills, validates, submits, and checks success."""

        t('automation.forms.actions.AcuityFormService.fill_and_submit')

        user_data = self._ensure_user_data(user_info)
        missing = self.validate(user_data)
        if missing:
            field_list = ', '.join(missing)
            self.logger.error("❌ Missing required fields: %s", field_list)
            return False, f"Missing required fields: {field_list}"

        async with self._trace_capture(page):
            filled_count = await self.fill_form(page, user_data)

        if filled_count == 0:
            return False, "❌ Could not fill any form fields"

        self.logger.info("✅ Filled %s fields successfully", filled_count)
        await asyncio.sleep(2)

        has_errors, errors = await self.check_validation(page)
        if has_errors:
            self.logger.error("❌ Form has validation errors, cannot submit:")
            for error in errors:
                self.logger.error("   • %s", error)
            joined = '; '.join(errors)
            return False, f"Form validation failed: {joined}"

        submit_success = await self.submit(page)
        if not submit_success:
            return False, "❌ Form submission failed"

        success, message = await self.check_success(page)
        if not success and 'bot_detected' in message:
            self.logger.warning("🚫 Bot detection triggered - sistema bloqueó uso automatizado")
            return False, "❌ Sistema detectó bot - usar navegador manual para reservar"

        return success, message

    # ------------------------------------------------------------------
    # Internal helpers
    # ------------------------------------------------------------------
    def _ensure_user_data(self, user_info: _UserInfo) -> Dict[str, str]:
        t('automation.forms.actions.AcuityFormService._ensure_user_data')

        if isinstance(user_info, Mapping):
            # If keys already match the required fields, use them directly
            if all(key in user_info for key in REQUIRED_FIELDS):
                return {field: str(user_info.get(field, '') or '') for field in REQUIRED_FIELDS}

        return self.map_user_info(user_info)

    @asynccontextmanager
    async def _trace_capture(self, page: Page):
        if not self.enable_tracing:
            yield None
            return

        context = page.context
        started = False
        try:
            await context.tracing.start(screenshots=True, snapshots=True, sources=True)
            started = True
            self.logger.info("🎥 Started trace recording for form filling debugging")
        except Exception as trace_error:  # pragma: no cover - best effort
            self.logger.warning("⚠️ Could not start tracing: %s", trace_error)

        try:
            yield context if started else None
        finally:
            if started:
                try:
                    trace_path = self.trace_path_template.format(timestamp=int(time.time()))
                    await context.tracing.stop(path=trace_path)
                    self.logger.info("💾 Saved form filling trace to: %s", trace_path)
                except Exception as trace_error:  # pragma: no cover - best effort
                    self.logger.warning("⚠️ Could not save trace: %s", trace_error)

    async def _fill_via_js(self, page: Page, user_data: Mapping[str, str]) -> Tuple[int, Tuple[str, ...]]:
        t('automation.forms.actions.AcuityFormService._fill_via_js')

        result = await page.evaluate(
            """
            (userData) => {
                const fields = {
                    'client.firstName': userData['client.firstName'],
                    'client.lastName': userData['client.lastName'],
                    'client.email': userData['client.email'],
                    'client.phone': userData['client.phone']
                };

                let filled = 0;
                const messages = [];

                Object.entries(fields).forEach(([fieldName, value]) => {
                    if (!value) return;
                    const element = document.querySelector(`input[name="${fieldName}"]`);
                    if (element) {
                        element.value = value;
                        element.dispatchEvent(new Event('input', { bubbles: true }));
                        element.dispatchEvent(new Event('change', { bubbles: true }));
                        filled += 1;
                        messages.push(`✅ ${fieldName}: ${value}`);
                    } else {
                        messages.push(`❌ ${fieldName}: field not found`);
                    }
                });

                return { filled, messages };
            }
            """,
            dict(user_data),
        )

        return int(result.get('filled', 0)), tuple(result.get('messages', ()))

    async def _fill_via_playwright(self, page: Page, user_data: Mapping[str, str]) -> int:
        t('automation.forms.actions.AcuityFormService._fill_via_playwright')

        fields = [
            ('client.firstName', user_data.get('client.firstName', '')),
            ('client.lastName', user_data.get('client.lastName', '')),
            ('client.phone', user_data.get('client.phone', '')),
            ('client.email', user_data.get('client.email', '')),
        ]

        filled_count = 0

        try:
            all_fields = await page.query_selector_all('input[name*="client."]')
            self.logger.info("📊 Found %s client form fields", len(all_fields))
            ready_state = await page.evaluate('() => document.readyState')
            self.logger.info("📊 Document ready state: %s", ready_state)
            await page.wait_for_timeout(1000)
        except Exception as exc:
            self.logger.warning("⚠️ Diagnostics failed: %s", exc)

        for field_name, value in fields:
            if not value:
                continue

            selector = FORM_SELECTORS.get(field_name, f'input[name="{field_name}"]')
            locator = page.locator(selector)

            try:
                self.logger.info("🔍 Checking actionability for %s...", field_name)
                await locator.wait_for(state='visible', timeout=10000)
                await locator.wait_for(state='attached', timeout=5000)

                is_visible = await locator.is_visible()
                is_enabled = await locator.is_enabled()
                count = await locator.count()
                self.logger.info(
                    "📊 %s - Visible: %s, Enabled: %s, Count: %s",
                    field_name,
                    is_visible,
                    is_enabled,
                    count,
                )

                if not is_visible or not is_enabled or count == 0:
                    self.logger.warning("⚠️ %s not ready - trying JavaScript fallback", field_name)
                    await page.evaluate(
                        """
                        (fieldName, value) => {
                            const field = document.querySelector(fieldName);
                            if (field) {
                                field.value = value;
                                field.dispatchEvent(new Event('input', { bubbles: true }));
                                field.dispatchEvent(new Event('change', { bubbles: true }));
                            }
                        }
                        """,
                        selector,
                        value,
                    )
                    filled_count += 1
                    self.logger.info("  ✅ %s: %s (JavaScript fallback)", field_name, value)
                    continue

                self.logger.info("🎯 Filling %s with native Playwright...", field_name)
                await locator.click(timeout=5000)
                await page.wait_for_timeout(200)
                await locator.fill(value, timeout=5000)
                await page.wait_for_timeout(200)
                await locator.press('Tab', timeout=3000)
                await page.wait_for_timeout(200)

                filled_count += 1
                self.logger.info("  ✅ %s: %s (native Playwright)", field_name, value)

            except Exception as exc:
                self.logger.error("  ❌ %s: %s", field_name, exc)

        return filled_count
