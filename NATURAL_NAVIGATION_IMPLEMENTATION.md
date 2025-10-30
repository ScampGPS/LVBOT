# Natural Navigation Implementation

## Summary
Successfully implemented natural navigation for reserved bookings to evade Acuity's anti-bot detection.

## What Was Implemented

### 1. Core Functionality (`automation/browser/pool/manager.py`)
- Added `enable_natural_navigation()` method to BrowserPoolManager
- When enabled, browsers now:
  1. Navigate to main site first (`https://clublavilla.as.me`)
  2. Wait 2-4 seconds with natural mouse movements
  3. Then navigate to the court booking page
- **Default:** Disabled (backward compatible)

### 2. Browser Pool Integration (`automation/browser/async_browser_pool.py`)
- Added `enable_natural_navigation()` method to AsyncBrowserPool
- Provides easy access to enable/disable the feature

### 3. Reserved Bookings Integration (`reservations/queue/reservation_scheduler.py`)
- Automatically enables natural navigation for ALL reserved bookings
- Applied to both `run_async()` and `start()` methods
- Logs: "Enabling natural navigation for reserved bookings"

## Key Features

### Backward Compatibility
- **Default behavior:** Direct navigation (unchanged)
- **Opt-in:** Must be explicitly enabled
- **No impact on immediate bookings** - they still use direct navigation for speed

### Anti-Bot Evasion
Based on the original working version:
- Mimics real user browsing pattern
- Adds natural delays and mouse movements
- Makes session appear human before attempting booking

## How It Works

1. **Reserved Booking Starts** → ReservationScheduler initializes
2. **Browser Pool Created** → Each court gets a browser
3. **Natural Navigation Enabled** → `browser_pool.enable_natural_navigation(True)`
4. **Each Browser:**
   - Goes to main site
   - Waits 2-4 seconds
   - Performs 1-3 random mouse movements
   - Navigates to court page
   - Ready for booking

## Testing

### 1. Test Reserved Booking
```bash
# Queue a reservation and watch the logs
# You should see:
# - "Natural navigation enabled - will visit main site before court pages"
# - "Court X: Natural navigation - visiting main site first"
# - "Court X: Now navigating to court page"
```

### 2. Smoke Test
```bash
LV_SMOKE_ENABLE=1 python -m pytest tests/bot/test_full_smoke_playwright.py
```

### 3. Monitor Results
- Check `logs/latest_log/booking_artifacts/` for CAPTCHA presence
- Look for "Se detectó un uso irregular del sitio" message
- If still blocked, consider additional measures from BOOKING_VERSION_ANALYSIS.md

## Configuration

### Enable for Specific Use Cases
```python
# For any browser pool instance
browser_pool.enable_natural_navigation(True)  # Enable
browser_pool.enable_natural_navigation(False) # Disable
```

### Environment Variable (Optional)
Could add `LV_NATURAL_NAVIGATION=true/false` environment variable if needed for runtime control.

## Next Steps if Still Blocked

1. **Reduce Speed Multiplier**
   - Edit `automation/executors/flows/natural_flow.py`
   - Change `WORKING_SPEED_MULTIPLIER = 2.5` to `1.0`

2. **Sequential Court Attempts**
   - Modify AsyncBookingExecutor to try courts one by one
   - Add delays between attempts

3. **Extended Natural Browsing**
   - Click on some links on main page
   - Scroll the page
   - Spend more time before navigation

## Files Modified
1. `automation/browser/pool/manager.py` - Added natural navigation logic
2. `automation/browser/async_browser_pool.py` - Added enable method
3. `reservations/queue/reservation_scheduler.py` - Auto-enable for reserved bookings

## Rollback Instructions
If needed, the feature can be disabled without any code changes:
```python
# In reservation_scheduler.py, comment out or set to False:
self.browser_pool.enable_natural_navigation(False)  # or just remove the line
```

The default behavior is direct navigation, so removing the enable call reverts to original behavior.