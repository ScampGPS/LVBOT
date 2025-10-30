# Browser Warmup Test Instructions

## Overview

Tests the sophisticated browser warmup flow with:
- ✅ HumanLikeActions (bezier curves, natural scrolling, reading pauses)
- ✅ Cookie persistence (save/load browser state)
- ✅ Natural navigation flow

## Running Tests on Windows CMD

### 1. Setup Environment

```cmd
cd C:\Users\SaulCamposJr\Documents\code\Python\LVBot
```

### 2. Enable Warmup Tests

```cmd
set LV_WARMUP_TEST_ENABLE=1
```

### 3. Run All Warmup Tests

```cmd
pytest tests/bot/test_browser_warmup_playwright.py -v -s
```

### 4. Run Individual Tests

**Test sophisticated warmup behavior:**
```cmd
pytest tests/bot/test_browser_warmup_playwright.py::test_browser_warmup_sophisticated_behavior -v -s
```

**Test cookie persistence (save and load):**
```cmd
pytest tests/bot/test_browser_warmup_playwright.py::test_cookie_persistence_save_and_load -v -s
```

**Test backward compatibility (no warmup when disabled):**
```cmd
pytest tests/bot/test_browser_warmup_playwright.py::test_warmup_without_natural_navigation -v -s
```

**Test helper methods (fast, no browser):**
```cmd
pytest tests/bot/test_browser_warmup_playwright.py::test_browser_state_helper_methods -v -s
```

### 5. Run with Markers

**Run only warmup tests:**
```cmd
pytest -m warmup -v -s
```

**Run only persistence tests:**
```cmd
pytest -m persistence -v -s
```

## What Each Test Verifies

### `test_browser_warmup_sophisticated_behavior`
- ✅ Natural navigation is enabled
- ✅ Browser visits main site first
- ✅ Uses HumanLikeActions (bezier curves, scrolling, pauses)
- ✅ Does NOT use old simple mouse movements
- ✅ Logs show "sophisticated warmup"

### `test_cookie_persistence_save_and_load`
- ✅ **First run:** Creates `browser_states/court_1_state.json`
- ✅ **Second run:** Loads saved state (appears as returning user)
- ✅ State files contain cookies and localStorage
- ✅ Logs show "loading saved browser state"

### `test_warmup_without_natural_navigation`
- ✅ When natural navigation is OFF, no warmup occurs
- ✅ No state files created
- ✅ Backward compatibility maintained

### `test_browser_state_helper_methods`
- ✅ `_get_storage_state_path()` returns correct path
- ✅ `_has_saved_state()` detects existing files
- ✅ `clear_browser_state()` deletes state files
- ✅ Fast test (no browser needed)

## Expected Output (Success)

```
tests/bot/test_browser_warmup_playwright.py::test_browser_warmup_sophisticated_behavior PASSED
tests/bot/test_browser_warmup_playwright.py::test_cookie_persistence_save_and_load PASSED
tests/bot/test_browser_warmup_playwright.py::test_warmup_without_natural_navigation PASSED
tests/bot/test_browser_state_helper_methods PASSED

✅ Sophisticated warmup behavior verified
✅ Browser navigated to: https://clublavilla.as.me/schedule.php?...
✅ Browser state saved to: browser_states\court_1_state.json
✅ State file size: 2481 bytes
✅ Browser state loaded successfully (returning user simulation)
```

## Test Duration

- `test_browser_warmup_sophisticated_behavior`: ~30-40 seconds
- `test_cookie_persistence_save_and_load`: ~60-80 seconds (runs twice)
- `test_warmup_without_natural_navigation`: ~20-30 seconds
- `test_browser_state_helper_methods`: <1 second (no browser)

**Total:** ~2-3 minutes for all tests

## Troubleshooting

### Test Skipped?
```
SKIPPED [1] Set LV_WARMUP_TEST_ENABLE=1 to run browser warmup test
```

**Solution:** Set the environment variable first:
```cmd
set LV_WARMUP_TEST_ENABLE=1
```

### Browser Not Found?
```
Error: Playwright browsers not installed
```

**Solution:** Install Playwright browsers:
```cmd
python -m playwright install chromium
```

### State Files Not Cleaned Up?
If `browser_states/` directory persists after tests, manually delete:
```cmd
rmdir /s /q browser_states
```

## Cleanup

Tests automatically clean up `browser_states/` directory before and after running.

To manually clean:
```cmd
rmdir /s /q browser_states
```

## Notes

- Tests use **Court 1** by default (fastest initialization)
- Browser runs in **non-headless mode** to observe behavior
- State files are saved to `browser_states/court_N_state.json`
- Natural navigation must be enabled for warmup to occur
- Tests are **isolated** - each creates fresh browser pool
