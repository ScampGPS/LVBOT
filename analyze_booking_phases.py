#!/usr/bin/env python3
"""
Analyze all phases of the booking process to identify optimization opportunities
"""

import asyncio
import logging
import time
from datetime import datetime, timedelta
from typing import Dict, List

# Setup logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    datefmt='%H:%M:%S'
)

class BookingPhaseAnalyzer:
    """Analyze timing of each booking phase"""
    
    def __init__(self):
        self.logger = logging.getLogger('PhaseAnalyzer')
        self.phase_times = {}
        self.user_info = {
            'user_id': 125763357,
            'first_name': 'Saul',
            'last_name': 'Campos',
            'email': 'msaulcampos@gmail.com',
            'phone': '31874277'
        }
        
    def start_phase(self, phase_name: str):
        """Mark the start of a phase"""
        self.phase_times[phase_name] = {'start': time.time()}
        
    def end_phase(self, phase_name: str):
        """Mark the end of a phase"""
        if phase_name in self.phase_times:
            self.phase_times[phase_name]['end'] = time.time()
            self.phase_times[phase_name]['duration'] = self.phase_times[phase_name]['end'] - self.phase_times[phase_name]['start']
    
    async def analyze_booking_process(self):
        """Analyze the entire booking process with detailed timing"""
        
        print("\n" + "="*80)
        print("BOOKING PHASE ANALYSIS")
        print("="*80)
        print("This will measure each phase of the booking process")
        print("Using Optimized 3 settings: 4s warmup + 1-2s delay")
        print("="*80 + "\n")
        
        # Import modules
        from utils.async_browser_pool import AsyncBrowserPool
        from utils.working_booking_executor import WorkingBookingExecutor
        from playwright.async_api import Page
        import random
        
        # Phase 1: Browser Pool Initialization
        self.start_phase("1_browser_pool_init")
        browser_pool = AsyncBrowserPool()
        browser_pool.WARMUP_DELAY = 4.0  # Optimized 3
        await browser_pool.start()
        self.end_phase("1_browser_pool_init")
        
        # Get page for analysis
        page = await browser_pool.get_page(2)  # Use Court 2
        if not page:
            self.logger.error("Could not get page")
            return
        
        # Target tomorrow
        tomorrow = datetime.now() + timedelta(days=1)
        target_time = '10:00'  # Court 2 should have this available
        
        print(f"Target: Court 2 at {target_time} on {tomorrow.strftime('%Y-%m-%d')}")
        print("="*80 + "\n")
        
        # Create custom executor for detailed analysis
        executor = WorkingBookingExecutor(browser_pool)
        
        # Override methods to add timing
        original_human_type = executor.__class__.__module__
        
        # Phase 2: Initial Delay
        self.start_phase("2_initial_delay")
        delay = random.uniform(1.0, 2.0)  # Optimized 3
        await asyncio.sleep(delay)
        self.end_phase("2_initial_delay")
        
        # Phase 3: Natural Mouse Movement
        self.start_phase("3_mouse_movement")
        # Simulate natural mouse movement
        for _ in range(2):  # Reduced from original
            x = random.randint(200, 1000)
            y = random.randint(200, 700)
            await page.mouse.move(x, y)
            await asyncio.sleep(0.3)  # Short delays
        self.end_phase("3_mouse_movement")
        
        # Phase 4: Find Time Slot
        self.start_phase("4_find_time_slot")
        time_button = await page.query_selector(f'button:has-text("{target_time}")')
        if not time_button:
            # Try alternatives
            for alt_time in ['10', '10:00 AM']:
                time_button = await page.query_selector(f'button:has-text("{alt_time}")')
                if time_button:
                    break
        self.end_phase("4_find_time_slot")
        
        if not time_button:
            self.logger.error(f"Time slot {target_time} not found")
            await browser_pool.close()
            return
        
        # Phase 5: Approach Time Button
        self.start_phase("5_approach_button")
        button_box = await time_button.bounding_box()
        if button_box:
            target_x = button_box['x'] + button_box['width'] / 2
            target_y = button_box['y'] + button_box['height'] / 2
            await page.mouse.move(target_x, target_y)
            await asyncio.sleep(0.5)  # Can we reduce this?
        self.end_phase("5_approach_button")
        
        # Phase 6: Click Time Slot
        self.start_phase("6_click_time_slot")
        await time_button.click()
        self.end_phase("6_click_time_slot")
        
        # Phase 7: Wait for Form Load
        self.start_phase("7_wait_for_form")
        try:
            await page.wait_for_selector('#client\\.firstName', timeout=10000)
        except:
            self.logger.error("Form did not load")
        self.end_phase("7_wait_for_form")
        
        # Phase 8: Form Filling
        self.start_phase("8_form_filling")
        
        # Sub-phases for each field
        fields = [
            ('8a_firstName', '#client\\.firstName', self.user_info['first_name'], True),
            ('8b_lastName', '#client\\.lastName', self.user_info['last_name'], True),
            ('8c_phone', '#client\\.phone', self.user_info['phone'], False),
            ('8d_email', '#client\\.email', self.user_info['email'], True)
        ]
        
        for phase_name, selector, value, use_typing in fields:
            self.start_phase(phase_name)
            field = await page.query_selector(selector)
            if field:
                if use_typing:
                    # Analyze typing speed
                    await field.click()
                    await asyncio.sleep(0.1)
                    await field.fill('')
                    
                    # Type with current speed
                    for char in value:
                        delay = random.randint(36, 88) / 1000  # 2.5x speed
                        await field.type(char, delay=int(delay * 1000))
                else:
                    # Phone is filled directly
                    await field.click()
                    await asyncio.sleep(0.1)
                    await field.fill(value)
            self.end_phase(phase_name)
            
        self.end_phase("8_form_filling")
        
        # Phase 9: Pre-submission Review
        self.start_phase("9_pre_submit_review")
        await page.mouse.move(random.randint(300, 700), random.randint(600, 800))
        await asyncio.sleep(1.0)  # Can we reduce this?
        self.end_phase("9_pre_submit_review")
        
        # Phase 10: Find Submit Button
        self.start_phase("10_find_submit")
        submit_button = await page.query_selector('button:has-text("CONFIRMAR CITA")')
        self.end_phase("10_find_submit")
        
        if submit_button:
            # Phase 11: Approach Submit
            self.start_phase("11_approach_submit")
            button_box = await submit_button.bounding_box()
            if button_box:
                target_x = button_box['x'] + button_box['width'] / 2
                target_y = button_box['y'] + button_box['height'] / 2
                await page.mouse.move(target_x, target_y)
                await asyncio.sleep(0.5)  # Can we reduce this?
            self.end_phase("11_approach_submit")
            
            # Phase 12: Click Submit
            self.start_phase("12_click_submit")
            await submit_button.click()
            self.end_phase("12_click_submit")
            
            # Phase 13: Wait for Confirmation
            self.start_phase("13_wait_confirmation")
            await asyncio.sleep(5.0)  # This seems long - necessary?
            self.end_phase("13_wait_confirmation")
        
        # Display results
        self.display_results()
        
        # Cleanup
        await browser_pool.close()
    
    def display_results(self):
        """Display timing analysis results"""
        print("\n" + "="*80)
        print("PHASE TIMING ANALYSIS")
        print("="*80)
        print(f"{'Phase':<30} {'Duration (s)':<15} {'Notes':<40}")
        print("-"*80)
        
        total_time = 0
        optimization_opportunities = []
        
        for phase_name in sorted(self.phase_times.keys()):
            if 'duration' in self.phase_times[phase_name]:
                duration = self.phase_times[phase_name]['duration']
                total_time += duration
                
                # Identify optimization opportunities
                notes = ""
                if duration > 3.0 and 'wait' not in phase_name.lower():
                    notes = "⚠️ Potential optimization"
                    optimization_opportunities.append((phase_name, duration))
                elif 'wait' in phase_name.lower() and duration > 5.0:
                    notes = "⏱️ Long wait - check if reducible"
                    optimization_opportunities.append((phase_name, duration))
                
                # Special formatting for sub-phases
                display_name = phase_name
                if phase_name.startswith('8'):
                    display_name = "  " + phase_name
                
                print(f"{display_name:<30} {duration:>6.2f}s        {notes:<40}")
        
        print("-"*80)
        print(f"{'TOTAL TIME':<30} {total_time:>6.2f}s")
        print("="*80)
        
        if optimization_opportunities:
            print("\n🎯 OPTIMIZATION OPPORTUNITIES:")
            for phase, duration in optimization_opportunities:
                print(f"  - {phase}: {duration:.2f}s")

async def main():
    """Run the phase analysis"""
    analyzer = BookingPhaseAnalyzer()
    await analyzer.analyze_booking_process()

if __name__ == "__main__":
    asyncio.run(main())