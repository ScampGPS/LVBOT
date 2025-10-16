#!/usr/bin/env python3
"""
Debugging test script for LVBOT critical issues

Tests:
1. Bot polling conflict detection
2. Browser cleanup verification
3. Process cleanup validation
"""
from tracking import t
import pathlib
import sys

ROOT_DIR = pathlib.Path(__file__).resolve().parents[2]
if str(ROOT_DIR) not in sys.path:
    sys.path.insert(0, str(ROOT_DIR))


import subprocess
import time
import logging
import os
from pathlib import Path

# Setup logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger('DebugTest')

def get_python_processes():
    """Get all Python processes running telegram bot"""
    t('archive.scripts.diagnostics.debug_bot_test.get_python_processes')
    try:
        result = subprocess.run(['ps', 'aux'], capture_output=True, text=True)
        processes = []
        for line in result.stdout.split('\n'):
            if 'python' in line and 'telegram_tennis_bot' in line:
                processes.append(line.strip())
        return processes
    except:
        return []

def get_browser_processes():
    """Get all browser-related processes"""
    t('archive.scripts.diagnostics.debug_bot_test.get_browser_processes')
    try:
        result = subprocess.run(['ps', 'aux'], capture_output=True, text=True)
        processes = []
        for line in result.stdout.split('\n'):
            if any(keyword in line for keyword in ['chromium', 'chrome-linux', 'playwright']):
                processes.append(line.strip())
        return processes
    except:
        return []

def check_bot_errors():
    """Check recent bot errors"""
    t('archive.scripts.diagnostics.debug_bot_test.check_bot_errors')
    try:
        testing_root = Path(__file__).resolve().parent.parent
        error_log = testing_root / "logs" / "archive" / "latest_log" / "bot_errors.log"
        with open(error_log, 'r') as f:
            lines = f.readlines()
            # Get last 10 lines
            recent_errors = lines[-10:] if len(lines) > 10 else lines
            conflict_errors = [line for line in recent_errors if 'terminated by other getUpdates request' in line]
            return conflict_errors
    except:
        return []

def main():
    t('archive.scripts.diagnostics.debug_bot_test.main')
    logger.info("="*60)
    logger.info("LVBOT DEBUGGING TEST")
    logger.info("="*60)
    
    # Test 1: Check for duplicate bot processes
    logger.info("1. CHECKING PYTHON BOT PROCESSES...")
    python_procs = get_python_processes()
    if len(python_procs) == 0:
        logger.info("   ✅ No bot processes currently running")
    elif len(python_procs) == 1:
        logger.info("   ✅ Single bot process running (normal)")
        logger.info(f"      {python_procs[0]}")
    else:
        logger.error(f"   ❌ MULTIPLE BOT PROCESSES DETECTED ({len(python_procs)})")
        for proc in python_procs:
            logger.error(f"      {proc}")
    
    # Test 2: Check for browser processes
    logger.info("\n2. CHECKING BROWSER PROCESSES...")
    browser_procs = get_browser_processes()
    if len(browser_procs) == 0:
        logger.info("   ✅ No browser processes running")
    else:
        logger.warning(f"   ⚠️  {len(browser_procs)} browser processes detected")
        for proc in browser_procs[:5]:  # Show first 5
            logger.info(f"      {proc}")
        if len(browser_procs) > 5:
            logger.info(f"      ... and {len(browser_procs) - 5} more")
    
    # Test 3: Check for recent polling conflicts
    logger.info("\n3. CHECKING FOR RECENT POLLING CONFLICTS...")
    conflict_errors = check_bot_errors()
    if len(conflict_errors) == 0:
        logger.info("   ✅ No recent polling conflicts detected")
    else:
        logger.error(f"   ❌ {len(conflict_errors)} recent polling conflicts found")
        for error in conflict_errors[-3:]:  # Show last 3
            logger.error(f"      {error.strip()}")
    
    # Test 4: Check bot functionality
    logger.info("\n4. TESTING BOT FUNCTIONALITY...")
    if len(python_procs) == 1:
        logger.info("   ℹ️  Bot is running - check Telegram for responsiveness")
        logger.info("   ℹ️  Send /start to the bot to test if it responds")
    elif len(python_procs) == 0:
        logger.info("   ℹ️  Bot is not running - safe to start")
    else:
        logger.error("   ❌ Multiple bot instances - STOP ALL before restarting")
    
    # Summary
    logger.info("\n" + "="*60)
    logger.info("SUMMARY:")
    issues = []
    
    if len(python_procs) > 1:
        issues.append(f"Multiple bot processes ({len(python_procs)})")
    
    if len(browser_procs) > 0:
        issues.append(f"Browser processes not cleaned up ({len(browser_procs)})")
    
    if len(conflict_errors) > 0:
        issues.append(f"Recent polling conflicts ({len(conflict_errors)})")
    
    if issues:
        logger.error("❌ ISSUES DETECTED:")
        for issue in issues:
            logger.error(f"   - {issue}")
        logger.info("\nRECOMMENDED ACTIONS:")
        logger.info("1. Kill all bot processes: pkill -f 'python.*telegram_tennis_bot'")
        logger.info("2. Kill all browser processes: pkill -9 -f 'chromium|chrome-linux|playwright'")
        logger.info("3. Wait 10 seconds, then restart bot")
    else:
        logger.info("✅ NO CRITICAL ISSUES DETECTED")
    
    logger.info("="*60)

if __name__ == '__main__':
    main()
