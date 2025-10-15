#!/usr/bin/env python3
"""
Comprehensive test script for LVBOT browser pool system
Tests browser pool initialization, health checks, and booking functionality
"""

import asyncio
import logging
import sys
import os
from datetime import datetime, timedelta
import traceback

# Add the project root to Python path
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from lvbot.utils.async_browser_pool import AsyncBrowserPool
from lvbot.utils.browser_health_checker import BrowserHealthChecker
from lvbot.utils.constants import ACUITY_EMBED_URL, COURT_CONFIG

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

class BrowserSystemTester:
    def __init__(self):
        self.browser_pool = None
        self.health_checker = None
        self.test_results = {
            'browser_pool_init': False,
            'health_checker_init': False,
            'health_checks_pass': False,
            'navigation_works': False,
            'booking_form_accessible': False,
            'errors': []
        }
    
    async def test_browser_pool_initialization(self):
        """Test browser pool initialization"""
        logger.info("🧪 Testing browser pool initialization...")
        
        try:
            self.browser_pool = AsyncBrowserPool(
                courts=[1, 2]  # Test with 2 courts for faster initialization
            )
            
            await self.browser_pool.start()
            
            if self.browser_pool.is_ready():
                logger.info("✅ Browser pool initialized successfully")
                self.test_results['browser_pool_init'] = True
                
                # Check pool size
                available_courts = self.browser_pool.get_available_courts()
                logger.info(f"📊 Browser pool size: {len(available_courts)} courts ready: {available_courts}")
                
                if self.browser_pool.is_fully_ready():
                    logger.info("🎯 All requested courts initialized successfully")
                else:
                    logger.warning("⚠️ Partial initialization - some courts may be unavailable")
                
            else:
                logger.error("❌ Browser pool failed to initialize")
                self.test_results['errors'].append("Browser pool initialization failed")
                
        except Exception as e:
            logger.error(f"❌ Browser pool initialization error: {e}")
            self.test_results['errors'].append(f"Browser pool init error: {str(e)}")
            traceback.print_exc()
    
    async def test_health_checker_initialization(self):
        """Test health checker initialization"""
        logger.info("🧪 Testing health checker initialization...")
        
        try:
            if not self.browser_pool:
                logger.error("❌ Cannot test health checker - browser pool not available")
                return
                
            self.health_checker = BrowserHealthChecker(
                browser_pool=self.browser_pool
            )
            
            logger.info("✅ Health checker initialized successfully")
            self.test_results['health_checker_init'] = True
            
        except Exception as e:
            logger.error(f"❌ Health checker initialization error: {e}")
            self.test_results['errors'].append(f"Health checker init error: {str(e)}")
            traceback.print_exc()
    
    async def test_health_checks(self):
        """Test health check execution"""
        logger.info("🧪 Testing health check execution...")
        
        try:
            if not self.health_checker:
                logger.error("❌ Cannot test health checks - health checker not available")
                return
                
            # Run a single health check
            logger.info("Running health check...")
            health_result = await self.health_checker.perform_pre_booking_health_check()
            
            if health_result:
                logger.info("✅ Health checks completed successfully")
                
                # Report health check results
                is_healthy = health_result.is_healthy()
                status_str = "✅ HEALTHY" if is_healthy else f"❌ {health_result.status.value.upper()}"
                logger.info(f"📊 Health check result: {status_str}")
                logger.info(f"💬 Message: {health_result.message}")
                
                if is_healthy:
                    self.test_results['health_checks_pass'] = True
                else:
                    self.test_results['errors'].append(f"Health check failed: {health_result.message}")
                    
            else:
                logger.error("❌ Health checks returned no results")
                self.test_results['errors'].append("Health checks returned no results")
                
        except Exception as e:
            logger.error(f"❌ Health check execution error: {e}")
            self.test_results['errors'].append(f"Health check error: {str(e)}")
            traceback.print_exc()
    
    async def test_navigation(self):
        """Test basic navigation to Club LaVilla"""
        logger.info("🧪 Testing navigation to Club LaVilla...")
        
        try:
            if not self.browser_pool:
                logger.error("❌ Cannot test navigation - browser pool not available")
                return
                
            # Get a page for court 1 from the pool
            available_courts = self.browser_pool.get_available_courts()
            if available_courts:
                court = available_courts[0]
                page = await self.browser_pool.get_page(court)
                
                if page:
                    logger.info(f"📱 Got page for court {court} for navigation test")
                    
                    # Navigate to Club LaVilla  
                    await page.goto(ACUITY_EMBED_URL, wait_until='networkidle')
                    
                    # Check if we reached the site
                    title = await page.title()
                    url = page.url
                    
                    logger.info(f"🌐 Navigated to: {url}")
                    logger.info(f"📄 Page title: {title}")
                    
                    if "lavilla" in url.lower() or "lavilla" in title.lower():
                        logger.info("✅ Successfully navigated to Club LaVilla")
                        self.test_results['navigation_works'] = True
                    else:
                        logger.warning(f"⚠️ Navigation may have redirected - URL: {url}")
                else:
                    logger.error("❌ Could not get page from pool")
                    self.test_results['errors'].append("Could not get page from pool")
            else:
                logger.error("❌ No courts available in pool")
                self.test_results['errors'].append("No courts available in pool")
                
        except Exception as e:
            logger.error(f"❌ Navigation test error: {e}")
            self.test_results['errors'].append(f"Navigation error: {str(e)}")
            traceback.print_exc()
    
    async def test_booking_form_access(self):
        """Test access to booking form"""
        logger.info("🧪 Testing booking form accessibility...")
        
        try:
            if not self.browser_pool:
                logger.error("❌ Cannot test booking form - browser pool not available")
                return
                
            # Get a page for court 1 from the pool
            available_courts = self.browser_pool.get_available_courts()
            if available_courts:
                court = available_courts[0]
                page = await self.browser_pool.get_page(court)
                
                if page:
                    # Create a direct URL for a future date (to avoid booking conflicts)
                    test_date = datetime.now() + timedelta(days=3)
                    test_time = "09:00"
                    # Use Court 1 configuration for testing
                    appointment_id = COURT_CONFIG[1]['appointment_id']
                    booking_url = f"{ACUITY_EMBED_URL}/7d558012/appointment/{appointment_id}/calendar/{COURT_CONFIG[1]['calendar_id']}/datetime/{test_date.strftime('%Y-%m-%d')}T{test_time}:00-06:00?appointmentTypeIds[]={appointment_id}"
                    
                    logger.info(f"🔗 Testing booking URL: {booking_url}")
                    
                    # Navigate to booking form
                    await page.goto(booking_url, wait_until='networkidle')
                    
                    # Wait a moment for form to load
                    await asyncio.sleep(2)
                    
                    # Check if booking form elements are present
                    form_elements = {
                        'firstName': 'input[name="client.firstName"]',
                        'lastName': 'input[name="client.lastName"]', 
                        'phone': 'input[name="client.phone"]',
                        'email': 'input[name="client.email"]'
                    }
                    
                    elements_found = 0
                    for field_name, selector in form_elements.items():
                        try:
                            element = await page.wait_for_selector(selector, timeout=5000)
                            if element:
                                elements_found += 1
                                logger.info(f"  ✅ Found {field_name} field")
                        except:
                            logger.info(f"  ❌ Missing {field_name} field")
                    
                    if elements_found >= 3:  # Most form fields found
                        logger.info("✅ Booking form is accessible")
                        self.test_results['booking_form_accessible'] = True
                    else:
                        logger.warning(f"⚠️ Booking form partially accessible ({elements_found}/4 fields)")
                else:
                    logger.error("❌ Could not get page from pool")
                    self.test_results['errors'].append("Could not get page from pool for booking test")
            else:
                logger.error("❌ No courts available for booking test")
                self.test_results['errors'].append("No courts available for booking test")
                
        except Exception as e:
            logger.error(f"❌ Booking form test error: {e}")
            self.test_results['errors'].append(f"Booking form error: {str(e)}")
            traceback.print_exc()
    
    async def cleanup(self):
        """Clean up resources"""
        logger.info("🧹 Cleaning up test resources...")
        
        try:
            # Health checker doesn't need explicit cleanup
            if self.browser_pool:
                await self.browser_pool.stop()
                
            logger.info("✅ Cleanup completed")
            
        except Exception as e:
            logger.error(f"❌ Cleanup error: {e}")
    
    def print_test_summary(self):
        """Print a summary of test results"""
        logger.info("\n" + "="*60)
        logger.info("🧪 BROWSER SYSTEM TEST SUMMARY")
        logger.info("="*60)
        
        # Test results
        tests = [
            ("Browser Pool Initialization", self.test_results['browser_pool_init']),
            ("Health Checker Initialization", self.test_results['health_checker_init']),
            ("Health Checks Pass", self.test_results['health_checks_pass']),
            ("Navigation Works", self.test_results['navigation_works']),
            ("Booking Form Accessible", self.test_results['booking_form_accessible'])
        ]
        
        passed = 0
        total = len(tests)
        
        for test_name, result in tests:
            status = "✅ PASS" if result else "❌ FAIL"
            logger.info(f"{status} - {test_name}")
            if result:
                passed += 1
        
        logger.info(f"\n📊 Overall Results: {passed}/{total} tests passed")
        
        # Errors
        if self.test_results['errors']:
            logger.info("\n❌ ERRORS ENCOUNTERED:")
            for error in self.test_results['errors']:
                logger.info(f"  • {error}")
        
        # System status
        logger.info(f"\n🏁 SYSTEM STATUS:")
        if passed == total:
            logger.info("✅ SYSTEM FULLY FUNCTIONAL - Ready for production use")
        elif passed >= total * 0.8:  # 80% pass rate
            logger.info("⚠️  SYSTEM MOSTLY FUNCTIONAL - Minor issues need attention")
        else:
            logger.info("❌ SYSTEM NEEDS MAJOR FIXES - Not ready for production")
        
        logger.info("="*60)
    
    async def run_all_tests(self):
        """Run all tests in sequence"""
        logger.info("🚀 Starting comprehensive browser system tests...")
        
        try:
            await self.test_browser_pool_initialization()
            await self.test_health_checker_initialization()
            await self.test_health_checks()
            await self.test_navigation()
            await self.test_booking_form_access()
            
        finally:
            await self.cleanup()
            self.print_test_summary()

async def main():
    """Main test execution"""
    tester = BrowserSystemTester()
    await tester.run_all_tests()

if __name__ == "__main__":
    # Run the tests
    asyncio.run(main())