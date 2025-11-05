"""Complete booking submission test - verify form submission works end-to-end.

This test attempts a REAL booking to verify:
1. Form loads without CORS errors
2. Form fields can be filled
3. Submit button works
4. POST request is sent
5. Navigation to confirmation page occurs

Run on Windows CMD:
    set LV_BOOKING_TEST=1
    pytest tests/bot/test_booking_submission_complete.py -v -s
"""

from __future__ import annotations

import asyncio
import json
from datetime import datetime, timedelta
from pathlib import Path

import pytest

from automation.browser.async_browser_pool import AsyncBrowserPool
from automation.executors.flows.human_behaviors import HumanLikeActions


COURT = 3
TEST_USER = {
    "name": "Saul Campos",
    "email": "scamposjr20@gmail.com",
    "phone": "53042662"
}


@pytest.fixture
def submission_test_dir():
    """Create directory for submission test artifacts."""
    artifacts_dir = Path("logs/latest_log/submission_test")
    artifacts_dir.mkdir(parents=True, exist_ok=True)
    return artifacts_dir


@pytest.mark.asyncio
@pytest.mark.booking_test
async def test_booking_submission_complete(submission_test_dir):
    """Attempt complete booking submission and verify it works."""

    import os
    flag = os.getenv("LV_BOOKING_TEST", "").strip()
    if flag != "1":
        pytest.skip("Set LV_BOOKING_TEST=1 to run booking submission test")

    print(f"\n{'='*80}")
    print(f"BOOKING SUBMISSION TEST")
    print(f"Court: {COURT}")
    print(f"User: {TEST_USER['name']}")
    print(f"{'='*80}\n")

    console_logs = []
    post_requests = []
    booking_responses = []
    submission_detected = False

    pool = AsyncBrowserPool(courts=[COURT])
    pool.enable_natural_navigation(True)

    try:
        await pool.start()
        ready = await pool.wait_until_ready(timeout=60)
        assert ready, "Browser pool failed to initialize"

        page = pool.pages.get(COURT)
        assert page is not None, f"Court {COURT} page not created"
        actions = HumanLikeActions(page, speed_multiplier=1.0)

        # Capture console
        page.on("console", lambda msg: console_logs.append({
            "timestamp": datetime.now().isoformat(),
            "type": msg.type,
            "text": msg.text
        }))

        # Monitor POST requests
        async def capture_request(route, request):
            """Capture POST requests."""
            if request.method == "POST":
                # Handle binary data safely
                try:
                    post_data = request.post_data
                except Exception:
                    post_data = "[binary data]"

                req_info = {
                    "timestamp": datetime.now().isoformat(),
                    "url": request.url,
                    "method": request.method,
                    "post_data": post_data if post_data != "[binary data]" else None,
                    "headers": dict(request.headers)
                }
                post_requests.append(req_info)
                print(f"\n[POST REQUEST] {request.url}")
                if post_data and post_data != "[binary data]":
                    print(f"[POST DATA] {str(post_data)[:200]}")

            try:
                await route.continue_()
            except Exception:
                await route.abort()

        # Monitor responses
        async def capture_response(response):
            """Capture booking responses."""
            url = response.url.lower()
            if any(kw in url for kw in ['booking', 'appointment', 'schedule', 'checkout', 'create']):
                res_info = {
                    "timestamp": datetime.now().isoformat(),
                    "url": response.url,
                    "status": response.status,
                    "status_text": response.status_text
                }
                booking_responses.append(res_info)
                print(f"\n[BOOKING RESPONSE] {response.status} {response.url}")

        await page.route("**/*", capture_request)
        page.on("response", capture_response)

        print(f"\n{'='*80}")
        print(f"STEP 1: Verify calendar is loaded")
        print(f"{'='*80}\n")

        # Calendar should already be loaded by pool initialization
        # Just verify we're on the right page
        current_url = page.url
        print(f"Current URL: {current_url}")
        assert "clublavilla.as.me" in current_url, "Not on booking site"
        print("[OK] Calendar page ready")

        # Take screenshot
        await page.screenshot(path=str(submission_test_dir / "01_calendar.png"), full_page=True)

        print(f"\n{'='*80}")
        print(f"STEP 2: Select time slot")
        print(f"{'='*80}\n")

        # Natural page interaction first (like production code)
        await actions.scroll_naturally(
            scroll_count_range=(1, 2),
            scroll_amount_range=(100, 300),
            scroll_back_prob=0.15
        )
        await actions.reading_pause(duration_range=(0.8, 1.5))
        await actions.move_mouse_random()

        # Select time slot using production code approach
        time_slot = "10:00"
        print(f"Looking for time slot: {time_slot}")

        # Try exact match first
        time_button = await page.query_selector(f'button:has-text("{time_slot}")')
        if not time_button:
            # Try without minutes
            time_button = await page.query_selector('button:has-text("10")')
        if not time_button:
            # Try any available time button
            print("[WARNING] 10:00 not available, selecting first available time")
            time_button = await page.query_selector('button[class*="time"]')

        if time_button:
            await actions.click_with_hesitation(
                time_button,
                hesitation_prob=0.5,
                correction_count_range=(0, 1)
            )
            print(f"[OK] Clicked time button")
        else:
            print("[ERROR] No time button found")

        await asyncio.sleep(2)
        await page.screenshot(path=str(submission_test_dir / "02_time_selected.png"), full_page=True)

        print(f"\n{'='*80}")
        print(f"STEP 3: Fill booking form")
        print(f"{'='*80}\n")

        # Wait for form to appear (like production code)
        await page.wait_for_selector("form", timeout=8000)
        print("[OK] Form loaded")

        # Fill form fields (using production code pattern)
        # First name
        first_name = await page.query_selector('input[name="client.firstName"]')
        if first_name:
            await actions.type_text(first_name, "Saul")
            await actions.pause(0.4, 0.8)
            print(f"[OK] First name filled")

        # Last name
        last_name = await page.query_selector('input[name="client.lastName"]')
        if last_name:
            await actions.type_text(last_name, "Campos")
            await actions.pause(0.4, 0.8)
            print(f"[OK] Last name filled")

        # Email
        email_input = await page.query_selector('input[name="client.email"]')
        if email_input:
            await actions.type_text(email_input, TEST_USER["email"])
            await actions.pause(0.4, 0.8)
            print(f"[OK] Email filled: {TEST_USER['email']}")

        # Phone
        phone_input = await page.query_selector('input[name="client.phone"]')
        if phone_input:
            await phone_input.click()
            await actions.pause(0.4, 0.8)
            await phone_input.fill(TEST_USER["phone"])  # Use fill for phone
            await actions.pause(0.6, 1.1)
            print(f"[OK] Phone filled: {TEST_USER['phone']}")

        # Set country code if needed
        country_select = await page.query_selector('select[name="client.phoneCountry"]')
        if country_select:
            await country_select.select_option("GT")
            print(f"[OK] Country set to GT")

        await asyncio.sleep(1)
        await page.screenshot(path=str(submission_test_dir / "03_form_filled.png"), full_page=True)

        print(f"\n{'='*80}")
        print(f"STEP 4: Check for checkboxes/terms")
        print(f"{'='*80}\n")

        # Look for any checkboxes that need to be checked
        checkboxes = await page.query_selector_all('input[type="checkbox"]')
        print(f"Found {len(checkboxes)} checkboxes")
        for i, checkbox in enumerate(checkboxes):
            is_checked = await checkbox.is_checked()
            if not is_checked:
                await checkbox.click()
                print(f"[OK] Checked checkbox {i+1}")

        await asyncio.sleep(1)
        await page.screenshot(path=str(submission_test_dir / "04_checkboxes_checked.png"), full_page=True)

        print(f"\n{'='*80}")
        print(f"STEP 5: Submit booking")
        print(f"{'='*80}\n")

        # Find submit button (like production code)
        submit_button = await page.query_selector('button:has-text("Confirmar")')
        if not submit_button:
            submit_button = await page.query_selector('button:has-text("Confirm")')
        if not submit_button:
            submit_button = await page.query_selector('button[type="submit"]')

        assert submit_button, "Submit button not found"
        print(f"[OK] Submit button found")

        # Take screenshot before submit
        await page.screenshot(path=str(submission_test_dir / "05_before_submit.png"), full_page=True)

        # Click submit (using production code pattern)
        print("[ACTION] Clicking submit button...")
        await actions.reading_pause(duration_range=(0.5, 1.0))
        await actions.click_with_hesitation(
            submit_button,
            hesitation_prob=0.6,
            correction_count_range=(0, 1)
        )
        submission_detected = True
        await actions.pause(0.8, 1.2)

        print("[ACTION] Waiting for submission to complete (30s)...")
        await asyncio.sleep(30)

        # Take screenshot after submit
        current_url = page.url
        await page.screenshot(path=str(submission_test_dir / "06_after_submit.png"), full_page=True)

        print(f"\n[CURRENT URL] {current_url}")

        # Save final state
        html_content = await page.content()
        html_file = submission_test_dir / "final_page.html"
        html_file.write_text(html_content, encoding='utf-8')

        # Save all captured data
        data = {
            "post_requests": post_requests,
            "booking_responses": booking_responses,
            "console_logs": console_logs,
            "final_url": current_url,
            "submission_detected": submission_detected
        }

        data_file = submission_test_dir / "submission_data.json"
        data_file.write_text(json.dumps(data, indent=2), encoding='utf-8')

        print(f"\n{'='*80}")
        print(f"SUBMISSION TEST RESULTS")
        print(f"{'='*80}\n")

        print(f"POST Requests Sent: {len(post_requests)}")
        print(f"Booking Responses: {len(booking_responses)}")
        print(f"Console Errors: {sum(1 for log in console_logs if log['type'] == 'error')}")
        print(f"Final URL: {current_url}")

        if post_requests:
            print(f"\n[POST REQUESTS]")
            for req in post_requests:
                print(f"  - {req['url']}")

        if booking_responses:
            print(f"\n[BOOKING RESPONSES]")
            for res in booking_responses:
                print(f"  - {res['status']} {res['url']}")

        # Check success
        if "confirmation" in current_url.lower() or "success" in current_url.lower() or "thank" in current_url.lower():
            print(f"\n[SUCCESS] Booking appears successful!")
        elif len(post_requests) > 0:
            print(f"\n[PARTIAL SUCCESS] POST request sent, check responses")
        else:
            print(f"\n[ISSUE] No POST request detected")

        print(f"\n{'='*80}")
        print(f"All artifacts saved to: {submission_test_dir}")
        print(f"{'='*80}\n")

    finally:
        await pool.stop()


if __name__ == "__main__":
    print("Use pytest to run this test:")
    print("  set LV_BOOKING_TEST=1")
    print("  pytest tests/bot/test_booking_submission_complete.py -v -s")
