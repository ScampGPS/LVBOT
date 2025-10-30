# Anti-Bot Detection Strategies for Acuity Scheduling (2025)

## Current Status
### ✅ Implemented:
- ✅ Natural navigation working (visiting main site first)
- ✅ Speed multiplier reduced to 1.0 (human speed)
- ✅ **Solution 1: Enhanced Browser Fingerprinting** (18 anti-detection measures)
  - Added realistic plugins, languages, hardware properties
  - Canvas & WebGL fingerprint masking
  - Enhanced HTTP headers (Chrome 131)
  - Complete navigator property spoofing
- ✅ **Solution 2: Enhanced Mouse & Behavioral Patterns** (Modular implementation)
  - Scrolling behavior (2-4 actions with random scroll-back)
  - Hesitant clicking (move near → corrections → click)
  - Reading pauses (2-4 seconds)
  - Natural page interaction wrapper method
  - Configurable via `ENABLE_ENHANCED_BEHAVIORS` flag

### 📊 Results:
- ❌ Still getting "Irregular usage warning encountered" (last test before Solutions 1 & 2)
- Total booking time: ~37 seconds base (will be 50-60s with enhanced behaviors)
- **Next:** Test with both stealth + behavioral enhancements

## Research Findings

Acuity likely uses **reCAPTCHA v3** (invisible CAPTCHA) which:
- Analyzes behavioral patterns (mouse movements, timing, scrolling)
- Checks browser fingerprinting (Canvas, WebGL, navigator properties)
- Generates a risk score (0.0-1.0) based on "human-likeness"
- Blocks if score < 0.5 (bot-like behavior)

---

## 4 Recommended Solutions (Ranked by Implementation Difficulty)

### 🥇 Solution 1: Enhanced Browser Fingerprinting & Stealth ✅ **IMPLEMENTED**
**Difficulty:** Easy | **Impact:** High | **Time:** 1-2 hours

**Problem:** Playwright automation is detectable through:
- `navigator.webdriver = true` (we already mask this, but may not be complete)
- Canvas/WebGL fingerprinting inconsistencies
- Missing browser properties (plugins, permissions, chrome object)
- Headless browser detection signals

**Implementation:**
```bash
# Install playwright-stealth or playwright-extra
pip install playwright-stealth
# OR use JavaScript version with CDP
```

**Code Changes:**
1. Add more stealth properties:
```python
await page.add_init_script("""
    // Existing stealth
    Object.defineProperty(navigator, 'webdriver', {get: () => undefined});
    window.chrome = {runtime: {}};

    // ADD THESE:
    // 1. Fix plugins
    Object.defineProperty(navigator, 'plugins', {
        get: () => [1, 2, 3, 4, 5].map(i => ({
            description: 'Portable Document Format',
            filename: 'internal-pdf-viewer',
            length: 1,
            name: 'PDF Viewer'
        }))
    });

    // 2. Fix languages
    Object.defineProperty(navigator, 'languages', {
        get: () => ['es-GT', 'es', 'en-US', 'en']
    });

    // 3. Fix platform
    Object.defineProperty(navigator, 'platform', {
        get: () => 'Win32'
    });

    // 4. Mask headless
    Object.defineProperty(navigator, 'hardwareConcurrency', {
        get: () => 8
    });

    // 5. Canvas fingerprint randomization
    const originalToDataURL = HTMLCanvasElement.prototype.toDataURL;
    HTMLCanvasElement.prototype.toDataURL = function(type) {
        const shift = Math.floor(Math.random() * 10) - 5;
        const context = this.getContext('2d');
        const imageData = context.getImageData(0, 0, this.width, this.height);
        for (let i = 0; i < imageData.data.length; i += 4) {
            imageData.data[i] = imageData.data[i] + shift;
        }
        context.putImageData(imageData, 0, 0);
        return originalToDataURL.apply(this, arguments);
    };
""")
```

2. Add more realistic headers:
```python
context = await browser.new_context(
    viewport={'width': 1920, 'height': 1080},
    user_agent='Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/131.0.0.0 Safari/537.36',
    locale='es-GT',
    timezone_id='America/Guatemala',
    extra_http_headers={
        'Accept': 'text/html,application/xhtml+xml,application/xml;q=0.9,image/avif,image/webp,*/*;q=0.8',
        'Accept-Language': 'es-GT,es;q=0.9,en-US;q=0.8,en;q=0.7',
        'Accept-Encoding': 'gzip, deflate, br',
        'DNT': '1',
        'Connection': 'keep-alive',
        'Upgrade-Insecure-Requests': '1',
        'Sec-Fetch-Dest': 'document',
        'Sec-Fetch-Mode': 'navigate',
        'Sec-Fetch-Site': 'none',
        'Sec-Fetch-User': '?1',
        'Cache-Control': 'max-age=0',
    }
)
```

**Expected Result:** Reduces fingerprinting detection by 60-80%

---

### 🥈 Solution 2: Enhanced Mouse & Behavioral Patterns ✅ **IMPLEMENTED**
**Difficulty:** Medium | **Impact:** Medium-High | **Time:** 2-3 hours

**Problem:** Current mouse movements may still look robotic
- reCAPTCHA v3 analyzes mouse trajectory speed, acceleration, curves
- Current implementation may have predictable patterns

**Implementation:**

1. **Add scroll behavior:**
```python
async def natural_page_interaction(page):
    """More realistic page interaction before booking"""
    # Random scrolling
    for _ in range(random.randint(2, 4)):
        scroll_amount = random.randint(100, 400)
        await page.mouse.wheel(0, scroll_amount)
        await asyncio.sleep(random.uniform(0.8, 1.5))

    # Scroll back up sometimes
    if random.random() < 0.3:
        await page.mouse.wheel(0, -random.randint(50, 150))
        await asyncio.sleep(random.uniform(0.5, 1.0))

    # Random pauses (like reading)
    await asyncio.sleep(random.uniform(2.0, 4.0))
```

2. **Add "hesitation" patterns:**
```python
async def hesitant_click(element):
    """Click with human hesitation"""
    # Move near button but not quite there
    box = await element.bounding_box()
    near_x = box['x'] + box['width'] * random.uniform(0.3, 0.7)
    near_y = box['y'] + box['height'] * random.uniform(0.3, 0.7)
    await page.mouse.move(near_x, near_y)
    await asyncio.sleep(random.uniform(0.3, 0.8))

    # Small correction movements (like aiming)
    for _ in range(random.randint(0, 2)):
        adjust_x = near_x + random.uniform(-10, 10)
        adjust_y = near_y + random.uniform(-10, 10)
        await page.mouse.move(adjust_x, adjust_y)
        await asyncio.sleep(random.uniform(0.1, 0.3))

    # Final move to button
    target_x = box['x'] + box['width'] * 0.5
    target_y = box['y'] + box['height'] * 0.5
    await page.mouse.move(target_x, target_y)
    await asyncio.sleep(random.uniform(0.2, 0.5))

    # Click
    await element.click()
```

3. **Add typing patterns with corrections:**
```python
async def human_typing_with_corrections(element, text):
    """Type with realistic mistakes and self-corrections"""
    await element.click()
    await asyncio.sleep(random.uniform(0.5, 1.0))

    typed_so_far = ""
    i = 0
    while i < len(text):
        # Sometimes make a typo
        if random.random() < 0.08 and i > 0:
            # Type wrong character
            wrong_char = random.choice('abcdefghijklmnopqrstuvwxyz')
            await element.type(wrong_char, delay=random.randint(120, 180))
            await asyncio.sleep(random.uniform(0.2, 0.5))
            # Notice mistake and backspace
            await element.press('Backspace')
            await asyncio.sleep(random.uniform(0.3, 0.7))

        # Type correct character
        await element.type(text[i], delay=random.randint(100, 250))

        # Random pauses (thinking)
        if random.random() < 0.15:
            await asyncio.sleep(random.uniform(0.5, 1.5))

        i += 1

    # Small pause after finishing
    await asyncio.sleep(random.uniform(0.8, 1.5))
```

**Expected Result:** Increases reCAPTCHA v3 score by mimicking more realistic human behavior

---

### 🥉 Solution 3: Session Warming & Cookie Persistence
**Difficulty:** Medium | **Impact:** High | **Time:** 3-4 hours

**Problem:** Brand new browser sessions with no history look suspicious
- No cookies from previous visits
- No browsing history
- Fresh fingerprint

**Implementation:**

1. **Pre-warm browser sessions:**
```python
async def warm_browser_session(page):
    """Build up realistic browsing history and cookies"""
    # Visit related sites first
    warming_sites = [
        "https://www.google.com",
        "https://www.google.com/search?q=club+lavilla+tennis",
        "https://clublavilla.as.me",
    ]

    for site in warming_sites:
        await page.goto(site, wait_until='networkidle')
        await asyncio.sleep(random.uniform(3, 6))

        # Interact with page
        await page.mouse.move(
            random.randint(200, 800),
            random.randint(200, 600)
        )
        await asyncio.sleep(random.uniform(1, 2))

        # Scroll
        await page.mouse.wheel(0, random.randint(100, 400))
        await asyncio.sleep(random.uniform(2, 4))
```

2. **Save and reuse browser context:**
```python
# Save cookies and storage state
async def save_browser_state(context, user_id):
    storage = await context.storage_state(path=f"browser_states/{user_id}_state.json")

# Load existing state
context = await browser.new_context(
    storage_state=f"browser_states/{user_id}_state.json"
)
```

3. **Add realistic timing between bookings:**
```python
# Don't book immediately after browser opens
async def realistic_booking_delay():
    # Simulate user navigating to site naturally
    delay = random.uniform(5.0, 15.0)
    logger.info(f"Waiting {delay:.1f}s to appear more natural...")
    await asyncio.sleep(delay)
```

**Expected Result:** Browsers appear to have history/legitimacy, increasing trust score

---

### 🏆 Solution 4: CAPTCHA Solving Service Integration (Last Resort)
**Difficulty:** Easy | **Impact:** Very High | **Time:** 1 hour | **Cost:** ~$1-3/1000 solves

**Problem:** Even with perfect stealth, reCAPTCHA v3 may still block
- Some systems are just too good
- May need human/AI assistance

**Implementation:**

1. **Use 2Captcha or similar service:**
```bash
pip install 2captcha-python
```

2. **Integration code:**
```python
from twocaptcha import TwoCaptcha

async def solve_recaptcha_if_present(page):
    """Detect and solve reCAPTCHA if it appears"""
    # Check if reCAPTCHA is present
    recaptcha_frame = await page.query_selector('iframe[src*="recaptcha"]')

    if recaptcha_frame:
        logger.warning("reCAPTCHA detected, using solving service...")

        # Get site key
        site_key_element = await page.query_selector('[data-sitekey]')
        site_key = await site_key_element.get_attribute('data-sitekey')

        # Solve via 2Captcha
        solver = TwoCaptcha(api_key='YOUR_API_KEY')
        result = solver.recaptcha(
            sitekey=site_key,
            url=page.url
        )

        # Inject solution
        await page.evaluate(f'''
            document.getElementById('g-recaptcha-response').innerHTML = '{result['code']}';
        ''')

        logger.info("reCAPTCHA solved successfully")
        return True

    return False
```

**Services:**
- 2Captcha: $2.99/1000 solves
- Anti-Captcha: Similar pricing
- CapMonster Cloud: $0.50-2/1000

**Expected Result:** 95%+ success rate, but costs money per booking

---

## Recommended Implementation Order

### Phase 1 (Do First - Highest ROI): ✅ **COMPLETE**
1. ✅ Natural navigation (DONE)
2. ✅ Speed multiplier to 1.0 (DONE)
3. ✅ **Solution 1: Enhanced browser fingerprinting** (DONE - 18 measures implemented)
4. ✅ **Solution 2: Better mouse/behavioral patterns** (DONE - Modular HumanLikeActions extension)

### Phase 2 (If Phase 1 Doesn't Work):
5. **Solution 3: Session warming**
6. **Solution 4: CAPTCHA solving service** (if all else fails)

---

## Testing Methodology

1. **Test after each change:**
   ```bash
   LV_SMOKE_ENABLE=1 python -m pytest tests/bot/test_full_smoke_playwright.py
   ```

2. **Check your fingerprint:**
   - Visit: https://pixelscan.net/ or https://bot.sannysoft.com/
   - Compare with real Chrome browser

3. **Monitor detection rate:**
   - Track success/failure ratio
   - Look for improvement trends

---

## Success Metrics

- **Current:** 0% success (100% detected)
- **After Phase 1:** Target 60-80% success
- **After Phase 2:** Target 95%+ success

---

## Important Notes

⚠️ **Legal/Ethical Considerations:**
- Ensure you have authorization to automate bookings
- Respect website terms of service
- Don't use for malicious purposes

⚠️ **Progressive Enhancement:**
- Implement solutions incrementally
- Test each change
- Don't over-engineer if earlier solutions work

⚠️ **Maintenance:**
- Bot detection evolves constantly
- Monitor for new blocking patterns
- Update fingerprinting regularly