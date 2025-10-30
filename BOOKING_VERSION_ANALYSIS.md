# LVBOT Booking Automation Version Analysis

## Summary
Analysis of multiple booking executor versions from the initial git commit to identify the working approach that successfully bypassed Acuity's anti-bot detection.

## Key Finding
The original `court_booking_final.py` from the `working_booking_solution/` directory appears to be the proven working version.

## Version Comparison

### 1. court_booking_final.py (ORIGINAL WORKING VERSION)
**File:** `working_booking_solution/court_booking_final.py`
**Lines:** 296
**Key Characteristics:**
- **Speed:** No speed multiplier, uses raw delays
- **Typing delays:** 80-220ms per character
- **Mistakes:** 10% probability with backspace corrections
- **Mouse:** Natural movements with 2-4 random moves, 0.5-1.5s delays
- **Browser config:**
  - `--disable-blink-features=AutomationControlled`
  - Custom user agent
  - Random viewport (1200-1600 x 700-900)
  - Locale: es-GT, Timezone: America/Guatemala
- **JavaScript injection:** Hides webdriver property
- **Initial delay:** 2-4 seconds
- **Form approach:** Natural browsing pattern before accessing court page

### 2. working_booking_executor.py (Adapted from original)
**File:** `utils/working_booking_executor.py`
**Lines:** 325
**Key Characteristics:**
- **Speed:** SPEED_MULTIPLIER = 2.5 (faster than original)
- **Typing delays:** 90-220ms base, divided by speed multiplier
- **Mistakes:** 10-15% probability
- **Initial delay:** 3-5 seconds (configurable)
- **Note:** "Based on proven court_booking_final.py - DO NOT CHANGE THE CORE LOGIC"

### 3. experienced_booking_executor.py
**File:** `utils/experienced_booking_executor.py`
**Lines:** 534
**Key Characteristics:**
- **Speed:** SPEED_MULTIPLIER = 3.0 (even faster)
- **Typing:** Simplified - just click, clear, fill (NO HUMAN-LIKE TYPING)
- **Minimal delays:** 0.05-0.1s
- **Focus:** Speed over human-likeness

### 4. smart_async_booking_executor.py
**File:** `utils/smart_async_booking_executor.py`
**Lines:** 654
**Key Characteristics:**
- **Complex timeout management**
- **Smart retry logic**
- **Multiple fallback strategies**
- **Focus on reliability over stealth**

### 5. optimized_booking_executor.py
**File:** `optimized_booking_executor.py`
**Lines:** 307
**Key Characteristics:**
- **Speed:** SPEED_MULTIPLIER = 2.5, TYPING_SPEED_MULTIPLIER = 3.5
- **Reduced mistakes:** 5% probability
- **Minimal mouse movements:** 1 movement
- **Faster typing:** 30-60ms base delay

### 6. Current Version (automation/executors/flows/natural_flow.py)
**Key Characteristics:**
- **Speed:** WORKING_SPEED_MULTIPLIER = 2.5
- **Sophisticated mouse:** Bezier curve movements
- **Advanced typing:** 12% mistake probability
- **Human behaviors:** Centralized in HumanLikeActions class
- **Browser config:** Has anti-detection settings

## Critical Differences

### What the ORIGINAL WORKING version had:
1. **SLOWER, MORE HUMAN-LIKE TIMING**
   - No speed multiplier
   - Raw delays of 80-220ms per keystroke
   - Longer pauses between actions

2. **SIMPLER MOUSE MOVEMENTS**
   - Basic random movements
   - No complex curves

3. **NATURAL BROWSING PATTERN**
   - Visits main site first
   - Natural exploration before booking

4. **COMPLETE STEALTH SETUP**
   - Browser args: `--disable-blink-features=AutomationControlled`
   - JavaScript injection to hide webdriver
   - Random viewport sizes
   - Proper locale/timezone

### What might be triggering detection NOW:

1. **SPEED MULTIPLIERS**
   - Current versions divide all delays by 2.5-3.5x
   - Makes actions too fast to be human

2. **PARALLEL BOOKING ATTEMPTS**
   - Current AsyncBookingExecutor tries all courts simultaneously
   - Original did sequential attempts

3. **OVERLY SOPHISTICATED PATTERNS**
   - Bezier curve mouse movements might be TOO perfect
   - Could be a signature of automation

4. **MISSING NATURAL BROWSING**
   - Current version goes directly to court page
   - Original visited main site first

## Recommended Solution

### Option 1: Restore Original Timing (Most Likely to Work)
1. Remove all speed multipliers (set to 1.0)
2. Use original delay values:
   - Typing: 80-220ms per character
   - Mouse moves: 0.5-1.5s between movements
   - Form field delays: 0.5-1.5s
3. Add initial site visit before court page

### Option 2: Sequential Court Attempts
1. Modify AsyncBookingExecutor to try courts one by one
2. Add 5-10 second delays between court attempts
3. Randomize court order

### Option 3: Simplify Mouse Movements
1. Replace Bezier curves with simple random movements
2. Reduce movement frequency
3. Add more random pauses

### Option 4: Full Restoration
1. Use the exact `court_booking_final.py` logic
2. Only adapt the minimum needed for LVBOT integration
3. Keep all original delays and patterns

## Implementation Priority
1. **First:** Remove speed multipliers (quick fix)
2. **Second:** Switch to sequential booking
3. **Third:** Restore natural browsing pattern
4. **Fourth:** If still failing, use exact original implementation

## Testing Strategy
1. Test with LV_SMOKE_ENABLE=1 for single court
2. Monitor logs/latest_log/booking_artifacts/ for CAPTCHA appearance
3. Compare timing logs between versions
4. Use video recording to verify human-like appearance