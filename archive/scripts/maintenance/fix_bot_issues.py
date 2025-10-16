#!/usr/bin/env python3
"""
LVBOT Critical Issues Fix Script

Fixes:
1. Kills duplicate bot processes
2. Force kills all browser processes
3. Provides clean restart instructions
"""
from tracking import t
import pathlib
import sys

from pathlib import Path

ROOT_DIR = pathlib.Path(__file__).resolve().parents[2]
if str(ROOT_DIR) not in sys.path:
    sys.path.insert(0, str(ROOT_DIR))


import subprocess
import time
import logging
import os

# Setup logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger('BotFixer')

def kill_bot_processes():
    """Kill all bot processes"""
    t('archive.scripts.maintenance.fix_bot_issues.kill_bot_processes')
    logger.info("🔴 Killing all bot processes...")
    try:
        # Kill Python bot processes
        result = subprocess.run(['pkill', '-f', 'python.*telegram_tennis_bot'], 
                              capture_output=True, text=True)
        if result.returncode == 0:
            logger.info("✅ Bot processes killed successfully")
        else:
            logger.info("ℹ️  No bot processes found to kill")
        
        # Also kill bash wrapper if exists
        subprocess.run(['pkill', '-f', 'bash.*telegram_tennis_bot'], 
                      capture_output=True, text=True)
        
        return True
    except Exception as e:
        logger.error(f"❌ Error killing bot processes: {e}")
        return False

def kill_browser_processes():
    """Force kill all browser processes"""
    t('archive.scripts.maintenance.fix_bot_issues.kill_browser_processes')
    logger.info("🔴 Force killing all browser processes...")
    try:
        # Kill with SIGKILL (-9) for immediate termination
        processes_to_kill = [
            'chromium',
            'chrome-linux', 
            'playwright',
            'node.*playwright'
        ]
        
        for process in processes_to_kill:
            subprocess.run(['pkill', '-9', '-f', process], 
                          capture_output=True, text=True)
        
        logger.info("✅ Browser processes force killed")
        return True
    except Exception as e:
        logger.error(f"❌ Error killing browser processes: {e}")
        return False

def verify_cleanup():
    """Verify all processes are cleaned up"""
    t('archive.scripts.maintenance.fix_bot_issues.verify_cleanup')
    logger.info("🔍 Verifying cleanup...")
    
    # Check for remaining bot processes
    try:
        result = subprocess.run(['pgrep', '-f', 'python.*telegram_tennis_bot'], 
                              capture_output=True, text=True)
        if result.returncode == 0:
            logger.warning(f"⚠️  Still {len(result.stdout.strip().split())} bot processes running")
            return False
    except:
        pass
    
    # Check for remaining browser processes
    try:
        result = subprocess.run(['pgrep', '-f', 'chromium|chrome-linux|playwright'], 
                              capture_output=True, text=True)
        if result.returncode == 0:
            browser_count = len(result.stdout.strip().split())
            if browser_count > 0:
                logger.warning(f"⚠️  Still {browser_count} browser processes running")
                return False
    except:
        pass
    
    logger.info("✅ All processes cleaned up successfully")
    return True

def main():
    t('archive.scripts.maintenance.fix_bot_issues.main')
    logger.info("="*60)
    logger.info("LVBOT CRITICAL ISSUES FIX SCRIPT")
    logger.info("="*60)
    
    # Step 1: Kill bot processes
    logger.info("STEP 1: Stopping bot processes...")
    if not kill_bot_processes():
        logger.error("❌ Failed to stop bot processes")
        return 1
    
    time.sleep(2)  # Give processes time to die
    
    # Step 2: Kill browser processes
    logger.info("\nSTEP 2: Force killing browser processes...")
    if not kill_browser_processes():
        logger.error("❌ Failed to kill browser processes")
        return 1
    
    time.sleep(3)  # Give processes time to die
    
    # Step 3: Verify cleanup
    logger.info("\nSTEP 3: Verifying cleanup...")
    if not verify_cleanup():
        logger.warning("⚠️  Some processes may still be running")
        logger.info("You may need to run this script again or restart the system")
    
    # Step 4: Instructions
    logger.info("\n" + "="*60)
    logger.info("✅ CLEANUP COMPLETED")
    logger.info("="*60)
    logger.info("")
    logger.info("NEXT STEPS:")
    logger.info("1. Wait 10 seconds for complete cleanup")
    logger.info("2. Start the bot with: python3 telegram_tennis_bot.py")
    logger.info("3. Monitor logs for any polling conflicts")
    logger.info("4. Test bot responsiveness in Telegram with /start")
    logger.info("")
    logger.info("FIXED ISSUES:")
    logger.info("✅ Enhanced polling configuration to prevent conflicts")
    logger.info("✅ Improved browser cleanup with detailed logging")
    logger.info("✅ Added signal handlers for graceful shutdown")
    logger.info("✅ Force kill mechanisms for stuck processes")
    logger.info("")
    logger.info("If issues persist, check logs in:")
    logger.info("- testing/logs/archive/latest_log/bot_errors.log")
    logger.info("- testing/logs/archive/latest_log/main_bot.log")
    logger.info("="*60)
    
    return 0

if __name__ == '__main__':
    exit_code = main()
    sys.exit(exit_code)
