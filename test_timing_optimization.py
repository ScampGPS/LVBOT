#!/usr/bin/env python3
"""
Timing optimization test - Find the fastest settings that still avoid bot detection
Tests different warm-up times and action delays systematically
"""

import asyncio
import logging
import json
import os
from datetime import datetime, timedelta
from typing import Dict, List, Tuple

# Setup logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    datefmt='%H:%M:%S'
)

class TimingOptimizer:
    """Systematically test different timing configurations"""
    
    def __init__(self):
        self.logger = logging.getLogger('TimingOptimizer')
        self.results = []
        self.user_info = {
            'user_id': 125763357,
            'first_name': 'Saul',
            'last_name': 'Campos',
            'email': 'msaulcampos@gmail.com',
            'phone': '31874277'
        }
        
    async def find_available_slots(self, browser_pool) -> List[Dict]:
        """Dynamically find available slots for tomorrow ONLY"""
        from utils.court_availability import CourtAvailability
        
        availability = CourtAvailability()
        
        # IMPORTANT: Only look for tomorrow's slots
        today = datetime.now()
        tomorrow = today + timedelta(days=1)
        tomorrow_str = tomorrow.strftime('%Y-%m-%d')
        today_str = today.strftime('%Y-%m-%d')
        
        self.logger.info(f"Searching for slots on {tomorrow_str} (tomorrow) ONLY")
        self.logger.info(f"TODAY ({today_str}) slots will be IGNORED to avoid same-day bookings")
        
        available_slots = []
        
        for court_number in [1, 2, 3]:
            try:
                page = await browser_pool.get_page(court_number)
                if page and await availability.is_acuity_scheduling_page(page):
                    times_by_day = await availability.extract_acuity_times_by_day(page)
                    
                    # CRITICAL: Only add tomorrow's slots
                    if tomorrow_str in times_by_day:
                        for time_slot in times_by_day[tomorrow_str]:
                            available_slots.append({
                                'court': court_number,
                                'time': time_slot,
                                'date': tomorrow  # Explicitly use tomorrow's date
                            })
                            
                    # Log if we see today's slots (but don't add them)
                    if today_str in times_by_day:
                        self.logger.warning(f"Court {court_number} has {len(times_by_day[today_str])} slots for TODAY - IGNORING THEM")
                        
            except Exception as e:
                self.logger.warning(f"Error checking court {court_number}: {e}")
        
        self.logger.info(f"Found {len(available_slots)} available slots for TOMORROW ({tomorrow_str})")
        return available_slots
    
    async def test_timing_configuration(
        self,
        warmup_seconds: float,
        initial_delay_min: float,
        initial_delay_max: float,
        config_name: str
    ) -> Dict:
        """Test a specific timing configuration"""
        
        self.logger.info(f"\n{'='*80}")
        self.logger.info(f"TESTING CONFIGURATION: {config_name}")
        self.logger.info(f"Warm-up: {warmup_seconds}s | Initial delay: {initial_delay_min}-{initial_delay_max}s")
        self.logger.info(f"{'='*80}")
        
        # Temporarily modify the browser pool warm-up time
        import utils.async_browser_pool as pool_module
        original_warmup = getattr(pool_module, 'WARMUP_DELAY', 10.0)
        pool_module.WARMUP_DELAY = warmup_seconds
        
        # Temporarily modify the working executor delays
        import utils.working_booking_executor as executor_module
        original_delay_min = getattr(executor_module, 'INITIAL_DELAY_MIN', 3.0)
        original_delay_max = getattr(executor_module, 'INITIAL_DELAY_MAX', 5.0)
        executor_module.INITIAL_DELAY_MIN = initial_delay_min
        executor_module.INITIAL_DELAY_MAX = initial_delay_max
        
        result = {
            'config_name': config_name,
            'warmup_seconds': warmup_seconds,
            'initial_delay_min': initial_delay_min,
            'initial_delay_max': initial_delay_max,
            'success': False,
            'bot_detected': False,
            'error': None,
            'execution_time': None,
            'slot_attempted': None
        }
        
        try:
            # Initialize browser pool with custom timing
            from utils.async_browser_pool import AsyncBrowserPool
            from utils.async_booking_executor import AsyncBookingExecutor
            
            browser_pool = AsyncBrowserPool()
            start_time = datetime.now()
            
            # Patch the warm-up delay in the browser pool
            original_method = browser_pool._create_and_navigate_court_page_safe
            async def patched_navigate(court):
                result = await original_method(court)
                if result:
                    self.logger.info(f"Court {court}: Warming up for {warmup_seconds}s...")
                    await asyncio.sleep(warmup_seconds)
                    self.logger.info(f"Court {court}: Warm-up complete")
                return result
            browser_pool._create_and_navigate_court_page_safe = patched_navigate
            
            await browser_pool.start()
            
            # Find available slots
            available_slots = await self.find_available_slots(browser_pool)
            if not available_slots:
                result['error'] = "No available slots found"
                return result
            
            # Try the first available slot
            slot = available_slots[0]
            
            # SAFETY CHECK: Ensure we're booking tomorrow
            if slot['date'].date() <= datetime.now().date():
                self.logger.error(f"SAFETY CHECK FAILED: Attempting to book today or past! Date: {slot['date'].date()}")
                result['error'] = "Safety check prevented booking today"
                return result
            
            result['slot_attempted'] = f"Court {slot['court']} at {slot['time']} on {slot['date'].strftime('%Y-%m-%d')}"
            
            # Patch the initial delay in working executor
            executor = AsyncBookingExecutor(browser_pool, use_natural_flow=False)
            
            # Execute booking
            self.logger.info(f"Attempting to book: {result['slot_attempted']}")
            booking_result = await executor.execute_booking(
                court_number=slot['court'],
                time_slot=slot['time'],
                user_info=self.user_info,
                target_date=slot['date']
            )
            
            execution_time = (datetime.now() - start_time).total_seconds()
            result['execution_time'] = execution_time
            
            # Check for bot detection
            page = await browser_pool.get_page(slot['court'])
            if page:
                try:
                    # Check for anti-bot message
                    error_element = await page.query_selector('p[role="alert"]')
                    if error_element:
                        error_text = await error_element.inner_text()
                        if 'irregular' in error_text.lower() or 'detectó' in error_text.lower():
                            result['bot_detected'] = True
                            result['error'] = error_text
                            self.logger.error(f"❌ BOT DETECTED: {error_text}")
                    
                    # Check page content for other indicators
                    page_text = await page.inner_text('body')
                    if 'irregular' in page_text.lower() and not result['bot_detected']:
                        result['bot_detected'] = True
                        result['error'] = "Bot detection found in page content"
                except:
                    pass
            
            if booking_result.success and not result['bot_detected']:
                result['success'] = True
                self.logger.info(f"✅ BOOKING SUCCESSFUL in {execution_time:.1f}s!")
            elif not result['bot_detected']:
                result['error'] = booking_result.error_message
                self.logger.warning(f"Booking failed: {result['error']}")
            
            # Cleanup
            if hasattr(browser_pool, 'close'):
                await browser_pool.close()
            
        except Exception as e:
            result['error'] = str(e)
            self.logger.error(f"Test failed: {e}")
        finally:
            # Restore original values
            pool_module.WARMUP_DELAY = original_warmup
            executor_module.INITIAL_DELAY_MIN = original_delay_min
            executor_module.INITIAL_DELAY_MAX = original_delay_max
        
        return result
    
    async def run_optimization_tests(self):
        """Run systematic timing tests"""
        
        print("\n" + "="*80)
        print("TIMING OPTIMIZATION TEST SUITE")
        print("="*80)
        print("This will test various timing configurations to find the fastest")
        print("settings that still avoid bot detection.")
        print("="*80 + "\n")
        
        # Test configurations - start conservative and get more aggressive
        test_configs = [
            # (warmup_seconds, initial_delay_min, initial_delay_max, config_name)
            (10.0, 3.0, 5.0, "Original (10s + 3-5s)"),
            (8.0, 3.0, 5.0, "Reduced warmup (8s + 3-5s)"),
            (8.0, 2.0, 4.0, "Reduced both (8s + 2-4s)"),
            (6.0, 2.0, 4.0, "Aggressive warmup (6s + 2-4s)"),
            (6.0, 1.0, 3.0, "More aggressive (6s + 1-3s)"),
            (5.0, 1.0, 2.0, "Very aggressive (5s + 1-2s)"),
            (4.0, 1.0, 2.0, "Ultra aggressive (4s + 1-2s)"),
            (3.0, 0.5, 1.5, "Extreme (3s + 0.5-1.5s)"),
        ]
        
        for config in test_configs:
            warmup, delay_min, delay_max, name = config
            
            result = await self.test_timing_configuration(
                warmup_seconds=warmup,
                initial_delay_min=delay_min,
                initial_delay_max=delay_max,
                config_name=name
            )
            
            self.results.append(result)
            
            # If bot was detected, stop testing more aggressive configs
            if result['bot_detected']:
                self.logger.warning("Bot detected! Stopping more aggressive tests.")
                break
            
            # Small delay between tests
            await asyncio.sleep(5)
        
        # Save and display results
        self.save_results()
        self.display_results()
    
    def save_results(self):
        """Save test results to file"""
        with open('timing_optimization_results.json', 'w') as f:
            json.dump(self.results, f, indent=2)
        self.logger.info("Results saved to timing_optimization_results.json")
    
    def display_results(self):
        """Display test results summary"""
        print("\n" + "="*80)
        print("TIMING OPTIMIZATION RESULTS")
        print("="*80)
        print(f"{'Configuration':<30} {'Success':<10} {'Bot Detected':<15} {'Time (s)':<10}")
        print("-"*80)
        
        optimal_config = None
        
        for result in self.results:
            status = "✅" if result['success'] else "❌"
            bot = "🚨 YES" if result['bot_detected'] else "No"
            time = f"{result['execution_time']:.1f}" if result['execution_time'] else "N/A"
            
            print(f"{result['config_name']:<30} {status:<10} {bot:<15} {time:<10}")
            
            # Track the fastest successful config
            if result['success'] and not result['bot_detected']:
                optimal_config = result
        
        print("="*80)
        
        if optimal_config:
            print(f"\n🎯 OPTIMAL CONFIGURATION FOUND:")
            print(f"   Warm-up: {optimal_config['warmup_seconds']}s")
            print(f"   Initial delay: {optimal_config['initial_delay_min']}-{optimal_config['initial_delay_max']}s")
            print(f"   Total execution time: {optimal_config['execution_time']:.1f}s")
        else:
            print("\n❌ No optimal configuration found")

async def main():
    """Run the timing optimization tests"""
    optimizer = TimingOptimizer()
    await optimizer.run_optimization_tests()

if __name__ == "__main__":
    asyncio.run(main())