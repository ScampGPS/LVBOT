"""Capture booking POST request details to debug submission issues.

This test uses REAL user data (Saul Campos) and captures:
- Complete POST request body
- Request headers
- Response details (if any)
- Timing information

Run on Windows CMD:
    set LV_CAPTURE_POST_ENABLE=1
    pytest tests/bot/test_capture_booking_post.py -v -s
"""

from __future__ import annotations
from tracking import t

import asyncio
import json
import os
from datetime import datetime
from pathlib import Path

import pytest

from automation.browser.async_browser_pool import AsyncBrowserPool


# Test configuration - REAL booking attempt
COURT = 3
TARGET_DATE = "2025-10-31"  # Tomorrow Friday
TARGET_TIME = "10:00"

# REAL user info - Saul Campos
USER_INFO = {
    "first_name": "SAULIN",
    "last_name": "CAMPOS",
    "email": "msaulcampos@gmail.com",
    "phone": "31874277"
}


@pytest.fixture
def capture_artifacts_dir():
    """Create directory for capture artifacts."""
    t('tests.bot.test_capture_booking_post.capture_artifacts_dir')
    artifacts_dir = Path("logs/latest_log/post_capture")
    artifacts_dir.mkdir(parents=True, exist_ok=True)
    return artifacts_dir


async def setup_request_interception(page, artifacts_dir: Path):
    """Set up comprehensive request/response interception."""
    t('tests.bot.test_capture_booking_post.setup_request_interception')

    captured_requests = []
    captured_responses = []

    async def log_request(route, request):
        """Intercept and log all requests."""
        t('tests.bot.test_capture_booking_post.setup_request_interception.log_request')

        # Capture request details
        request_data = {
            "url": request.url,
            "method": request.method,
            "headers": dict(request.headers),
            "post_data": request.post_data if request.method == "POST" else None,
            "timestamp": datetime.now().isoformat(),
            "resource_type": request.resource_type
        }

        # Only log booking-related requests in detail
        if any(keyword in request.url.lower() for keyword in ['booking', 'appointment', 'schedule', 'checkout', 'create']):
            print(f"\n{'='*60}")
            print(f"[INTERCEPT] {request.method} {request.url}")
            print(f"{'='*60}")
            print(f"[HEADERS] {json.dumps(dict(request.headers), indent=2)}")
            if request.post_data:
                print(f"[POST DATA] {request.post_data}")
            print(f"{'='*60}\n")

        captured_requests.append(request_data)

        # Continue the request
        try:
            await route.continue_()
        except Exception as e:
            print(f"[WARN] Failed to continue route: {e}")
            await route.abort()

    async def log_response(response):
        """Log response details."""
        t('tests.bot.test_capture_booking_post.setup_request_interception.log_response')

        # Capture response details
        response_data = {
            "url": response.url,
            "status": response.status,
            "status_text": response.status_text,
            "headers": dict(response.headers),
            "timestamp": datetime.now().isoformat()
        }

        # For booking-related responses, try to get body
        if any(keyword in response.url.lower() for keyword in ['booking', 'appointment', 'schedule', 'checkout', 'create']):
            print(f"\n{'='*60}")
            print(f"[RESPONSE] {response.status} {response.url}")
            print(f"{'='*60}")
            print(f"[STATUS] {response.status} {response.status_text}")
            print(f"[HEADERS] {json.dumps(dict(response.headers), indent=2)}")

            try:
                # Try to get response body
                body = await response.body()
                body_text = body.decode('utf-8')
                print(f"[BODY] {body_text[:1000]}")  # First 1000 chars
                response_data["body"] = body_text
            except Exception as e:
                print(f"[WARN] Could not read response body: {e}")

            print(f"{'='*60}\n")

        captured_responses.append(response_data)

    # Enable request interception
    await page.route("**/*", log_request)
    page.on("response", log_response)

    return captured_requests, captured_responses


@pytest.mark.asyncio
@pytest.mark.capture
async def test_capture_booking_post_request(capture_artifacts_dir):
    """Capture complete booking POST request with real user data."""
    t('tests.bot.test_capture_booking_post.test_capture_booking_post_request')

    flag = os.getenv("LV_CAPTURE_POST_ENABLE", "").strip()
    if flag != "1":
        pytest.skip("Set LV_CAPTURE_POST_ENABLE=1 to run POST capture test")

    print(f"\n{'='*80}")
    print(f"BOOKING POST CAPTURE TEST")
    print(f"User: {USER_INFO['first_name']} {USER_INFO['last_name']}")
    print(f"Court: {COURT}, Date: {TARGET_DATE}, Time: {TARGET_TIME}")
    print(f"{'='*80}\n")

    pool = AsyncBrowserPool(courts=[COURT])
    pool.enable_natural_navigation(True)

    try:
        await pool.start()
        ready = await pool.wait_until_ready(timeout=60)
        assert ready, "Browser pool failed to initialize"

        page = pool.pages.get(COURT)
        assert page is not None, f"Court {COURT} page not created"

        # Set up request/response interception
        captured_requests, captured_responses = await setup_request_interception(
            page, capture_artifacts_dir
        )

        print("[OK] Request interception enabled")

        # STEP 1: Find and click time slot
        print(f"\n[ACTION] Looking for time slot: {TARGET_TIME}")

        time_selectors = [
            f'button:has-text("{TARGET_TIME}")',
            f'button:has-text("{TARGET_TIME.replace(":00", "")}")',
            f'button:has-text("{TARGET_TIME.split(":")[0]}")'
        ]

        time_button = None
        for selector in time_selectors:
            time_button = await page.query_selector(selector)
            if time_button:
                print(f"[FOUND] Time button: {selector}")
                break

        if not time_button:
            pytest.fail(f"Time slot {TARGET_TIME} not found")

        print(f"[ACTION] Clicking time slot...")
        await time_button.click()
        await asyncio.sleep(2)

        # STEP 2: Fill form with REAL user info
        print(f"\n[ACTION] Filling form with REAL user data...")
        print(f"  Name: {USER_INFO['first_name']} {USER_INFO['last_name']}")
        print(f"  Email: {USER_INFO['email']}")
        print(f"  Phone: {USER_INFO['phone']}")

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
                await element.click()
                await asyncio.sleep(0.2)
                await element.fill(value)
                await asyncio.sleep(0.2)
                print(f"  [OK] Filled {key}")

        # Set country
        try:
            country_select = await page.query_selector('select[name="client.phoneCountry"]')
            if country_select:
                await country_select.select_option("GT")
                print(f"  [OK] Set country: GT")
        except Exception:
            pass

        print(f"\n[OK] Form filled with real user data")

        # STEP 3: Take screenshot before submit
        screenshot_before = capture_artifacts_dir / "before_submit.png"
        await page.screenshot(path=str(screenshot_before), full_page=True)
        print(f"[OK] Screenshot saved: {screenshot_before}")

        # STEP 4: Find submit button
        submit_button = await page.query_selector('button:has-text("Confirmar")')
        if not submit_button:
            submit_button = await page.query_selector('button:has-text("Confirm")')

        if not submit_button:
            pytest.fail("Submit button not found!")

        print(f"\n{'='*80}")
        print(f"[ACTION] Clicking SUBMIT button with hesitation (like production)...")
        print(f"[WATCH] Intercepting requests/responses...")
        print(f"{'='*80}\n")

        # STEP 5: Click submit with hesitation (CRITICAL - triggers hover events)
        from automation.executors.flows.human_behaviors import HumanLikeActions
        actions = HumanLikeActions(page, speed_multiplier=1.8)

        # Reading pause before submit (like production)
        await actions.reading_pause(duration_range=(0.5, 1.0))

        # Click with hesitation (moves mouse, hovers, then clicks)
        print("[DEBUG] Using click_with_hesitation (bezier curves + hover)")
        await actions.click_with_hesitation(
            submit_button,
            hesitation_prob=0.6,
            correction_count_range=(0, 1)
        )

        # Pause after click
        await actions.pause(0.8, 1.2)

        # Wait 5 seconds for request to be sent
        print("[WAIT] Waiting 5 seconds for POST request...")
        await asyncio.sleep(5)

        # Take screenshot after click
        screenshot_after = capture_artifacts_dir / "after_submit_5s.png"
        await page.screenshot(path=str(screenshot_after), full_page=True)
        print(f"[OK] Screenshot saved: {screenshot_after}")

        # Wait longer (total 60 seconds)
        print("[WAIT] Waiting additional 55 seconds for response...")
        for i in range(11):  # 11 x 5 = 55 seconds
            await asyncio.sleep(5)
            print(f"  ... {5 * (i + 2)} seconds elapsed")

        # Take final screenshot
        screenshot_final = capture_artifacts_dir / "after_submit_60s.png"
        await page.screenshot(path=str(screenshot_final), full_page=True)
        print(f"[OK] Final screenshot saved: {screenshot_final}")

        # STEP 6: Save all captured requests/responses
        print(f"\n{'='*80}")
        print(f"ANALYSIS")
        print(f"{'='*80}\n")

        # Save full request log
        requests_file = capture_artifacts_dir / "all_requests.json"
        requests_file.write_text(json.dumps(captured_requests, indent=2), encoding='utf-8')
        print(f"[SAVED] All requests: {requests_file}")

        responses_file = capture_artifacts_dir / "all_responses.json"
        responses_file.write_text(json.dumps(captured_responses, indent=2), encoding='utf-8')
        print(f"[SAVED] All responses: {responses_file}")

        # Filter booking-related requests
        booking_requests = [
            req for req in captured_requests
            if any(keyword in req['url'].lower() for keyword in
                   ['booking', 'appointment', 'schedule', 'checkout', 'create'])
        ]

        booking_responses = [
            res for res in captured_responses
            if any(keyword in res['url'].lower() for keyword in
                   ['booking', 'appointment', 'schedule', 'checkout', 'create'])
        ]

        print(f"\n[SUMMARY]")
        print(f"  Total requests captured: {len(captured_requests)}")
        print(f"  Total responses captured: {len(captured_responses)}")
        print(f"  Booking-related requests: {len(booking_requests)}")
        print(f"  Booking-related responses: {len(booking_responses)}")

        if booking_requests:
            print(f"\n[BOOKING REQUESTS]")
            for i, req in enumerate(booking_requests, 1):
                print(f"  {i}. {req['method']} {req['url']}")
                if req['post_data']:
                    print(f"     POST DATA: {req['post_data'][:200]}")

        if booking_responses:
            print(f"\n[BOOKING RESPONSES]")
            for i, res in enumerate(booking_responses, 1):
                print(f"  {i}. {res['status']} {res['url']}")

        # Check current URL
        final_url = page.url
        print(f"\n[FINAL URL] {final_url}")

        # Check if confirmation page
        if "confirmation" in final_url.lower() or "success" in final_url.lower():
            print(f"[SUCCESS] Booking appears to have succeeded!")
        else:
            print(f"[WARNING] Still on form page - booking may have failed")

        print(f"\n{'='*80}")
        print(f"POST CAPTURE COMPLETE")
        print(f"Check artifacts in: {capture_artifacts_dir}")
        print(f"{'='*80}\n")

    finally:
        await pool.stop()


if __name__ == "__main__":
    print("Use pytest to run this test:")
    print("  set LV_CAPTURE_POST_ENABLE=1")
    print("  pytest tests/bot/test_capture_booking_post.py -v -s")
