#!/usr/bin/env python3
"""
Browser Pool Test Script
========================

PURPOSE: Test and debug browser pool functionality to identify issues
SCOPE: AsyncBrowserPool validation, health checking, basic operations

This script performs comprehensive testing of the browser pool to determine:
1. Whether browsers can actually initialize and navigate
2. If the health checker is the only issue or if there are deeper problems
3. Network connectivity to the booking site
4. Basic browser operations like page.evaluate()

Run this script to diagnose browser pool failures.
"""
from utils.tracking import t

import asyncio
import logging
from datetime import datetime
from typing import Dict, Any
import sys
import os

# Add project root to path
sys.path.append(os.path.dirname(__file__))

from lvbot.utils.async_browser_pool import AsyncBrowserPool
from lvbot.utils.browser_health_checker import BrowserHealthChecker, HealthStatus
from lvbot.utils.constants import COURT_CONFIG

# Set up logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)


class BrowserPoolTester:
    """Comprehensive browser pool testing and diagnostics"""
    
    def __init__(self):
        t('archive.testing.tests.test_browser_pool.BrowserPoolTester.__init__')
        self.browser_pool = None
        self.health_checker = None
        self.test_results = {
            'pool_initialization': False,
            'browser_connection': False,
            'pages_created': {},
            'navigation_test': {},
            'javascript_execution': {},
            'dom_queries': {},
            'network_connectivity': {},
            'health_checker_results': {},
            'errors_encountered': []
        }
    
    async def run_all_tests(self) -> Dict[str, Any]:
        """
        Run comprehensive browser pool tests
        
        Returns:
            Dict with detailed test results
        """
        t('archive.testing.tests.test_browser_pool.BrowserPoolTester.run_all_tests')
        logger.info("🧪 Starting comprehensive browser pool testing...")
        
        try:
            # Test 1: Initialize browser pool
            await self.test_pool_initialization()
            
            if not self.test_results['pool_initialization']:
                logger.error("❌ Browser pool initialization failed - skipping further tests")
                return self.test_results
            
            # Test 2: Test browser connection
            await self.test_browser_connection()
            
            # Test 3: Test page creation
            await self.test_page_creation()
            
            # Test 4: Test basic navigation
            await self.test_navigation()
            
            # Test 5: Test JavaScript execution (without problematic timeout)
            await self.test_javascript_execution()
            
            # Test 6: Test DOM queries
            await self.test_dom_queries()
            
            # Test 7: Test network connectivity
            await self.test_network_connectivity()
            
            # Test 8: Test health checker (the problematic one)
            await self.test_health_checker()
            
            # Final analysis
            self.analyze_results()
            
        except Exception as e:
            logger.error(f"❌ Test execution failed: {e}")
            self.test_results['errors_encountered'].append(f"Test execution error: {str(e)}")
        
        finally:
            # Cleanup
            await self.cleanup()
        
        return self.test_results
    
    async def test_pool_initialization(self):
        """Test browser pool initialization"""
        t('archive.testing.tests.test_browser_pool.BrowserPoolTester.test_pool_initialization')
        logger.info("🔧 Testing browser pool initialization...")
        
        try:
            # Initialize with all 3 courts like in real scenarios
            test_courts = [1, 2, 3]
            
            self.browser_pool = AsyncBrowserPool(courts=test_courts)
            await self.browser_pool.start()
            
            self.test_results['pool_initialization'] = True
            logger.info("✅ Browser pool initialization successful")
            
            # Initialize health checker
            self.health_checker = BrowserHealthChecker(self.browser_pool)
            
        except Exception as e:
            logger.error(f"❌ Browser pool initialization failed: {e}")
            self.test_results['errors_encountered'].append(f"Pool init error: {str(e)}")
    
    async def test_browser_connection(self):
        """Test browser connection status"""
        t('archive.testing.tests.test_browser_pool.BrowserPoolTester.test_browser_connection')
        logger.info("🌐 Testing browser connection...")
        
        try:
            if self.browser_pool.browser and self.browser_pool.browser.is_connected():
                self.test_results['browser_connection'] = True
                logger.info("✅ Browser connection is active")
            else:
                logger.error("❌ Browser is not connected")
                self.test_results['errors_encountered'].append("Browser not connected")
        except Exception as e:
            logger.error(f"❌ Browser connection test failed: {e}")
            self.test_results['errors_encountered'].append(f"Browser connection error: {str(e)}")
    
    async def test_page_creation(self):
        """Test page creation for each court"""
        t('archive.testing.tests.test_browser_pool.BrowserPoolTester.test_page_creation')
        logger.info("📄 Testing page creation...")
        
        available_courts = self.browser_pool.get_available_courts()
        
        for court_num in available_courts:
            try:
                async with self.browser_pool.lock:
                    page = self.browser_pool.pages.get(court_num)
                
                if page:
                    self.test_results['pages_created'][court_num] = True
                    logger.info(f"✅ Court {court_num} page exists")
                else:
                    self.test_results['pages_created'][court_num] = False
                    logger.error(f"❌ Court {court_num} page not found")
                    
            except Exception as e:
                logger.error(f"❌ Court {court_num} page test failed: {e}")
                self.test_results['pages_created'][court_num] = False
                self.test_results['errors_encountered'].append(f"Court {court_num} page error: {str(e)}")
    
    async def test_navigation(self):
        """Test basic navigation to booking site"""
        t('archive.testing.tests.test_browser_pool.BrowserPoolTester.test_navigation')
        logger.info("🧭 Testing navigation to booking site...")
        
        booking_url = "https://clublavilla.as.me/schedule/7d558012/appointment/16021953/calendar/4291312"
        
        for court_num in self.browser_pool.get_available_courts():
            try:
                async with self.browser_pool.lock:
                    page = self.browser_pool.pages.get(court_num)
                
                if not page:
                    continue
                
                # Test navigation
                await page.goto(booking_url, timeout=30000)
                current_url = page.url
                
                if "clublavilla.as.me" in current_url:
                    self.test_results['navigation_test'][court_num] = True
                    logger.info(f"✅ Court {court_num} navigation successful: {current_url}")
                else:
                    self.test_results['navigation_test'][court_num] = False
                    logger.error(f"❌ Court {court_num} navigation failed: {current_url}")
                    
            except Exception as e:
                logger.error(f"❌ Court {court_num} navigation failed: {e}")
                self.test_results['navigation_test'][court_num] = False
                self.test_results['errors_encountered'].append(f"Court {court_num} navigation error: {str(e)}")
    
    async def test_javascript_execution(self):
        """Test JavaScript execution without timeout wrapper"""
        t('archive.testing.tests.test_browser_pool.BrowserPoolTester.test_javascript_execution')
        logger.info("⚡ Testing JavaScript execution...")
        
        for court_num in self.browser_pool.get_available_courts():
            try:
                async with self.browser_pool.lock:
                    page = self.browser_pool.pages.get(court_num)
                
                if not page:
                    continue
                
                # Test simple JavaScript execution (without asyncio.wait_for wrapper)
                result = await page.evaluate("() => 1 + 1")
                
                if result == 2:
                    self.test_results['javascript_execution'][court_num] = True
                    logger.info(f"✅ Court {court_num} JavaScript execution works")
                else:
                    self.test_results['javascript_execution'][court_num] = False
                    logger.error(f"❌ Court {court_num} JavaScript returned: {result}")
                    
            except Exception as e:
                logger.error(f"❌ Court {court_num} JavaScript execution failed: {e}")
                self.test_results['javascript_execution'][court_num] = False
                self.test_results['errors_encountered'].append(f"Court {court_num} JS error: {str(e)}")
    
    async def test_dom_queries(self):
        """Test DOM query capabilities"""
        t('archive.testing.tests.test_browser_pool.BrowserPoolTester.test_dom_queries')
        logger.info("🔍 Testing DOM queries...")
        
        for court_num in self.browser_pool.get_available_courts():
            try:
                async with self.browser_pool.lock:
                    page = self.browser_pool.pages.get(court_num)
                
                if not page:
                    continue
                
                # Test DOM query without timeout wrapper
                button_count = await page.evaluate("() => document.querySelectorAll('button').length")
                
                if button_count >= 0:  # Even 0 buttons is a successful query
                    self.test_results['dom_queries'][court_num] = True
                    logger.info(f"✅ Court {court_num} DOM query works: {button_count} buttons found")
                else:
                    self.test_results['dom_queries'][court_num] = False
                    
            except Exception as e:
                logger.error(f"❌ Court {court_num} DOM query failed: {e}")
                self.test_results['dom_queries'][court_num] = False
                self.test_results['errors_encountered'].append(f"Court {court_num} DOM error: {str(e)}")
    
    async def test_network_connectivity(self):
        """Test network connectivity to booking site"""
        t('archive.testing.tests.test_browser_pool.BrowserPoolTester.test_network_connectivity')
        logger.info("🌍 Testing network connectivity...")
        
        for court_num in self.browser_pool.get_available_courts():
            try:
                async with self.browser_pool.lock:
                    page = self.browser_pool.pages.get(court_num)
                
                if not page:
                    continue
                
                # Test network connectivity without timeout wrapper
                hostname_check = await page.evaluate("""
                    () => {
                        return window.location.hostname.includes('as.me') || 
                               window.location.hostname.includes('acuityscheduling');
                    }
                """)
                
                if hostname_check:
                    self.test_results['network_connectivity'][court_num] = True
                    logger.info(f"✅ Court {court_num} network connectivity confirmed")
                else:
                    self.test_results['network_connectivity'][court_num] = False
                    logger.warning(f"⚠️  Court {court_num} not on booking site")
                    
            except Exception as e:
                logger.error(f"❌ Court {court_num} network test failed: {e}")
                self.test_results['network_connectivity'][court_num] = False
                self.test_results['errors_encountered'].append(f"Court {court_num} network error: {str(e)}")
    
    async def test_health_checker(self):
        """Test the health checker that's causing the original error"""
        t('archive.testing.tests.test_browser_pool.BrowserPoolTester.test_health_checker')
        logger.info("🏥 Testing health checker (this will likely fail)...")
        
        if not self.health_checker:
            logger.error("❌ Health checker not initialized")
            return
        
        try:
            # This should trigger the original error
            health_result = await self.health_checker.perform_pre_booking_health_check()
            
            self.test_results['health_checker_results'] = {
                'status': health_result.status.value,
                'message': health_result.message,
                'details': health_result.details
            }
            
            logger.info(f"Health check result: {health_result.status.value} - {health_result.message}")
            
        except Exception as e:
            logger.error(f"❌ Health checker failed as expected: {e}")
            self.test_results['health_checker_results'] = {
                'error': str(e)
            }
            self.test_results['errors_encountered'].append(f"Health checker error: {str(e)}")
    
    def analyze_results(self):
        """Analyze test results and provide diagnosis"""
        t('archive.testing.tests.test_browser_pool.BrowserPoolTester.analyze_results')
        logger.info("🔬 Analyzing test results...")
        
        # Count successful tests
        successful_areas = []
        failed_areas = []
        
        if self.test_results['pool_initialization']:
            successful_areas.append("Pool Initialization")
        else:
            failed_areas.append("Pool Initialization")
        
        if self.test_results['browser_connection']:
            successful_areas.append("Browser Connection")
        else:
            failed_areas.append("Browser Connection")
        
        # Page creation
        pages_success = sum(self.test_results['pages_created'].values())
        pages_total = len(self.test_results['pages_created'])
        if pages_success == pages_total and pages_total > 0:
            successful_areas.append("Page Creation")
        else:
            failed_areas.append(f"Page Creation ({pages_success}/{pages_total})")
        
        # Navigation
        nav_success = sum(self.test_results['navigation_test'].values())
        nav_total = len(self.test_results['navigation_test'])
        if nav_success == nav_total and nav_total > 0:
            successful_areas.append("Navigation")
        else:
            failed_areas.append(f"Navigation ({nav_success}/{nav_total})")
        
        # JavaScript
        js_success = sum(self.test_results['javascript_execution'].values())
        js_total = len(self.test_results['javascript_execution'])
        if js_success == js_total and js_total > 0:
            successful_areas.append("JavaScript Execution")
        else:
            failed_areas.append(f"JavaScript ({js_success}/{js_total})")
        
        # DOM Queries
        dom_success = sum(self.test_results['dom_queries'].values())
        dom_total = len(self.test_results['dom_queries'])
        if dom_success == dom_total and dom_total > 0:
            successful_areas.append("DOM Queries")
        else:
            failed_areas.append(f"DOM Queries ({dom_success}/{dom_total})")
        
        # Network
        net_success = sum(self.test_results['network_connectivity'].values())
        net_total = len(self.test_results['network_connectivity'])
        if net_success == net_total and net_total > 0:
            successful_areas.append("Network Connectivity")
        else:
            failed_areas.append(f"Network ({net_success}/{net_total})")
        
        # Health Checker
        if 'error' not in self.test_results['health_checker_results']:
            successful_areas.append("Health Checker")
        else:
            failed_areas.append("Health Checker")
        
        # Print results
        logger.info("=" * 60)
        logger.info("📊 TEST RESULTS SUMMARY")
        logger.info("=" * 60)
        
        if successful_areas:
            logger.info("✅ WORKING CORRECTLY:")
            for area in successful_areas:
                logger.info(f"   • {area}")
        
        if failed_areas:
            logger.info("❌ FAILING:")
            for area in failed_areas:
                logger.info(f"   • {area}")
        
        if self.test_results['errors_encountered']:
            logger.info("🐛 ERRORS ENCOUNTERED:")
            for error in self.test_results['errors_encountered']:
                logger.info(f"   • {error}")
        
        # Diagnosis
        logger.info("🔬 DIAGNOSIS:")
        if len(successful_areas) >= 6:  # Most things work
            logger.info("   Browser pool is mostly functional - likely just health checker bug")
        elif len(successful_areas) >= 3:
            logger.info("   Browser pool has partial functionality - mixed issues")
        else:
            logger.info("   Browser pool has fundamental problems - needs investigation")
    
    async def cleanup(self):
        """Clean up resources"""
        t('archive.testing.tests.test_browser_pool.BrowserPoolTester.cleanup')
        logger.info("🧹 Cleaning up...")
        
        try:
            if self.browser_pool:
                await self.browser_pool.stop()
        except Exception as e:
            logger.error(f"Cleanup error: {e}")


async def main():
    """Run the browser pool test"""
    t('archive.testing.tests.test_browser_pool.main')
    tester = BrowserPoolTester()
    
    try:
        results = await tester.run_all_tests()
        
        # Print final summary
        print("\n" + "=" * 80)
        print("🎯 FINAL DIAGNOSIS")
        print("=" * 80)
        
        if results['pool_initialization'] and results['browser_connection']:
            if 'error' in results['health_checker_results']:
                print("✅ RESULT: Browser pool is working - Health checker has a bug")
                print("🔧 RECOMMENDATION: Fix the Page.evaluate() timeout issue in health checker")
            else:
                print("✅ RESULT: Everything appears to be working")
        else:
            print("❌ RESULT: Browser pool has fundamental initialization issues")
            print("🔧 RECOMMENDATION: Fix browser pool initialization first")
        
        return results
        
    except Exception as e:
        logger.error(f"Main execution failed: {e}")
        return None


if __name__ == "__main__":
    results = asyncio.run(main())