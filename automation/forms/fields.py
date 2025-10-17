"""Form field helpers for Acuity booking forms."""

from __future__ import annotations

from typing import Dict, Tuple

from playwright.async_api import Page

from tracking import t

FORM_SELECTORS = {
    'client.firstName': 'input[name="client.firstName"]',
    'client.lastName': 'input[name="client.lastName"]',
    'client.phone': 'input[name="client.phone"]',
    'client.email': 'input[name="client.email"]',
}

REQUIRED_FIELDS = tuple(FORM_SELECTORS.keys())


async def fill_fields_javascript(page: Page, user_data: Dict[str, str]) -> Tuple[int, Tuple[str, ...]]:
    """Fill form fields via JavaScript and return count plus log messages."""

    t('automation.forms.fields.fill_fields_javascript')

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
        user_data,
    )

    return int(result.get('filled', 0)), tuple(result.get('messages', ()))


async def fill_fields_playwright(page: Page, user_data: Dict[str, str], *, logger) -> int:
    """Fill form fields via native Playwright interactions."""

    from tracking import t as _t  # local import to avoid cycles

    _t('automation.forms.fields.fill_fields_playwright')

    fields = [
        ('client.firstName', user_data.get('client.firstName', '')),
        ('client.lastName', user_data.get('client.lastName', '')),
        ('client.phone', user_data.get('client.phone', '')),
        ('client.email', user_data.get('client.email', '')),
    ]

    filled_count = 0

    try:
        all_fields = await page.query_selector_all('input[name*="client."]')
        logger.info("📊 Found %s client form fields", len(all_fields))
        ready_state = await page.evaluate('() => document.readyState')
        logger.info("📊 Document ready state: %s", ready_state)
        await page.wait_for_timeout(1000)
    except Exception as exc:
        logger.warning("⚠️ Diagnostics failed: %s", exc)

    for field_name, value in fields:
        if not value:
            continue

        selector = FORM_SELECTORS.get(field_name, f'input[name="{field_name}"]')
        locator = page.locator(selector)

        try:
            logger.info("🔍 Checking actionability for %s...", field_name)
            await locator.wait_for(state='visible', timeout=10000)
            await locator.wait_for(state='attached', timeout=5000)

            is_visible = await locator.is_visible()
            is_enabled = await locator.is_enabled()
            count = await locator.count()
            logger.info(
                "📊 %s - Visible: %s, Enabled: %s, Count: %s",
                field_name,
                is_visible,
                is_enabled,
                count,
            )

            if not is_visible or not is_enabled or count == 0:
                logger.warning("⚠️ %s not ready - trying JavaScript fallback", field_name)
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
                logger.info("  ✅ %s: %s (JavaScript fallback)", field_name, value)
                continue

            logger.info("🎯 Filling %s with native Playwright...", field_name)
            await locator.click(timeout=5000)
            await page.wait_for_timeout(200)
            await locator.fill(value, timeout=5000)
            await page.wait_for_timeout(200)
            await locator.press('Tab', timeout=3000)
            await page.wait_for_timeout(200)

            filled_count += 1
            logger.info("  ✅ %s: %s (native Playwright)", field_name, value)

        except Exception as exc:
            logger.error("  ❌ %s: %s", field_name, exc)

    return filled_count
