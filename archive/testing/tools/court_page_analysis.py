#!/usr/bin/env python3
"""
Test to analyze DOM and network differences between Court 1, 2, and 3 pages
Specifically looking for why Court 3 fails to load properly
"""

import asyncio
import json
from playwright.async_api import async_playwright
from datetime import datetime
import os

# Court URLs
COURT_URLS = {
    1: "https://clublavilla.as.me/schedule/7d558012/appointment/15970897/calendar/4282490?appointmentTypeIds[]=15970897",
    2: "https://clublavilla.as.me/schedule/7d558012/appointment/16021953/calendar/4291312?appointmentTypeIds[]=16021953",
    3: "https://clublavilla.as.me/schedule/7d558012/appointment/16120442/calendar/4307254?appointmentTypeIds[]=16120442"
}

async def analyze_court_page(page, court_number):
    """Analyze a single court page for DOM and network resources"""
    print(f"\n{'='*60}")
    print(f"ANALYZING COURT {court_number}")
    print(f"{'='*60}")
    
    results = {
        "court": court_number,
        "url": COURT_URLS[court_number],
        "network_requests": [],
        "dom_structure": {},
        "time_buttons": [],
        "errors": []
    }
    
    # Set up network monitoring
    network_requests = []
    
    async def log_request(request):
        network_requests.append({
            "url": request.url,
            "method": request.method,
            "resource_type": request.resource_type,
            "timestamp": datetime.now().isoformat()
        })
    
    async def log_response(response):
        # Log failed responses
        if response.status >= 400:
            results["errors"].append({
                "url": response.url,
                "status": response.status,
                "status_text": response.status_text
            })
    
    page.on("request", log_request)
    page.on("response", log_response)
    
    # Navigate to court page
    print(f"Navigating to: {COURT_URLS[court_number]}")
    try:
        await page.goto(COURT_URLS[court_number], wait_until='networkidle', timeout=30000)
        await asyncio.sleep(3)  # Wait for dynamic content
    except Exception as e:
        results["errors"].append(f"Navigation error: {str(e)}")
        print(f"❌ Navigation failed: {e}")
    
    # Analyze DOM structure
    print("\n📋 Analyzing DOM structure...")
    
    # Check for key elements
    dom_checks = {
        "scheduling_container": await page.query_selector('.scheduling-container'),
        "calendar_container": await page.query_selector('.calendar'),
        "time_buttons_container": await page.query_selector('.times'),
        "acuity_container": await page.query_selector('[id*="acuity"]'),
        "appointment_type": await page.query_selector('[data-appointment-type]'),
        "day_containers": await page.query_selector_all('.day'),
        "time_list": await page.query_selector('.time-list'),
        "slots_container": await page.query_selector('.slots')
    }
    
    for element_name, element in dom_checks.items():
        if element:
            results["dom_structure"][element_name] = "Found"
            print(f"✅ {element_name}: Found")
        else:
            results["dom_structure"][element_name] = "Not found"
            print(f"❌ {element_name}: Not found")
    
    # Look for time buttons with various selectors
    print("\n🕐 Searching for time buttons...")
    time_selectors = [
        'button:has-text("AM")',
        'button:has-text("PM")',
        'button.time',
        '[class*="time-button"]',
        'button[data-time]',
        '.time-slot',
        'a:has-text("AM")',
        'a:has-text("PM")'
    ]
    
    for selector in time_selectors:
        try:
            buttons = await page.query_selector_all(selector)
            if buttons:
                print(f"  Found {len(buttons)} buttons with selector: {selector}")
                for i, button in enumerate(buttons[:3]):  # Show first 3
                    text = await button.text_content()
                    results["time_buttons"].append({
                        "selector": selector,
                        "text": text.strip() if text else ""
                    })
                    print(f"    Button {i+1}: '{text.strip() if text else 'empty'}'")
        except Exception as e:
            print(f"  Error with selector {selector}: {e}")
    
    # Get page text content
    print("\n📄 Page text preview:")
    page_text = await page.text_content('body')
    if page_text:
        preview = page_text[:200].replace('\n', ' ').strip()
        print(f"  {preview}...")
        
        # Check for specific text patterns
        if "no disponible" in page_text.lower():
            print("  ⚠️  Found 'no disponible' - might indicate no availability")
        if "error" in page_text.lower():
            print("  ⚠️  Found 'error' in page text")
        if "6:00" in page_text or "06:00" in page_text:
            print("  ✅ Found 6:00 AM slot in page text!")
    
    # Analyze network requests
    print(f"\n🌐 Network requests: {len(network_requests)}")
    api_requests = [r for r in network_requests if 'api' in r['url'] or 'acuity' in r['url']]
    print(f"  API requests: {len(api_requests)}")
    
    # Show unique API endpoints
    unique_apis = set()
    for req in api_requests:
        # Extract endpoint from URL
        url_parts = req['url'].split('?')[0].split('/')
        endpoint = '/'.join(url_parts[-2:]) if len(url_parts) > 2 else url_parts[-1]
        unique_apis.add(endpoint)
    
    print("  Unique API endpoints:")
    for endpoint in sorted(unique_apis):
        print(f"    - {endpoint}")
    
    results["network_requests"] = network_requests[:50]  # Limit to first 50
    
    # Take screenshot
    screenshot_path = f"court_{court_number}_analysis.png"
    await page.screenshot(path=screenshot_path, full_page=True)
    print(f"\n📸 Screenshot saved: {screenshot_path}")
    
    # Save HTML for debugging
    html_path = f"court_{court_number}_page.html"
    html_content = await page.content()
    with open(html_path, 'w', encoding='utf-8') as f:
        f.write(html_content)
    print(f"📄 HTML saved: {html_path}")
    
    return results

async def main():
    """Run the court page analysis"""
    print("🎾 Court Page Analysis Tool")
    print("Analyzing differences between Court 1, 2, and 3")
    
    async with async_playwright() as p:
        browser = await p.chromium.launch(
            headless=False,  # Show browser for debugging
            args=['--disable-blink-features=AutomationControlled']
        )
        
        context = await browser.new_context(
            viewport={'width': 1280, 'height': 720},
            user_agent='Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36'
        )
        
        all_results = {}
        
        # Analyze each court
        for court_num in [1, 2, 3]:
            page = await context.new_page()
            results = await analyze_court_page(page, court_num)
            all_results[f"court_{court_num}"] = results
            await page.close()
        
        # Compare results
        print("\n" + "="*60)
        print("COMPARISON SUMMARY")
        print("="*60)
        
        # Compare DOM structures
        print("\n🔍 DOM Structure Differences:")
        court1_dom = set(all_results["court_1"]["dom_structure"].keys())
        court2_dom = set(all_results["court_2"]["dom_structure"].keys())
        court3_dom = set(all_results["court_3"]["dom_structure"].keys())
        
        # Find what Court 3 is missing
        court3_missing = (court1_dom | court2_dom) - court3_dom
        if court3_missing:
            print(f"  Court 3 is missing: {court3_missing}")
        
        # Compare found elements
        for element in sorted(court1_dom | court2_dom | court3_dom):
            c1 = all_results["court_1"]["dom_structure"].get(element, "N/A")
            c2 = all_results["court_2"]["dom_structure"].get(element, "N/A")
            c3 = all_results["court_3"]["dom_structure"].get(element, "N/A")
            
            if c3 != c1 or c3 != c2:
                print(f"  {element}:")
                print(f"    Court 1: {c1}")
                print(f"    Court 2: {c2}")
                print(f"    Court 3: {c3} {'⚠️' if c3 == 'Not found' else ''}")
        
        # Compare time buttons found
        print("\n⏰ Time Buttons Comparison:")
        for court_num in [1, 2, 3]:
            buttons = all_results[f"court_{court_num}"]["time_buttons"]
            print(f"  Court {court_num}: {len(buttons)} time buttons found")
            if court_num == 3 and len(buttons) == 0:
                print("    ⚠️  NO TIME BUTTONS FOUND FOR COURT 3!")
        
        # Compare errors
        print("\n❌ Errors:")
        for court_num in [1, 2, 3]:
            errors = all_results[f"court_{court_num}"]["errors"]
            if errors:
                print(f"  Court {court_num}: {len(errors)} errors")
                for error in errors[:3]:
                    print(f"    - {error}")
        
        # Save full results
        with open("court_analysis_results.json", "w") as f:
            json.dump(all_results, f, indent=2)
        print("\n💾 Full results saved to: court_analysis_results.json")
        
        await browser.close()

if __name__ == "__main__":
    # Create test directory
    os.makedirs("tests", exist_ok=True)
    os.chdir("tests")
    
    asyncio.run(main())