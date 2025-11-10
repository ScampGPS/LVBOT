"""Manual booking test - YOU book, WE capture everything.

Opens Chrome and lets you manually complete the booking while capturing:
- All network requests/responses with full bodies
- Console logs (errors, warnings, info)
- Screenshots at 10s intervals
- Final DOM state
- Cookies
- localStorage/sessionStorage

Run on Windows CMD:
    set LV_MANUAL_CAPTURE=1
    pytest tests/bot/test_manual_booking_capture.py -v -s
"""

from __future__ import annotations
from tracking import t

import asyncio
import json
from datetime import datetime
from pathlib import Path

import pytest

from automation.browser.async_browser_pool import AsyncBrowserPool


COURT = 3
CAPTURE_DURATION = 60  # seconds


@pytest.fixture
def manual_capture_dir():
    """Create directory for manual capture artifacts."""
    t('tests.bot.test_manual_booking_capture.manual_capture_dir')
    artifacts_dir = Path("logs/latest_log/manual_capture")
    artifacts_dir.mkdir(parents=True, exist_ok=True)
    return artifacts_dir


@pytest.mark.asyncio
@pytest.mark.manual
async def test_manual_booking_capture(manual_capture_dir):
    """Open browser and let user manually book while capturing everything."""
    t('tests.bot.test_manual_booking_capture.test_manual_booking_capture')

    import os
    flag = os.getenv("LV_MANUAL_CAPTURE", "").strip()
    if flag != "1":
        pytest.skip("Set LV_MANUAL_CAPTURE=1 to run manual capture test")

    print(f"\n{'='*80}")
    print(f"MANUAL BOOKING CAPTURE")
    print(f"Court: {COURT}")
    print(f"Duration: {CAPTURE_DURATION} seconds")
    print(f"{'='*80}\n")

    # Storage for captured data
    all_requests = []
    all_responses = []
    console_logs = []
    screenshots = []
    keyboard_events = []
    mouse_events = []

    pool = AsyncBrowserPool(courts=[COURT])
    pool.enable_natural_navigation(True)

    try:
        await pool.start()
        ready = await pool.wait_until_ready(timeout=60)
        assert ready, "Browser pool failed to initialize"

        page = pool.pages.get(COURT)
        assert page is not None, f"Court {COURT} page not created"

        # Set up comprehensive request interception
        async def capture_request(route, request):
            """Capture all request details."""
            t('tests.bot.test_manual_booking_capture.test_manual_booking_capture.capture_request')
            req_data = {
                "timestamp": datetime.now().isoformat(),
                "url": request.url,
                "method": request.method,
                "headers": dict(request.headers),
                "post_data": request.post_data if request.method == "POST" else None,
                "resource_type": request.resource_type
            }
            all_requests.append(req_data)

            # Log booking-related requests in real-time
            if any(kw in request.url.lower() for kw in ['booking', 'appointment', 'schedule', 'checkout', 'create']):
                print(f"\n[REQUEST] {request.method} {request.url}")
                if request.post_data:
                    print(f"[POST DATA] {request.post_data[:500]}")

            try:
                await route.continue_()
            except Exception:
                await route.abort()

        async def capture_response(response):
            """Capture all response details including body."""
            t('tests.bot.test_manual_booking_capture.test_manual_booking_capture.capture_response')
            res_data = {
                "timestamp": datetime.now().isoformat(),
                "url": response.url,
                "status": response.status,
                "status_text": response.status_text,
                "headers": dict(response.headers)
            }

            # Try to get response body
            try:
                if response.status != 304:  # Skip not-modified responses
                    body = await response.body()
                    body_text = body.decode('utf-8', errors='ignore')
                    res_data["body"] = body_text

                    # Log booking responses in real-time
                    if any(kw in response.url.lower() for kw in ['booking', 'appointment', 'schedule', 'checkout', 'create']):
                        print(f"\n[RESPONSE] {response.status} {response.url}")
                        print(f"[BODY] {body_text[:500]}")
            except Exception:
                pass

            all_responses.append(res_data)

        # Capture console logs
        page.on("console", lambda msg: console_logs.append({
            "timestamp": datetime.now().isoformat(),
            "type": msg.type,
            "text": msg.text
        }))

        # Inject event listeners for keyboard and mouse
        await page.evaluate('''() => {
            window.__capturedEvents__ = {
                keyboard: [],
                mouse: []
            };

            document.addEventListener('keydown', (e) => {
                window.__capturedEvents__.keyboard.push({
                    timestamp: new Date().toISOString(),
                    type: 'keydown',
                    key: e.key,
                    code: e.code,
                    ctrlKey: e.ctrlKey,
                    shiftKey: e.shiftKey,
                    altKey: e.altKey
                });
            });

            document.addEventListener('keyup', (e) => {
                window.__capturedEvents__.keyboard.push({
                    timestamp: new Date().toISOString(),
                    type: 'keyup',
                    key: e.key,
                    code: e.code
                });
            });

            document.addEventListener('click', (e) => {
                window.__capturedEvents__.mouse.push({
                    timestamp: new Date().toISOString(),
                    type: 'click',
                    x: e.clientX,
                    y: e.clientY,
                    target: e.target.tagName,
                    targetId: e.target.id,
                    targetClass: e.target.className
                });
            });

            document.addEventListener('mousemove', (e) => {
                // Only capture every 100ms to avoid too much data
                if (!window.__lastMouseCapture__ || Date.now() - window.__lastMouseCapture__ > 100) {
                    window.__capturedEvents__.mouse.push({
                        timestamp: new Date().toISOString(),
                        type: 'mousemove',
                        x: e.clientX,
                        y: e.clientY
                    });
                    window.__lastMouseCapture__ = Date.now();
                }
            });
        }''')

        # Enable interception
        await page.route("**/*", capture_request)
        page.on("response", capture_response)

        print(f"\n{'='*80}")
        print(f"BROWSER READY - PLEASE COMPLETE BOOKING MANUALLY")
        print(f"You have {CAPTURE_DURATION} seconds")
        print(f"{'='*80}\n")

        # Take screenshots every 10 seconds
        for i in range(CAPTURE_DURATION // 10):
            await asyncio.sleep(10)

            screenshot_path = manual_capture_dir / f"screenshot_{i*10}s.png"
            await page.screenshot(path=str(screenshot_path), full_page=True)
            screenshots.append(str(screenshot_path))

            current_url = page.url
            print(f"[{(i+1)*10}s] URL: {current_url}")
            print(f"[{(i+1)*10}s] Screenshot: {screenshot_path}")

        # Final screenshot
        final_screenshot = manual_capture_dir / f"screenshot_{CAPTURE_DURATION}s_FINAL.png"
        await page.screenshot(path=str(final_screenshot), full_page=True)
        screenshots.append(str(final_screenshot))

        # Capture final state
        print(f"\n{'='*80}")
        print(f"CAPTURING FINAL STATE")
        print(f"{'='*80}\n")

        # Final URL
        final_url = page.url
        print(f"[FINAL URL] {final_url}")

        # Final HTML
        html_content = await page.content()
        html_file = manual_capture_dir / "final_page.html"
        html_file.write_text(html_content, encoding='utf-8')
        print(f"[SAVED] Final HTML: {html_file}")

        # Cookies
        cookies = await page.context.cookies()
        cookies_file = manual_capture_dir / "cookies.json"
        cookies_file.write_text(json.dumps(cookies, indent=2), encoding='utf-8')
        print(f"[SAVED] Cookies: {cookies_file}")

        # localStorage and sessionStorage
        storage = await page.evaluate('''() => {
            return {
                localStorage: Object.entries(localStorage),
                sessionStorage: Object.entries(sessionStorage)
            };
        }''')
        storage_file = manual_capture_dir / "storage.json"
        storage_file.write_text(json.dumps(storage, indent=2), encoding='utf-8')
        print(f"[SAVED] Storage: {storage_file}")

        # Get captured keyboard and mouse events
        captured_events = await page.evaluate('() => window.__capturedEvents__')
        if captured_events:
            keyboard_events = captured_events.get('keyboard', [])
            mouse_events = captured_events.get('mouse', [])

            keyboard_file = manual_capture_dir / "keyboard_events.json"
            keyboard_file.write_text(json.dumps(keyboard_events, indent=2), encoding='utf-8')
            print(f"[SAVED] Keyboard events ({len(keyboard_events)}): {keyboard_file}")

            mouse_file = manual_capture_dir / "mouse_events.json"
            mouse_file.write_text(json.dumps(mouse_events, indent=2), encoding='utf-8')
            print(f"[SAVED] Mouse events ({len(mouse_events)}): {mouse_file}")

        # Save all captured data
        requests_file = manual_capture_dir / "all_requests.json"
        requests_file.write_text(json.dumps(all_requests, indent=2), encoding='utf-8')
        print(f"[SAVED] Requests ({len(all_requests)}): {requests_file}")

        responses_file = manual_capture_dir / "all_responses.json"
        responses_file.write_text(json.dumps(all_responses, indent=2), encoding='utf-8')
        print(f"[SAVED] Responses ({len(all_responses)}): {responses_file}")

        console_file = manual_capture_dir / "console_logs.json"
        console_file.write_text(json.dumps(console_logs, indent=2), encoding='utf-8')
        print(f"[SAVED] Console logs ({len(console_logs)}): {console_file}")

        # Analysis summary
        print(f"\n{'='*80}")
        print(f"ANALYSIS SUMMARY")
        print(f"{'='*80}\n")

        # Find booking-related requests
        booking_requests = [
            req for req in all_requests
            if any(kw in req['url'].lower() for kw in ['booking', 'appointment', 'schedule', 'checkout', 'create'])
        ]

        booking_responses = [
            res for res in all_responses
            if any(kw in res['url'].lower() for kw in ['booking', 'appointment', 'schedule', 'checkout', 'create'])
        ]

        print(f"Total requests: {len(all_requests)}")
        print(f"Total responses: {len(all_responses)}")
        print(f"Booking-related requests: {len(booking_requests)}")
        print(f"Booking-related responses: {len(booking_responses)}")
        print(f"Console logs: {len(console_logs)}")
        print(f"Keyboard events: {len(keyboard_events) if captured_events else 0}")
        print(f"Mouse events: {len(mouse_events) if captured_events else 0}")
        print(f"Screenshots: {len(screenshots)}")

        if booking_requests:
            print(f"\n[BOOKING REQUESTS]")
            for req in booking_requests:
                print(f"  {req['method']} {req['url']}")

        if booking_responses:
            print(f"\n[BOOKING RESPONSES]")
            for res in booking_responses:
                print(f"  {res['status']} {res['url']}")

        # Check if successful
        if "confirmation" in final_url.lower() or "success" in final_url.lower():
            print(f"\n[SUCCESS] Booking appears successful!")
        elif "datetime" in final_url.lower():
            print(f"\n[NOTICE] Still on form page")
        else:
            print(f"\n[UNKNOWN] Check final URL and screenshots")

        print(f"\n{'='*80}")
        print(f"MANUAL CAPTURE COMPLETE")
        print(f"All artifacts saved to: {manual_capture_dir}")
        print(f"{'='*80}\n")

    finally:
        await pool.stop()


if __name__ == "__main__":
    print("Use pytest to run this test:")
    print("  set LV_MANUAL_CAPTURE=1")
    print("  pytest tests/bot/test_manual_booking_capture.py -v -s")
