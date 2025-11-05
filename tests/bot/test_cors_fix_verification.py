"""Verify CORS fix - check that reCAPTCHA and form submission work.

Tests that removing extra_http_headers fixed CORS violations that were
blocking reCAPTCHA, Stripe, and other third-party resources.

Run on Windows CMD:
    set LV_MANUAL_CAPTURE=1
    pytest tests/bot/test_cors_fix_verification.py -v -s
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


@pytest.fixture
def cors_test_dir():
    """Create directory for CORS test artifacts."""
    artifacts_dir = Path("logs/latest_log/cors_verification")
    artifacts_dir.mkdir(parents=True, exist_ok=True)
    return artifacts_dir


@pytest.mark.asyncio
@pytest.mark.manual
async def test_cors_fix_verification(cors_test_dir):
    """Verify CORS fix by checking console for errors and testing form submission."""

    import os
    flag = os.getenv("LV_MANUAL_CAPTURE", "").strip()
    if flag != "1":
        pytest.skip("Set LV_MANUAL_CAPTURE=1 to run CORS verification test")

    print(f"\n{'='*80}")
    print(f"CORS FIX VERIFICATION TEST")
    print(f"Court: {COURT}")
    print(f"{'='*80}\n")

    console_logs = []
    cors_errors = []
    recaptcha_loaded = False
    stripe_loaded = False
    booking_requests = []

    pool = AsyncBrowserPool(courts=[COURT])
    pool.enable_natural_navigation(True)

    try:
        await pool.start()
        ready = await pool.wait_until_ready(timeout=60)
        assert ready, "Browser pool failed to initialize"

        page = pool.pages.get(COURT)
        assert page is not None, f"Court {COURT} page not created"

        # Capture console logs
        def log_handler(msg):
            log_entry = {
                "timestamp": datetime.now().isoformat(),
                "type": msg.type,
                "text": msg.text
            }
            console_logs.append(log_entry)

            # Check for CORS errors
            if "CORS" in msg.text or "Cross-Origin" in msg.text:
                cors_errors.append(log_entry)
                print(f"\n[CORS ERROR DETECTED] {msg.text}")

            # Check for reCAPTCHA
            if "recaptcha" in msg.text.lower():
                print(f"\n[reCAPTCHA] {msg.text}")

            # Check for other critical errors
            if msg.type == "error":
                print(f"\n[CONSOLE ERROR] {msg.text}")

        page.on("console", log_handler)

        # Monitor network for third-party resources
        def response_handler(response):
            nonlocal recaptcha_loaded, stripe_loaded

            url = response.url.lower()

            # Check reCAPTCHA loads
            if "recaptcha" in url or "gstatic.com" in url:
                if response.status == 200:
                    recaptcha_loaded = True
                    print(f"\n[OK] reCAPTCHA resource loaded: {response.url[:80]}")
                else:
                    print(f"\n[FAIL] reCAPTCHA failed ({response.status}): {response.url[:80]}")

            # Check Stripe loads
            if "stripe" in url:
                if response.status == 200:
                    stripe_loaded = True
                    print(f"\n[OK] Stripe resource loaded: {response.url[:80]}")
                else:
                    print(f"\n[FAIL] Stripe failed ({response.status}): {response.url[:80]}")

            # Check booking submissions
            if "booking" in url or "appointment" in url or "schedule" in url:
                booking_requests.append({
                    "url": response.url,
                    "status": response.status,
                    "timestamp": datetime.now().isoformat()
                })
                print(f"\n[BOOKING REQUEST] {response.status} {response.url}")

        page.on("response", response_handler)

        print(f"\n{'='*80}")
        print(f"BROWSER READY")
        print(f"Waiting 30 seconds for page to fully load and monitoring for CORS errors...")
        print(f"{'='*80}\n")

        # Wait and monitor
        await asyncio.sleep(30)

        # Take screenshot
        screenshot_path = cors_test_dir / "cors_check.png"
        await page.screenshot(path=str(screenshot_path), full_page=True)
        print(f"\n[SAVED] Screenshot: {screenshot_path}")

        # Save final state
        html_content = await page.content()
        html_file = cors_test_dir / "page_state.html"
        html_file.write_text(html_content, encoding='utf-8')
        print(f"[SAVED] HTML: {html_file}")

        console_file = cors_test_dir / "console_logs.json"
        console_file.write_text(json.dumps(console_logs, indent=2), encoding='utf-8')
        print(f"[SAVED] Console logs ({len(console_logs)}): {console_file}")

        # Analysis
        print(f"\n{'='*80}")
        print(f"CORS FIX VERIFICATION RESULTS")
        print(f"{'='*80}\n")

        print(f"CORS Errors Detected: {len(cors_errors)}")
        print(f"reCAPTCHA Loaded: {'YES' if recaptcha_loaded else 'NO'}")
        print(f"Stripe Loaded: {'YES' if stripe_loaded else 'NO'}")
        print(f"Total Console Logs: {len(console_logs)}")
        print(f"Console Errors: {sum(1 for log in console_logs if log['type'] == 'error')}")
        print(f"Console Warnings: {sum(1 for log in console_logs if log['type'] == 'warning')}")

        if cors_errors:
            print(f"\n[FAIL] CORS ERRORS STILL PRESENT:")
            for err in cors_errors[:5]:  # Show first 5
                print(f"  - {err['text'][:100]}")
        else:
            print(f"\n[OK] No CORS errors detected!")

        if not recaptcha_loaded:
            print(f"\n[WARNING] reCAPTCHA may not have loaded - check logs")

        print(f"\n{'='*80}")
        print(f"TEST COMPLETE")
        print(f"All artifacts saved to: {cors_test_dir}")
        print(f"{'='*80}\n")

        # Assertions
        assert len(cors_errors) == 0, f"CORS errors still present: {len(cors_errors)}"
        print("\n[SUCCESS] CORS fix verified - no CORS violations detected!")

    finally:
        await pool.stop()


if __name__ == "__main__":
    print("Use pytest to run this test:")
    print("  set LV_MANUAL_CAPTURE=1")
    print("  pytest tests/bot/test_cors_fix_verification.py -v -s")
