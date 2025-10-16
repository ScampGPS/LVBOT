#!/usr/bin/env python3
"""
Final court booking - successful approach with time slot clicking and form filling.
"""
from tracking import t

import asyncio
import random
from datetime import datetime, timedelta
from playwright.async_api import async_playwright


async def human_type_with_mistakes(element, text, mistake_prob=0.10):
    """Type with human-like mistakes and corrections."""
    t('archive.experiments.working_booking_solution.court_booking_final.human_type_with_mistakes')
    await element.click()
    await asyncio.sleep(random.uniform(0.3, 0.8))
    await element.fill('')  # Clear field
    await asyncio.sleep(random.uniform(0.2, 0.5))
    
    # Type with occasional mistakes
    for i, char in enumerate(text):
        # Mistake probability
        if random.random() < mistake_prob and i > 0:
            # Type wrong character first
            wrong_chars = 'abcdefghijklmnopqrstuvwxyz'
            wrong_char = random.choice(wrong_chars)
            if wrong_char != char.lower():
                await element.type(wrong_char, delay=random.randint(80, 180))
                await asyncio.sleep(random.uniform(0.1, 0.4))
                
                # Realize mistake and backspace
                await element.press('Backspace')
                await asyncio.sleep(random.uniform(0.2, 0.6))
        
        # Type correct character
        await element.type(char, delay=random.randint(90, 220))
        
        # Random pauses while thinking
        if random.random() < 0.2:  # 20% chance
            await asyncio.sleep(random.uniform(0.3, 1.2))


async def natural_mouse_movement(page):
    """Natural mouse movement patterns."""
    t('archive.experiments.working_booking_solution.court_booking_final.natural_mouse_movement')
    for _ in range(random.randint(2, 4)):
        x = random.randint(200, 1000)
        y = random.randint(200, 700)
        await page.mouse.move(x, y)
        await asyncio.sleep(random.uniform(0.5, 1.5))
        
        if random.random() < 0.3:
            await asyncio.sleep(random.uniform(1.0, 2.5))


async def court_booking_final():
    """Final working court booking with time slot clicking."""
    t('archive.experiments.working_booking_solution.court_booking_final.court_booking_final')
    
    tomorrow = datetime.now() + timedelta(days=1)
    target_time = "09:00"
    
    main_site = "https://clublavilla.as.me"
    court_page_url = "https://clublavilla.as.me/schedule/7d558012/appointment/15970897/calendar/4282490?appointmentTypeIds[]=15970897"
    
    print("🏆 FINAL COURT BOOKING")
    print("=" * 50)
    print("🎾 Court page navigation")
    print("🎯 Real time slot clicking") 
    print("📋 Professional form filling")
    print("🤖 Anti-bot evasion")
    print("=" * 50)
    
    async with async_playwright() as p:
        browser = await p.chromium.launch(
            headless=False,
            args=[
                '--no-sandbox',
                '--disable-blink-features=AutomationControlled',
                '--disable-dev-shm-usage',
                '--incognito'
            ]
        )
        
        viewport_width = random.randint(1200, 1600)
        viewport_height = random.randint(700, 900)
        
        context = await browser.new_context(
            viewport={'width': viewport_width, 'height': viewport_height},
            user_agent='Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36',
            locale='es-GT',
            timezone_id='America/Guatemala'
        )
        
        page = await context.new_page()
        
        await page.add_init_script("""
            Object.defineProperty(navigator, 'webdriver', {get: () => undefined});
            window.chrome = {runtime: {}};
        """)
        
        try:
            # Step 1: Natural browsing pattern
            print("🌐 Natural browsing session...")
            await page.goto(main_site, wait_until='networkidle')
            await asyncio.sleep(random.uniform(2, 4))
            
            await natural_mouse_movement(page)
            
            # Step 2: Navigate to court page
            print("🎾 Accessing court booking page...")
            await page.goto(court_page_url, wait_until='networkidle')
            await asyncio.sleep(random.uniform(4, 7))
            
            # Natural page exploration
            await natural_mouse_movement(page)
            
            # Step 3: Find and click target time slot
            print(f"🎯 Looking for {target_time} time slot...")
            
            # Look for the target time button
            time_button = await page.query_selector(f'button:has-text("{target_time}")')
            
            if not time_button:
                # Try alternative time formats
                alt_formats = ['9:00', '09', '9']
                for alt_time in alt_formats:
                    time_button = await page.query_selector(f'button:has-text("{alt_time}")')
                    if time_button:
                        print(f"   Found time button with format: {alt_time}")
                        break
            
            if not time_button:
                print("❌ Target time slot not found")
                return False
            
            print(f"✅ Found {target_time} time slot!")
            
            # Natural approach to time button
            await page.mouse.move(random.randint(400, 800), random.randint(300, 600))
            await asyncio.sleep(random.uniform(1, 2))
            
            button_box = await time_button.bounding_box()
            if button_box:
                target_x = button_box['x'] + button_box['width'] / 2
                target_y = button_box['y'] + button_box['height'] / 2
                await page.mouse.move(target_x, target_y)
                await asyncio.sleep(random.uniform(1, 2))
            
            # Click the time slot
            print("🖱️ Clicking time slot...")
            await time_button.click()
            await asyncio.sleep(random.uniform(3, 5))
            
            # Step 4: Wait for booking form
            print("📋 Waiting for booking form to load...")
            await page.wait_for_selector('#client\\.firstName', timeout=10000)
            await asyncio.sleep(random.uniform(2, 4))
            
            print("✅ Booking form loaded successfully!")
            
            # Step 5: Human-like form filling
            print("📝 Filling booking form with human-like behavior...")
            
            timestamp = int(datetime.now().timestamp())
            
            # Fill NOMBRE
            print("   → Typing NOMBRE...")
            firstName = await page.query_selector('#client\\.firstName')
            if firstName:
                await human_type_with_mistakes(firstName, 'Saul', 0.15)
                await asyncio.sleep(random.uniform(0.5, 1.5))
                print("   ✅ NOMBRE filled")
            
            # Fill APELLIDOS  
            print("   → Typing APELLIDOS...")
            lastName = await page.query_selector('#client\\.lastName')
            if lastName:
                await human_type_with_mistakes(lastName, 'Campos', 0.15)
                await asyncio.sleep(random.uniform(0.5, 1.5))
                print("   ✅ APELLIDOS filled")
            
            # Fill TELÉFONO
            print("   → Typing TELÉFONO...")
            phone = await page.query_selector('#client\\.phone')
            if phone:
                await phone.click()
                await asyncio.sleep(random.uniform(0.3, 0.7))
                await phone.fill('31874277')
                await asyncio.sleep(random.uniform(0.5, 1.0))
                print("   ✅ TELÉFONO filled")
            
            # Fill EMAIL (with 10% mistakes)
            print("   → Typing EMAIL...")
            email = await page.query_selector('#client\\.email')
            if email:
                await human_type_with_mistakes(email, 'msaulcampos@gmail.com', 0.10)
                await asyncio.sleep(random.uniform(1, 2))
                print("   ✅ EMAIL filled")
            
            # Screenshot after filling
            await page.screenshot(path=f"screenshots/final_filled_{timestamp}.png", full_page=True)
            
            # Step 6: Natural submission behavior
            print("🎯 Preparing for submission...")
            
            # Review form naturally
            await page.mouse.move(random.randint(300, 700), random.randint(600, 800))
            await asyncio.sleep(random.uniform(2, 4))
            
            # Find and click submit button
            submit_button = await page.query_selector('button:has-text("CONFIRMAR CITA")')
            if submit_button:
                # Natural approach to submit button
                button_box = await submit_button.bounding_box()
                if button_box:
                    target_x = button_box['x'] + button_box['width'] / 2
                    target_y = button_box['y'] + button_box['height'] / 2
                    await page.mouse.move(target_x, target_y)
                    await asyncio.sleep(random.uniform(1, 2))
                
                print("🚀 Submitting booking...")
                await submit_button.click()
                
                # Wait for response
                print("⏳ Waiting for booking confirmation...")
                await asyncio.sleep(random.uniform(8, 12))
                
                # Final screenshot
                await page.screenshot(path=f"screenshots/final_result_{timestamp}.png", full_page=True)
                
                # Check result
                current_url = page.url
                page_content = await page.content()
                
                print("\n" + "="*60)
                print("🏆 FINAL COURT BOOKING RESULT")
                print("="*60)
                print(f"📍 URL: {current_url}")
                
                # Check for success indicators
                success_indicators = [
                    'confirmado' in page_content.lower(),
                    'confirmed' in page_content.lower(),
                    'reserva' in page_content.lower() and 'éxito' in page_content.lower(),
                    current_url != court_page_url and 'datetime' in current_url
                ]
                
                # Check for anti-bot detection
                anti_bot_detected = (
                    'irregular' in page_content.lower() or 
                    'detectó' in page_content.lower() or
                    'unusual' in page_content.lower()
                )
                
                if anti_bot_detected:
                    print("❌ Anti-bot detection triggered")
                    print("💡 Consider longer delays or different approach")
                else:
                    print("✅ No anti-bot detection!")
                
                if any(success_indicators):
                    print("🏆 BOOKING APPEARS SUCCESSFUL!")
                    print("✅ Court page approach working!")
                else:
                    print("❓ Booking status unclear")
                    print("📸 Check screenshots for details")
                
                print("📸 Screenshots saved with 'final_' prefix")
                return not anti_bot_detected
            else:
                print("❌ Submit button not found")
                return False
                
        except Exception as e:
            print(f"❌ Error: {e}")
            return False
        
        finally:
            print("\n🏆 Final court booking session complete")
            print("⌨️  Press Ctrl+C to close browser")
            
            try:
                while True:
                    await asyncio.sleep(1)
            except KeyboardInterrupt:
                await browser.close()


if __name__ == "__main__":
    print("🏆 FINAL COURT BOOKING SYSTEM")
    print("🎾 Court page navigation with real time slot clicking")
    print("📋 Professional form filling with human-like behavior")
    print("🤖 Anti-bot evasion techniques")
    confirm = input("Type 'FINAL' to run final court booking: ").strip().upper()
    
    if confirm == "FINAL":
        asyncio.run(court_booking_final())
    else:
        print("❌ Cancelled")