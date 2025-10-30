"""Test browser warmup with sophisticated HumanLikeActions and cookie persistence.

This test verifies that:
1. Browser warmup uses sophisticated behavior (HumanLikeActions, not simple mouse moves)
2. Cookie persistence works (save and load browser state)
3. Natural navigation flow executes correctly

Run on Windows CMD:
    pytest tests/bot/test_browser_warmup_playwright.py -v -s

With natural navigation enabled:
    set LV_WARMUP_TEST_ENABLE=1
    pytest tests/bot/test_browser_warmup_playwright.py -v -s
"""

from __future__ import annotations

import os
import shutil
from pathlib import Path

import pytest

from automation.browser.async_browser_pool import AsyncBrowserPool
from automation.browser.pool.manager import BrowserPoolManager, BROWSER_STATES_DIR


@pytest.fixture
def cleanup_browser_states():
    """Cleanup browser states before and after test."""
    # Clean before test
    if BROWSER_STATES_DIR.exists():
        shutil.rmtree(BROWSER_STATES_DIR)

    yield

    # Clean after test
    if BROWSER_STATES_DIR.exists():
        shutil.rmtree(BROWSER_STATES_DIR)


@pytest.mark.asyncio
@pytest.mark.warmup
async def test_browser_warmup_sophisticated_behavior(cleanup_browser_states, caplog):
    """Test that browser warmup uses sophisticated HumanLikeActions, not simple movements.

    This test verifies:
    - Natural navigation is enabled
    - Browser visits main site first
    - Sophisticated warmup behavior is executed (HumanLikeActions)
    - No simple random mouse movements
    """

    flag = os.getenv("LV_WARMUP_TEST_ENABLE", "").strip()
    if flag != "1":
        pytest.skip("Set LV_WARMUP_TEST_ENABLE=1 to run browser warmup test")

    # Use single court for faster test
    test_court = 1
    pool = AsyncBrowserPool(courts=[test_court])

    try:
        # Enable natural navigation (this triggers the warmup flow)
        pool.enable_natural_navigation(True)

        # Start pool (this will execute warmup with HumanLikeActions)
        await pool.start()

        # Wait for pool to be ready
        ready = await pool.wait_until_ready(timeout=60)
        assert ready, "Browser pool failed to initialize within timeout"

        # Verify page was created
        page = pool.pages.get(test_court)
        assert page is not None, f"Court {test_court} page not created"

        # Verify page is on the court URL (after navigation)
        current_url = page.url
        assert "clublavilla.as.me" in current_url, f"Browser not on expected domain: {current_url}"

        # Capture logs to verify sophisticated warmup was used
        log_text = caplog.text

        # Verify sophisticated warmup was used (not simple movements)
        assert "sophisticated warmup" in log_text.lower() or "HumanLikeActions" in log_text, \
            "Sophisticated warmup (HumanLikeActions) was not logged"

        # Make sure we're NOT using simple mouse movements
        # (The old code logged "Simple mouse movement to appear human" which should be gone)
        assert "simple mouse movement" not in log_text.lower(), \
            "Old simple mouse movement code is still being used!"

        print("\n[OK] Sophisticated warmup behavior verified")
        print(f"[OK] Browser navigated to: {current_url}")

    finally:
        await pool.stop()


@pytest.mark.asyncio
@pytest.mark.warmup
@pytest.mark.persistence
async def test_cookie_persistence_save_and_load(cleanup_browser_states, caplog):
    """Test that browser state (cookies) is saved and loaded correctly.

    This test verifies:
    - First run: Browser state is saved after warmup
    - Second run: Browser state is loaded from saved file
    - State files are created in correct location
    """

    flag = os.getenv("LV_WARMUP_TEST_ENABLE", "").strip()
    if flag != "1":
        pytest.skip("Set LV_WARMUP_TEST_ENABLE=1 to run browser warmup test")

    test_court = 1
    state_file = BROWSER_STATES_DIR / f"court_{test_court}_state.json"

    # === FIRST RUN: Save browser state ===
    print("\n=== FIRST RUN: Testing state save ===")

    pool = AsyncBrowserPool(courts=[test_court])

    try:
        pool.enable_natural_navigation(True)
        await pool.start()

        ready = await pool.wait_until_ready(timeout=60)
        assert ready, "Browser pool failed to initialize within timeout"

        # After warmup, state should be saved
        assert state_file.exists(), f"Browser state file not created: {state_file}"
        print(f"[OK] Browser state saved to: {state_file}")

        # Verify state file has content
        state_size = state_file.stat().st_size
        assert state_size > 0, "Browser state file is empty"
        print(f"[OK] State file size: {state_size} bytes")

    finally:
        await pool.stop()

    # === SECOND RUN: Load browser state ===
    print("\n=== SECOND RUN: Testing state load ===")

    # Verify state file still exists
    assert state_file.exists(), "Browser state file was deleted after pool stop"

    pool2 = AsyncBrowserPool(courts=[test_court])

    try:
        pool2.enable_natural_navigation(True)
        await pool2.start()

        ready = await pool2.wait_until_ready(timeout=60)
        assert ready, "Browser pool failed to initialize on second run"

        # Capture logs to verify state was loaded
        log_text = caplog.text

        # Should log that it's loading saved state
        assert "loading saved browser state" in log_text.lower() or "returning user" in log_text.lower(), \
            "Browser state was not loaded on second run"

        print("[OK] Browser state loaded successfully (returning user simulation)")

    finally:
        await pool2.stop()


@pytest.mark.asyncio
@pytest.mark.warmup
async def test_warmup_without_natural_navigation(cleanup_browser_states, caplog):
    """Test that cookie persistence works even without natural navigation warmup.

    This verifies:
    - When natural navigation is OFF: No warmup occurs (no main site visit)
    - But browser state IS still saved (cookie persistence is independent)
    """

    flag = os.getenv("LV_WARMUP_TEST_ENABLE", "").strip()
    if flag != "1":
        pytest.skip("Set LV_WARMUP_TEST_ENABLE=1 to run browser warmup test")

    test_court = 1
    state_file = BROWSER_STATES_DIR / f"court_{test_court}_state.json"
    pool = AsyncBrowserPool(courts=[test_court])

    try:
        # Do NOT enable natural navigation (it's disabled by default)
        # pool.enable_natural_navigation(False)  # This is the default

        await pool.start()
        ready = await pool.wait_until_ready(timeout=60)
        assert ready, "Browser pool failed to initialize"

        log_text = caplog.text

        # Verify NO sophisticated warmup occurred
        assert "sophisticated warmup" not in log_text.lower(), \
            "Sophisticated warmup should not occur when natural navigation is disabled"
        assert "visiting main site first" not in log_text.lower(), \
            "Should not visit main site when natural navigation is disabled"

        # But state file SHOULD still be created (cookie persistence is independent)
        assert state_file.exists(), \
            "Browser state should be saved even when natural navigation is disabled"

        print("[OK] No warmup occurred, but state saved (cookie persistence independent)")

    finally:
        await pool.stop()


@pytest.mark.asyncio
@pytest.mark.warmup
async def test_browser_state_helper_methods():
    """Test the static helper methods for browser state management.

    Tests BrowserPoolManager helper methods without actually starting browsers.
    """

    test_court = 99  # Use unique court number to avoid conflicts
    state_path = BrowserPoolManager._get_storage_state_path(test_court)

    # Initially, should not exist
    assert not BrowserPoolManager._has_saved_state(test_court), \
        f"State should not exist initially: {state_path}"

    # Create a dummy state file
    state_path.parent.mkdir(exist_ok=True)
    state_path.write_text('{"cookies": [], "origins": []}')

    try:
        # Now should exist
        assert BrowserPoolManager._has_saved_state(test_court), \
            "State file should exist after creation"

        # Clear specific state
        cleared = BrowserPoolManager.clear_browser_state(test_court)
        assert cleared, "clear_browser_state should return True when file existed"
        assert not state_path.exists(), "State file should be deleted"

        # Clear again should return False
        cleared_again = BrowserPoolManager.clear_browser_state(test_court)
        assert not cleared_again, "clear_browser_state should return False when file doesn't exist"

        print("[OK] Browser state helper methods work correctly")

    finally:
        # Cleanup
        if state_path.exists():
            state_path.unlink()


if __name__ == "__main__":
    # Allow running directly for quick testing on Windows
    # python tests/bot/test_browser_warmup_playwright.py
    print("Use pytest to run these tests:")
    print("  pytest tests/bot/test_browser_warmup_playwright.py -v -s")
    print("\nOr enable warmup test:")
    print("  set LV_WARMUP_TEST_ENABLE=1")
    print("  pytest tests/bot/test_browser_warmup_playwright.py::test_browser_warmup_sophisticated_behavior -v -s")
