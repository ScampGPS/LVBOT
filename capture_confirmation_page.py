#!/usr/bin/env python3
"""
Script to capture confirmation page details after successful booking
"""

import asyncio
import logging
from datetime import datetime, timedelta
from playwright.async_api import async_playwright
import json
import os

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

async def capture_confirmation_page():
    """Navigate to booking form and capture confirmation details after submission"""
    async with async_playwright() as p:
        browser = await p.chromium.launch(
            headless=False,  # Show browser
            slow_mo=500
        )
        page = await browser.new_page()
        
        # Create output directory
        output_dir = "debugging/confirmation_capture"
        os.makedirs(output_dir, exist_ok=True)
        
        # Court URLs
        court_urls = {
            1: "https://clublavilla.as.me/schedule/7d558012/appointment/15970897/calendar/4282490",
            2: "https://clublavilla.as.me/schedule/7d558012/appointment/16021953/calendar/4291312", 
            3: "https://clublavilla.as.me/schedule/7d558012/appointment/16120442/calendar/4307254"
        }
        
        # Test parameters
        court = 2
        target_date = datetime.now() + timedelta(days=1)
        target_time = "20:15"  # Evening time
        
        # Construct direct URL
        date_str = target_date.strftime("%Y-%m-%d")
        appointment_type_id = court_urls[court].split('/')[-2]
        direct_url = f"{court_urls[court]}/datetime/{date_str}T{target_time}:00-06:00?appointmentTypeIds[]={appointment_type_id}"
        
        logger.info(f"Navigating to: {direct_url}")
        
        try:
            # Navigate to form
            await page.goto(direct_url, wait_until='networkidle')
            await page.wait_for_timeout(3000)
            
            # Check for form
            form_present = await page.query_selector('form') is not None
            
            if form_present:
                logger.info("Form found - please complete the booking manually")
                logger.info("I will capture the confirmation page details")
                
                # Monitor for confirmation page
                confirmation_found = False
                check_count = 0
                
                while not confirmation_found and check_count < 300:  # 5 minutes max
                    await page.wait_for_timeout(1000)
                    check_count += 1
                    
                    # Look for confirmation indicators
                    page_text = await page.inner_text('body')
                    
                    if any(phrase in page_text for phrase in [
                        "confirmada",
                        "confirmado", 
                        "Cita confirmada",
                        "está confirmada",
                        "appointment is confirmed"
                    ]):
                        confirmation_found = True
                        logger.info("\n✅ CONFIRMATION PAGE DETECTED!")
                        
                        # Capture all the details
                        confirmation_data = await page.evaluate('''() => {
                            // Get all text content
                            const bodyText = document.body.innerText;
                            
                            // Find all buttons
                            const buttons = [];
                            document.querySelectorAll('button, a[role="button"], a.button').forEach(btn => {
                                if (btn.offsetParent !== null) {
                                    buttons.push({
                                        text: btn.innerText || btn.textContent,
                                        href: btn.href || null,
                                        onclick: btn.onclick ? btn.onclick.toString() : null,
                                        className: btn.className,
                                        id: btn.id,
                                        tagName: btn.tagName
                                    });
                                }
                            });
                            
                            // Find all links
                            const links = [];
                            document.querySelectorAll('a').forEach(link => {
                                if (link.offsetParent !== null && link.href) {
                                    links.push({
                                        text: link.innerText || link.textContent,
                                        href: link.href,
                                        className: link.className,
                                        id: link.id
                                    });
                                }
                            });
                            
                            // Look for cancel/modify links specifically
                            const actionLinks = [];
                            const actionKeywords = ['cancel', 'modify', 'reschedule', 'change', 'cancelar', 'modificar', 'cambiar', 'reprogramar'];
                            
                            [...buttons, ...links].forEach(element => {
                                const text = (element.text || '').toLowerCase();
                                if (actionKeywords.some(keyword => text.includes(keyword))) {
                                    actionLinks.push(element);
                                }
                            });
                            
                            // Get any confirmation codes or IDs
                            const confirmationInfo = {};
                            const patterns = [
                                /confirmation\s*#?\s*:?\s*([A-Z0-9]+)/i,
                                /confirmación\s*#?\s*:?\s*([A-Z0-9]+)/i,
                                /booking\s*id\s*:?\s*([A-Z0-9]+)/i,
                                /reservation\s*#?\s*:?\s*([A-Z0-9]+)/i
                            ];
                            
                            patterns.forEach(pattern => {
                                const match = bodyText.match(pattern);
                                if (match) {
                                    confirmationInfo.confirmationCode = match[1];
                                }
                            });
                            
                            // Get URL
                            confirmationInfo.url = window.location.href;
                            
                            return {
                                pageText: bodyText,
                                buttons: buttons,
                                links: links,
                                actionLinks: actionLinks,
                                confirmationInfo: confirmationInfo,
                                timestamp: new Date().toISOString()
                            };
                        }''')
                        
                        # Take screenshot
                        await page.screenshot(path=f"{output_dir}/confirmation_page.png", full_page=True)
                        
                        # Save data
                        with open(f"{output_dir}/confirmation_data.json", "w", encoding="utf-8") as f:
                            json.dump(confirmation_data, f, indent=2, ensure_ascii=False)
                        
                        # Log findings
                        logger.info(f"\nConfirmation URL: {confirmation_data['confirmationInfo']['url']}")
                        
                        if confirmation_data['actionLinks']:
                            logger.info("\n🔗 Action links found:")
                            for link in confirmation_data['actionLinks']:
                                logger.info(f"  - {link['text']}: {link.get('href', 'No href')}")
                        
                        # Extract specific cancel link if found
                        cancel_links = [
                            link for link in confirmation_data['actionLinks'] 
                            if 'cancel' in link['text'].lower() or 'cancelar' in link['text'].lower()
                        ]
                        
                        if cancel_links:
                            logger.info("\n❌ Cancel link(s) found:")
                            for link in cancel_links:
                                logger.info(f"  URL: {link.get('href')}")
                                
                            # Save cancel link separately
                            with open(f"{output_dir}/cancel_link.json", "w") as f:
                                json.dump({
                                    "cancel_links": cancel_links,
                                    "confirmation_url": confirmation_data['confirmationInfo']['url'],
                                    "captured_at": datetime.now().isoformat()
                                }, f, indent=2)
                        
                        # Look for any email information
                        email_info = await page.evaluate('''() => {
                            const bodyText = document.body.innerText;
                            const emailPatterns = [
                                /enviado.*correo.*a\s+([^\s]+@[^\s]+)/i,
                                /sent.*email.*to\s+([^\s]+@[^\s]+)/i,
                                /confirmación.*enviada.*a\s+([^\s]+@[^\s]+)/i,
                                /recibirás.*correo.*en\s+([^\s]+@[^\s]+)/i
                            ];
                            
                            for (const pattern of emailPatterns) {
                                const match = bodyText.match(pattern);
                                if (match) {
                                    return {
                                        email: match[1],
                                        context: match[0]
                                    };
                                }
                            }
                            return null;
                        }''')
                        
                        if email_info:
                            logger.info(f"\n📧 Email info: {email_info['context']}")
                        
                        # Wait a bit to see if page changes
                        await page.wait_for_timeout(5000)
                        
                        # Final screenshot
                        await page.screenshot(path=f"{output_dir}/confirmation_final.png", full_page=True)
                        
                        break
                
                if not confirmation_found:
                    logger.warning("No confirmation page detected after 5 minutes")
                    
            else:
                logger.error("No form found on the page")
                await page.screenshot(path=f"{output_dir}/no_form.png", full_page=True)
                
        except Exception as e:
            logger.error(f"Error: {e}", exc_info=True)
            await page.screenshot(path=f"{output_dir}/error.png", full_page=True)
        
        finally:
            logger.info(f"\nResults saved to: {output_dir}")
            input("\nPress Enter to close browser...")
            await browser.close()

if __name__ == "__main__":
    logger.info("Confirmation Page Capture")
    logger.info("========================")
    logger.info("This will:")
    logger.info("1. Open the booking form")
    logger.info("2. Wait for you to complete the booking")
    logger.info("3. Capture all details from the confirmation page")
    logger.info("4. Extract cancel/modify links")
    asyncio.run(capture_confirmation_page())