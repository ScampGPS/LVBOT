"""Debug test to investigate booking submission issues with detailed inspection.

This test attempts a real booking and captures EVERYTHING:
- HTML content before/after submission
- DOM state and hidden elements
- Iframes and shadow DOM
- Network requests
- Console logs
- Screenshots at each step
- Button state and attributes

Run on Windows CMD:
    set LV_DEBUG_BOOKING_ENABLE=1
    pytest tests/bot/test_debug_booking_submission.py -v -s
"""

from __future__ import annotations

import asyncio
import json
import os
from datetime import datetime, timedelta
from pathlib import Path

import pytest
import pytz

from automation.browser.async_browser_pool import AsyncBrowserPool
from automation.executors.flows.natural_flow import execute_natural_flow


# Test configuration
COURT = 3
TARGET_DATE = "2025-10-31"  # Tomorrow Friday
TARGET_TIME = "10:00"
TIMEZONE = "America/Guatemala"

# User info for booking
USER_INFO = {
    "first_name": "Test",
    "last_name": "User",
    "email": "test@example.com",
    "phone": "12345678"
}


@pytest.fixture
def debug_artifacts_dir():
    """Create directory for debug artifacts."""
    artifacts_dir = Path("logs/latest_log/debug_booking")
    artifacts_dir.mkdir(parents=True, exist_ok=True)
    return artifacts_dir


async def capture_page_state(page, step_name: str, artifacts_dir: Path):
    """Capture comprehensive page state for debugging."""

    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    prefix = f"{step_name}_{timestamp}"

    print(f"\n{'='*60}")
    print(f"[DEBUG] Capturing state: {step_name}")
    print(f"{'='*60}")

    # 1. Screenshot
    screenshot_path = artifacts_dir / f"{prefix}_screenshot.png"
    await page.screenshot(path=str(screenshot_path), full_page=True)
    print(f"[OK] Screenshot saved: {screenshot_path}")

    # 2. Full HTML
    html_content = await page.content()
    html_path = artifacts_dir / f"{prefix}_page.html"
    html_path.write_text(html_content, encoding='utf-8')
    print(f"[OK] HTML saved: {html_path}")

    # 3. Current URL
    current_url = page.url
    print(f"[URL] {current_url}")

    # 4. Check for iframes
    frames = page.frames
    print(f"[FRAMES] Found {len(frames)} frame(s)")
    for i, frame in enumerate(frames):
        frame_url = frame.url
        print(f"  Frame {i}: {frame_url}")
        if frame_url != "about:blank":
            try:
                frame_html = await frame.content()
                frame_path = artifacts_dir / f"{prefix}_frame_{i}.html"
                frame_path.write_text(frame_html, encoding='utf-8')
                print(f"  [OK] Frame {i} HTML saved")
            except Exception as e:
                print(f"  [WARN] Could not capture frame {i}: {e}")

    # 5. Check for hidden elements
    hidden_elements = await page.eval_on_selector_all(
        '[type="hidden"]',
        '(elements) => elements.map(el => ({ name: el.name, value: el.value, id: el.id }))'
    )
    if hidden_elements:
        print(f"[HIDDEN] Found {len(hidden_elements)} hidden input(s):")
        for el in hidden_elements:
            print(f"  - {el}")

    # 6. Check form state
    try:
        form_info = await page.evaluate('''() => {
            const form = document.querySelector('form');
            if (!form) return null;
            return {
                action: form.action,
                method: form.method,
                enctype: form.enctype,
                fieldCount: form.elements.length
            };
        }''')
        if form_info:
            print(f"[FORM] {json.dumps(form_info, indent=2)}")
    except Exception as e:
        print(f"[WARN] Could not inspect form: {e}")

    # 7. Console logs (if available)
    print(f"{'='*60}\n")


async def inspect_submit_button(page, artifacts_dir: Path):
    """Inspect submit button state and attributes."""

    print(f"\n{'='*60}")
    print("[DEBUG] Inspecting Submit Button")
    print(f"{'='*60}")

    # Find submit button
    submit_selectors = [
        'button:has-text("Confirmar")',
        'button:has-text("Confirm")',
        'button[type="submit"]',
        'input[type="submit"]'
    ]

    submit_button = None
    used_selector = None

    for selector in submit_selectors:
        submit_button = await page.query_selector(selector)
        if submit_button:
            used_selector = selector
            break

    if not submit_button:
        print("[ERROR] Submit button not found!")
        return None

    print(f"[FOUND] Button found with selector: {used_selector}")

    # Get button properties
    button_info = await submit_button.evaluate('''(btn) => {
        const rect = btn.getBoundingClientRect();
        const computed = window.getComputedStyle(btn);
        return {
            text: btn.textContent.trim(),
            disabled: btn.disabled,
            type: btn.type,
            id: btn.id,
            className: btn.className,
            visible: computed.display !== 'none' && computed.visibility !== 'hidden',
            position: {
                top: rect.top,
                left: rect.left,
                width: rect.width,
                height: rect.height
            },
            styles: {
                display: computed.display,
                visibility: computed.visibility,
                opacity: computed.opacity,
                cursor: computed.cursor,
                pointerEvents: computed.pointerEvents
            },
            attributes: Array.from(btn.attributes).map(attr => ({
                name: attr.name,
                value: attr.value
            }))
        };
    }''')

    print(f"[BUTTON] State:")
    print(json.dumps(button_info, indent=2))

    # Take screenshot of button area
    try:
        await submit_button.screenshot(path=str(artifacts_dir / "submit_button.png"))
        print(f"[OK] Button screenshot saved")
    except Exception as e:
        print(f"[WARN] Could not screenshot button: {e}")

    print(f"{'='*60}\n")

    return submit_button


@pytest.mark.asyncio
@pytest.mark.debug
async def test_debug_booking_submission(debug_artifacts_dir):
    """Debug booking submission with comprehensive state inspection."""

    flag = os.getenv("LV_DEBUG_BOOKING_ENABLE", "").strip()
    if flag != "1":
        pytest.skip("Set LV_DEBUG_BOOKING_ENABLE=1 to run debug booking test")

    print(f"\n{'='*80}")
    print(f"DEBUG BOOKING TEST")
    print(f"Court: {COURT}, Date: {TARGET_DATE}, Time: {TARGET_TIME}")
    print(f"{'='*80}\n")

    pool = AsyncBrowserPool(courts=[COURT])

    # Enable natural navigation (uses HumanLikeActions)
    pool.enable_natural_navigation(True)

    # Enable console message logging
    console_logs = []

    try:
        await pool.start()
        ready = await pool.wait_until_ready(timeout=60)
        assert ready, "Browser pool failed to initialize"

        page = pool.pages.get(COURT)
        assert page is not None, f"Court {COURT} page not created"

        # Capture console logs
        page.on("console", lambda msg: console_logs.append({
            "type": msg.type,
            "text": msg.text
        }))

        # Also capture network requests
        network_logs = []
        page.on("request", lambda request: network_logs.append({
            "url": request.url,
            "method": request.method,
            "type": "request"
        }))
        page.on("response", lambda response: network_logs.append({
            "url": response.url,
            "status": response.status,
            "type": "response"
        }))

        print("[OK] Browser initialized with monitoring")

        # STEP 1: Capture initial state (on court page)
        await capture_page_state(page, "01_initial_court_page", debug_artifacts_dir)

        # STEP 2: Find and click time slot
        print(f"[ACTION] Looking for time slot: {TARGET_TIME}")

        time_selectors = [
            f'button:has-text("{TARGET_TIME}")',
            f'button:has-text("{TARGET_TIME.replace(":00", "")}")',
            f'button:has-text("{TARGET_TIME.split(":")[0]}")'
        ]

        time_button = None
        for selector in time_selectors:
            time_button = await page.query_selector(selector)
            if time_button:
                print(f"[FOUND] Time button with selector: {selector}")
                break

        if not time_button:
            print("[ERROR] Time slot not found!")
            await capture_page_state(page, "ERROR_time_not_found", debug_artifacts_dir)
            pytest.fail(f"Time slot {TARGET_TIME} not found")

        # Click time slot
        print(f"[ACTION] Clicking time slot...")
        await time_button.click()
        await asyncio.sleep(2)  # Wait for form to load

        # STEP 3: Capture form state
        await capture_page_state(page, "02_after_time_click", debug_artifacts_dir)

        # STEP 4: Fill form using natural flow typing
        print(f"[ACTION] Filling form with user info...")

        # Import HumanLikeActions for natural typing
        from automation.executors.flows.human_behaviors import HumanLikeActions
        actions = HumanLikeActions(page, speed_multiplier=1.8)

        # Fill fields
        selectors = [
            ('first_name', 'input[name="client.firstName"]'),
            ('last_name', 'input[name="client.lastName"]'),
            ('email', 'input[name="client.email"]'),
            ('phone', 'input[name="client.phone"]'),
        ]

        for key, selector in selectors:
            element = await page.query_selector(selector)
            if element:
                value = USER_INFO[key]
                print(f"  Filling {key}: {value}")
                await element.click()
                await asyncio.sleep(0.3)
                await element.fill(value)  # Use fill for speed in debug
                await asyncio.sleep(0.2)

        # Set country if needed
        try:
            country_select = await page.query_selector('select[name="client.phoneCountry"]')
            if country_select:
                await country_select.select_option("GT")
                print(f"  Set country: GT")
        except Exception:
            pass

        # STEP 5: Capture form filled state
        await capture_page_state(page, "03_form_filled", debug_artifacts_dir)

        # STEP 6: Inspect submit button BEFORE clicking
        submit_button = await inspect_submit_button(page, debug_artifacts_dir)

        if not submit_button:
            pytest.fail("Submit button not found!")

        # STEP 7: Click submit button and monitor what happens
        print(f"\n{'='*60}")
        print("[ACTION] Clicking submit button...")
        print(f"{'='*60}\n")

        # Capture state just before click
        await capture_page_state(page, "04_before_submit_click", debug_artifacts_dir)

        # Click the button
        await submit_button.click()

        # Wait a bit and see what happens
        print("[WAIT] Waiting 3 seconds to see what happens...")
        await asyncio.sleep(3)

        # STEP 8: Capture state after click
        await capture_page_state(page, "05_after_submit_click", debug_artifacts_dir)

        # STEP 9: Inspect button again (maybe it's still there?)
        await inspect_submit_button(page, debug_artifacts_dir)

        # STEP 10: Check if we navigated anywhere
        current_url = page.url
        print(f"\n[URL] Current URL after submit: {current_url}")

        # STEP 11: Wait longer and check again
        print("[WAIT] Waiting 10 more seconds...")
        await asyncio.sleep(10)

        await capture_page_state(page, "06_after_long_wait", debug_artifacts_dir)

        # STEP 12: Check for confirmation elements
        print("\n[CHECK] Looking for confirmation indicators...")

        confirmation_selectors = [
            'text=confirmed',
            'text=confirmation',
            'text=success',
            'text=booking',
            '[class*="success"]',
            '[class*="confirm"]',
            '[class*="thank"]'
        ]

        for selector in confirmation_selectors:
            element = await page.query_selector(selector)
            if element:
                text = await element.text_content()
                print(f"[FOUND] Confirmation element: {selector} -> {text}")

        # Save all logs
        logs_file = debug_artifacts_dir / "console_logs.json"
        logs_file.write_text(json.dumps(console_logs, indent=2), encoding='utf-8')
        print(f"\n[OK] Console logs saved: {logs_file}")

        network_file = debug_artifacts_dir / "network_logs.json"
        network_file.write_text(json.dumps(network_logs, indent=2), encoding='utf-8')
        print(f"[OK] Network logs saved: {network_file}")

        print(f"\n{'='*80}")
        print(f"DEBUG TEST COMPLETE - Check artifacts in: {debug_artifacts_dir}")
        print(f"{'='*80}\n")

    finally:
        await pool.stop()


if __name__ == "__main__":
    print("Use pytest to run this test:")
    print("  set LV_DEBUG_BOOKING_ENABLE=1")
    print("  pytest tests/bot/test_debug_booking_submission.py -v -s")
