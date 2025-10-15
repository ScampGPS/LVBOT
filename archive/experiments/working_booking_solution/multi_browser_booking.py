#!/usr/bin/env python3
"""
Multi-browser safe booking - optimized for environments with 3+ concurrent browsers.
"""

import asyncio
import random
import time
import psutil
from datetime import datetime, timedelta
from playwright.async_api import async_playwright


class BrowserResourceManager:
    """Manages browser resources in multi-browser environments."""
    
    @staticmethod
    def get_system_load():
        """Check current system resource usage."""
        cpu_percent = psutil.cpu_percent(interval=1)
        memory = psutil.virtual_memory()
        return {
            'cpu_percent': cpu_percent,
            'memory_percent': memory.percent,
            'available_memory_gb': memory.available / (1024**3)
        }
    
    @staticmethod
    def should_delay_for_resources():
        """Determine if we should delay due to high resource usage."""
        load = BrowserResourceManager.get_system_load()
        
        # Delay if system is under heavy load
        if load['cpu_percent'] > 80 or load['memory_percent'] > 85:
            return True, f"High resource usage: CPU {load['cpu_percent']}%, Memory {load['memory_percent']}%"
        
        return False, "Resources available"


async def staggered_delay(min_seconds=3, max_seconds=8):
    """Create staggered delays to avoid simultaneous actions."""
    # Add extra randomization for multi-browser environments
    base_delay = random.uniform(min_seconds, max_seconds)
    
    # Add process-specific offset based on current time
    time_offset = (int(time.time()) % 10) * 0.5
    
    total_delay = base_delay + time_offset
    await asyncio.sleep(total_delay)


async def cautious_navigation(page, url, wait_time=None):
    """Navigate with extra caution for multi-browser environments."""
    print(f"   Navigating to: {url[:50]}...")
    
    # Check system resources before navigation
    resource_mgr = BrowserResourceManager()
    should_delay, reason = resource_mgr.should_delay_for_resources()
    
    if should_delay:
        print(f"   ⏳ Waiting for resources: {reason}")
        await asyncio.sleep(random.uniform(5, 10))
    
    # Navigate with retry logic
    for attempt in range(3):
        try:
            await page.goto(url, wait_until='networkidle', timeout=30000)
            break
        except Exception as e:
            if attempt < 2:
                print(f"   ⚠️ Navigation attempt {attempt + 1} failed, retrying...")
                await asyncio.sleep(random.uniform(3, 6))
            else:
                raise e
    
    # Post-navigation delay
    if wait_time:
        await asyncio.sleep(wait_time)
    else:
        await staggered_delay(4, 8)


async def multi_browser_safe_booking():
    """Booking optimized for multi-browser environments."""
    
    tomorrow = datetime.now() + timedelta(days=1)
    target_time = "09:00"
    
    main_site = "https://clublavilla.as.me"
    court_page_url = "https://clublavilla.as.me/schedule/7d558012/appointment/15970897/calendar/4282490?appointmentTypeIds[]=15970897"
    
    print("🔒 MULTI-BROWSER SAFE BOOKING")
    print("=" * 50)
    print("🎾 Optimized for concurrent browser environments")
    print("⚡ Resource-aware execution")
    print("🛡️ Anti-detection with staggered timing")
    print("=" * 50)
    
    # Check initial system state
    resource_mgr = BrowserResourceManager()
    load = resource_mgr.get_system_load()
    print(f"💻 System load: CPU {load['cpu_percent']}%, Memory {load['memory_percent']}%")
    
    async with async_playwright() as p:
        # Use more conservative browser settings for multi-browser env
        browser_args = [
            '--no-sandbox',
            '--disable-dev-shm-usage',
            '--disable-extensions',
            '--disable-plugins',
            '--disable-images',  # Reduce bandwidth usage
            '--disable-javascript-harmony-shipping',
            '--memory-pressure-off',  # Reduce memory pressure
            '--max_old_space_size=512',  # Limit memory usage
            '--incognito'
        ]
        
        browser = await p.chromium.launch(
            headless=False,
            args=browser_args
        )
        
        # Smaller viewport to reduce memory usage
        viewport_width = random.randint(1024, 1200)  # Smaller than before
        viewport_height = random.randint(600, 768)
        
        context = await browser.new_context(
            viewport={'width': viewport_width, 'height': viewport_height},
            user_agent='Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36',
            locale='es-GT',
            timezone_id='America/Guatemala'
        )
        
        page = await context.new_page()
        
        # Enhanced stealth for multi-browser detection
        await page.add_init_script("""
            Object.defineProperty(navigator, 'webdriver', {get: () => undefined});
            window.chrome = {runtime: {}};
            Object.defineProperty(navigator, 'plugins', {get: () => [1, 2, 3, 4, 5]});
            
            // Add unique fingerprint to differentiate from other browsers
            window.uniqueId = Math.random().toString(36).substring(7);
        """)
        
        try:
            # Step 1: Extended pre-browsing with resource awareness
            print("🌐 Conservative browsing session...")
            await cautious_navigation(page, main_site)
            
            # Longer initial delay for multi-browser safety
            print("   ⏳ Extended initial delay for multi-browser safety...")
            await staggered_delay(8, 15)
            
            # Step 2: Court page access with staggered timing
            print("🎾 Accessing court page with staggered timing...")
            await cautious_navigation(page, court_page_url)
            
            # Extra delay before time slot interaction
            print("   ⏳ Waiting before time slot interaction...")
            await staggered_delay(6, 12)
            
            # Step 3: Find time slot with multiple attempts
            print(f"🎯 Searching for {target_time} time slot...")
            
            time_button = None
            for attempt in range(5):  # More attempts
                try:
                    time_button = await page.query_selector(f'button:has-text("{target_time}")')
                    if time_button:
                        break
                    
                    # Try alternative formats
                    for alt_time in ['9:00', '09', '9']:
                        time_button = await page.query_selector(f'button:has-text("{alt_time}")')
                        if time_button:
                            break
                    
                    if time_button:
                        break
                        
                    print(f"   ⏳ Time slot search attempt {attempt + 1}/5...")
                    await asyncio.sleep(random.uniform(2, 4))
                    
                except Exception as e:
                    print(f"   ⚠️ Search attempt failed: {e}")
                    await asyncio.sleep(random.uniform(3, 6))
            
            if not time_button:
                print("❌ Target time slot not found after multiple attempts")
                return False
            
            print(f"✅ Found {target_time} time slot!")
            
            # Step 4: Ultra-conservative time slot clicking
            print("🖱️ Ultra-conservative time slot clicking...")
            
            # Pre-click system check
            should_delay, reason = resource_mgr.should_delay_for_resources()
            if should_delay:
                print(f"   ⏳ Resource check: {reason}")
                await asyncio.sleep(random.uniform(5, 10))
            
            # Natural mouse approach with extra caution
            await page.mouse.move(random.randint(300, 700), random.randint(200, 500))
            await staggered_delay(2, 4)
            
            button_box = await time_button.bounding_box()
            if button_box:
                target_x = button_box['x'] + button_box['width'] / 2
                target_y = button_box['y'] + button_box['height'] / 2
                
                # Multi-stage mouse movement
                current_x, current_y = 500, 400
                for i in range(3):
                    intermediate_x = current_x + (target_x - current_x) * (i + 1) / 3
                    intermediate_y = current_y + (target_y - current_y) * (i + 1) / 3
                    await page.mouse.move(intermediate_x, intermediate_y)
                    await asyncio.sleep(random.uniform(0.8, 1.5))
            
            # Final pre-click pause
            await staggered_delay(2, 5)
            
            await time_button.click()
            print("✅ Time slot clicked!")
            
            # Step 5: Patient form waiting
            print("📋 Patient form waiting...")
            await staggered_delay(5, 10)
            
            try:
                await page.wait_for_selector('#client\\.firstName', timeout=15000)
                print("✅ Form detected!")
            except:
                print("⚠️ Form detection timeout, continuing...")
            
            # Step 6: Conservative form filling
            print("📝 Conservative form filling...")
            
            timestamp = int(datetime.now().timestamp())
            
            # Fill fields with extra delays between each
            fields = [
                ('#client\\.firstName', 'Saul'),
                ('#client\\.lastName', 'Campos'), 
                ('#client\\.phone', '31874277'),
                ('#client\\.email', 'msaulcampos@gmail.com')
            ]
            
            for selector, value in fields:
                try:
                    element = await page.query_selector(selector)
                    if element:
                        await element.click()
                        await staggered_delay(1, 2)
                        await element.fill('')
                        await asyncio.sleep(random.uniform(0.3, 0.7))
                        await element.fill(value)
                        await staggered_delay(1, 3)  # Extra delay between fields
                        print(f"   ✅ Filled {selector}")
                except Exception as e:
                    print(f"   ⚠️ Error filling {selector}: {e}")
            
            # Screenshot
            await page.screenshot(path=f"multi_browser_filled_{timestamp}.png", full_page=True)
            
            # Step 7: Ultra-careful submission
            print("🎯 Ultra-careful submission preparation...")
            await staggered_delay(5, 10)
            
            submit_button = await page.query_selector('button:has-text("CONFIRMAR CITA")')
            if submit_button:
                # Final resource check
                should_delay, reason = resource_mgr.should_delay_for_resources()
                if should_delay:
                    print(f"   ⏳ Final resource check: {reason}")
                    await asyncio.sleep(random.uniform(5, 10))
                
                print("🚀 Submitting with maximum caution...")
                await submit_button.click()
                
                # Extended wait for response
                await staggered_delay(10, 20)
                
                # Final screenshot
                await page.screenshot(path=f"multi_browser_result_{timestamp}.png", full_page=True)
                
                current_url = page.url
                page_content = await page.content()
                
                print("\n" + "="*60)
                print("🔒 MULTI-BROWSER SAFE BOOKING RESULT")
                print("="*60)
                print(f"📍 URL: {current_url}")
                
                # Enhanced success detection
                success_indicators = [
                    'confirmado' in page_content.lower(),
                    'confirmed' in page_content.lower(),
                    'reserva' in page_content.lower(),
                    current_url != court_page_url
                ]
                
                anti_bot_detected = (
                    'irregular' in page_content.lower() or 
                    'detectó' in page_content.lower()
                )
                
                if anti_bot_detected:
                    print("❌ Anti-bot detection despite multi-browser precautions")
                else:
                    print("✅ No anti-bot detection - multi-browser approach successful!")
                
                if any(success_indicators):
                    print("🏆 BOOKING SUCCESSFUL!")
                    print("✅ Multi-browser environment handled properly!")
                else:
                    print("❓ Booking status unclear")
                
                print(f"📸 Screenshots: multi_browser_filled_{timestamp}.png, multi_browser_result_{timestamp}.png")
                return not anti_bot_detected
            else:
                print("❌ Submit button not found")
                return False
                
        except Exception as e:
            print(f"❌ Multi-browser booking error: {e}")
            return False
        
        finally:
            print("\n🔒 Multi-browser safe session complete")
            print("⌨️  Press Ctrl+C to close browser")
            
            try:
                while True:
                    await asyncio.sleep(1)
            except KeyboardInterrupt:
                await browser.close()


if __name__ == "__main__":
    print("🔒 MULTI-BROWSER SAFE BOOKING SYSTEM")
    print("🎾 Optimized for environments with 3+ concurrent browsers")
    print("💻 Resource-aware execution with anti-detection")
    confirm = input("Type 'MULTI' to run multi-browser safe booking: ").strip().upper()
    
    if confirm == "MULTI":
        asyncio.run(multi_browser_safe_booking())
    else:
        print("❌ Cancelled")