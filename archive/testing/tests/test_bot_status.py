#!/usr/bin/env python3
"""Test script to check LVBOT system status and take diagnostic screenshots."""
from utils.tracking import t

import asyncio
import os
import sys
import json
from datetime import datetime
from pathlib import Path

# Add parent directory to path
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from lvbot.utils.async_browser_pool import AsyncBrowserPool
from lvbot.utils.constants import COURT_CONFIG


async def test_browser_pool():
    """Test browser pool initialization and take screenshots."""
    t('archive.testing.tests.test_bot_status.test_browser_pool')
    print("🔍 Testing LVBOT System Status\n")
    
    status_report = {
        "timestamp": datetime.now().isoformat(),
        "browser_pool": False,
        "browsers_initialized": 0,
        "screenshots_taken": [],
        "errors": []
    }
    
    testing_root = Path(__file__).resolve().parent.parent

    try:
        # Try to initialize browser pool
        print("1. Attempting to initialize browser pool...")
        pool = AsyncBrowserPool(courts=[1])  # Initialize with court 1 only
        await pool.start()
        status_report["browser_pool"] = True
        print("   ✅ Browser pool initialized successfully")
        
        # Test browser functionality
        print("\n2. Testing browser functionality...")
        browser = None
        try:
            # Get a page from the pool
            page = pool.pages.get(1)  # Get court 1 page
            if page:
                status_report["browsers_initialized"] += 1
                print("   ✅ Browser instance obtained")
                
                # Create screenshots directory
                screenshot_dir = testing_root / "screencaps" / "debug_screenshots_status"
                screenshot_dir.mkdir(exist_ok=True)
                
                # Take screenshot of court URLs
                print("\n3. Taking screenshots of court booking pages...")
                for court_num, config in COURT_CONFIG.items():
                    url = config["full_url"]
                    try:
                        print(f"   📸 Court {court_num}: ", end="", flush=True)
                        # Create new page for each court
                        new_page = await pool.browser.new_page()
                        await new_page.goto(url, wait_until="domcontentloaded", timeout=10000)
                        
                        screenshot_path = screenshot_dir / f"court_{court_num}_status.png"
                        await new_page.screenshot(path=str(screenshot_path))
                        status_report["screenshots_taken"].append(str(screenshot_path))
                        print("✅")
                        
                        await new_page.close()
                    except Exception as e:
                        error_msg = f"Court {court_num} screenshot failed: {str(e)}"
                        status_report["errors"].append(error_msg)
                        print(f"❌ {str(e)}")
                
        finally:
            pass
        
        # Cleanup
        await pool.stop()
        
    except Exception as e:
        error_msg = f"Browser pool initialization failed: {str(e)}"
        status_report["errors"].append(error_msg)
        print(f"   ❌ {error_msg}")
    
    # Check bot data files
    print("\n4. Checking bot data files...")
    data_files = ["users.json", "queue.json", "data/all_reservations.json"]
    for file_path in data_files:
        try:
            if os.path.exists(file_path):
                with open(file_path, 'r') as f:
                    data = json.load(f)
                    if file_path == "queue.json":
                        # queue.json is a list, not a dict
                        if isinstance(data, list):
                            active_count = len([r for r in data 
                                              if r.get("status") in ["scheduled", "executing"]])
                            print(f"   📋 {file_path}: {active_count} active reservations")
                        else:
                            print(f"   📋 {file_path}: unexpected format")
                    else:
                        print(f"   📋 {file_path}: exists")
            else:
                print(f"   ❌ {file_path}: not found")
        except Exception as e:
            print(f"   ❌ {file_path}: error reading - {str(e)}")
    
    # Check log files
    print("\n5. Checking recent log activity...")
    log_dir = testing_root / "logs" / "archive" / "latest_log"
    if log_dir.exists():
        for log_file in ["bot.log", "bot_errors.log"]:
            log_path = log_dir / log_file
            if log_path.exists():
                # Get last modification time
                mtime = datetime.fromtimestamp(log_path.stat().st_mtime)
                time_diff = datetime.now() - mtime
                print(f"   📄 {log_file}: last updated {time_diff.total_seconds():.0f}s ago")
    
    # Generate summary
    print("\n" + "="*50)
    print("📊 SYSTEM STATUS SUMMARY:")
    print("="*50)
    print(f"✅ Browser pool: {'Working' if status_report['browser_pool'] else 'Failed'}")
    print(f"📸 Screenshots taken: {len(status_report['screenshots_taken'])}")
    print(f"❌ Errors encountered: {len(status_report['errors'])}")
    
    if status_report['errors']:
        print("\n⚠️  Errors:")
        for error in status_report['errors']:
            print(f"   - {error}")
    
    # Save status report
    report_path = testing_root / "artifacts" / "system_status_report.json"
    with open(report_path, 'w') as f:
        json.dump(status_report, f, indent=2)
    print(f"\n💾 Full report saved to: {report_path}")
    
    return status_report


if __name__ == "__main__":
    # Run the test
    asyncio.run(test_browser_pool())
