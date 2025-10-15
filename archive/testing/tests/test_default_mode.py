#!/usr/bin/env python3
"""
Test that experienced mode is now the default
"""

import asyncio
import logging

# Setup logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)

async def test_default_mode():
    """Test that experienced mode is the default"""
    
    from lvbot.utils.async_booking_executor import AsyncBookingExecutor
    
    # Create executor without specifying experienced_mode
    executor = AsyncBookingExecutor(browser_pool=None)
    
    print(f"Default experienced_mode value: {executor.experienced_mode}")
    print(f"Expected: True (experienced mode enabled by default)")
    
    # Also test explicit modes
    standard_executor = AsyncBookingExecutor(browser_pool=None, experienced_mode=False)
    experienced_executor = AsyncBookingExecutor(browser_pool=None, experienced_mode=True)
    
    print(f"\nStandard mode executor: experienced_mode={standard_executor.experienced_mode}")
    print(f"Experienced mode executor: experienced_mode={experienced_executor.experienced_mode}")
    
    if executor.experienced_mode:
        print("\n✅ SUCCESS: Experienced mode is now the default!")
        print("   Bookings will execute in ~26.5s instead of ~40.2s")
    else:
        print("\n❌ FAILED: Experienced mode is not the default")

if __name__ == "__main__":
    asyncio.run(test_default_mode())