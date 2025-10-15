"""
Browser Health Checker Module
============================

PURPOSE: Monitor and validate browser pool health before critical operations
PATTERN: Proactive health monitoring to prevent booking failures
SCOPE: AsyncBrowserPool health validation

This module provides comprehensive health checks for the browser pool to
ensure bookings have the best chance of success by detecting issues early.
"""

import asyncio
import logging
from typing import Dict, List, Optional, Any
from datetime import datetime
from enum import Enum
from dataclasses import dataclass
from playwright.async_api import Page

from lvbot.utils.constants import BrowserTimeouts, COURT_CONFIG

logger = logging.getLogger(__name__)


class HealthStatus(Enum):
    """Health status levels for browser components"""
    HEALTHY = "healthy"
    DEGRADED = "degraded"
    CRITICAL = "critical"
    FAILED = "failed"


@dataclass
class HealthCheckResult:
    """Result of a health check operation"""
    status: HealthStatus
    message: str
    timestamp: datetime
    details: Dict[str, Any] = None
    
    def is_healthy(self) -> bool:
        """Check if the result indicates healthy status"""
        return self.status == HealthStatus.HEALTHY


@dataclass
class CourtHealthStatus:
    """Health status for an individual court browser"""
    court_number: int
    status: HealthStatus
    last_check: datetime
    page_url: Optional[str] = None
    error_message: Optional[str] = None
    response_time_ms: Optional[int] = None
    checks_passed: Dict[str, bool] = None


class BrowserHealthChecker:
    """
    Health checker for browser pool and individual court browsers
    
    Performs various health checks to ensure browsers are ready for bookings:
    - Page connectivity and responsiveness
    - JavaScript execution capability
    - Network connectivity to booking site
    - DOM query functionality
    - Resource availability
    """
    
    def __init__(self, browser_pool):
        """
        Initialize health checker with browser pool reference
        
        Args:
            browser_pool: AsyncBrowserPool instance to monitor
        """
        self.browser_pool = browser_pool
        self.last_full_check: Optional[datetime] = None
        self.court_health_cache: Dict[int, CourtHealthStatus] = {}
    
    async def perform_pre_booking_health_check(self) -> HealthCheckResult:
        """
        Main health check before attempting bookings
        
        Performs comprehensive health validation of the browser pool
        to ensure maximum chance of booking success.
        
        Returns:
            HealthCheckResult with overall pool health status
        """
        logger.info("🏥 Starting pre-booking health check...")
        start_time = datetime.now()
        
        try:
            # First check overall pool health
            pool_health = await self.check_pool_health()
            if pool_health.status == HealthStatus.FAILED:
                return pool_health
            
            # Check individual court health in parallel
            available_courts = self.browser_pool.get_available_courts()
            if not available_courts:
                return HealthCheckResult(
                    status=HealthStatus.FAILED,
                    message="No courts available in browser pool",
                    timestamp=datetime.now()
                )
            
            # Parallel health checks for all courts
            court_tasks = []
            for court_num in available_courts:
                court_tasks.append(self.check_court_health(court_num))
            
            court_results = await asyncio.gather(*court_tasks, return_exceptions=True)
            
            # Analyze results
            healthy_courts = 0
            degraded_courts = 0
            failed_courts = 0
            court_details = {}
            
            for i, result in enumerate(court_results):
                court_num = available_courts[i]
                if isinstance(result, Exception):
                    logger.error(f"Court {court_num} health check failed: {result}")
                    failed_courts += 1
                    court_details[f"court_{court_num}"] = "error"
                else:
                    court_details[f"court_{court_num}"] = result.status.value
                    if result.status == HealthStatus.HEALTHY:
                        healthy_courts += 1
                    elif result.status == HealthStatus.DEGRADED:
                        degraded_courts += 1
                    else:
                        failed_courts += 1
            
            # Determine overall status
            elapsed_ms = int((datetime.now() - start_time).total_seconds() * 1000)
            
            if healthy_courts == len(available_courts):
                status = HealthStatus.HEALTHY
                message = f"All {healthy_courts} courts are healthy"
            elif healthy_courts > 0:
                status = HealthStatus.DEGRADED
                message = f"{healthy_courts} healthy, {degraded_courts} degraded, {failed_courts} failed"
            elif degraded_courts > 0:
                status = HealthStatus.CRITICAL
                message = f"No healthy courts, {degraded_courts} degraded, {failed_courts} failed"
            else:
                status = HealthStatus.FAILED
                message = f"All {failed_courts} courts have failed"
            
            self.last_full_check = datetime.now()
            
            return HealthCheckResult(
                status=status,
                message=message,
                timestamp=datetime.now(),
                details={
                    "courts": court_details,
                    "healthy_count": healthy_courts,
                    "degraded_count": degraded_courts,
                    "failed_count": failed_courts,
                    "total_courts": len(available_courts),
                    "check_duration_ms": elapsed_ms
                }
            )
            
        except Exception as e:
            logger.error(f"Pre-booking health check failed: {e}")
            return HealthCheckResult(
                status=HealthStatus.FAILED,
                message=f"Health check error: {str(e)}",
                timestamp=datetime.now()
            )
    
    async def check_pool_health(self) -> HealthCheckResult:
        """
        Check overall browser pool status
        
        Validates:
        - Pool initialization state
        - Browser instance availability
        - Critical operation status
        
        Returns:
            HealthCheckResult for the overall pool
        """
        try:
            # Check if pool is ready
            if not self.browser_pool.is_ready():
                return HealthCheckResult(
                    status=HealthStatus.FAILED,
                    message="Browser pool is not ready",
                    timestamp=datetime.now()
                )
            
            # Check browser instance
            if not self.browser_pool.browser or not self.browser_pool.browser.is_connected():
                return HealthCheckResult(
                    status=HealthStatus.FAILED,
                    message="Browser instance is not connected",
                    timestamp=datetime.now()
                )
            
            # Check if critical operation in progress
            if self.browser_pool.is_critical_operation_in_progress():
                return HealthCheckResult(
                    status=HealthStatus.DEGRADED,
                    message="Critical operation in progress - pool is busy",
                    timestamp=datetime.now(),
                    details={"critical_operation": True}
                )
            
            # Check partial initialization
            if self.browser_pool.is_partially_ready:
                available = len(self.browser_pool.get_available_courts())
                requested = len(self.browser_pool.courts)
                return HealthCheckResult(
                    status=HealthStatus.DEGRADED,
                    message=f"Pool partially initialized: {available}/{requested} courts",
                    timestamp=datetime.now(),
                    details={
                        "available_courts": available,
                        "requested_courts": requested,
                        "partial_ready": True
                    }
                )
            
            return HealthCheckResult(
                status=HealthStatus.HEALTHY,
                message="Browser pool is healthy",
                timestamp=datetime.now()
            )
            
        except Exception as e:
            logger.error(f"Pool health check error: {e}")
            return HealthCheckResult(
                status=HealthStatus.FAILED,
                message=f"Pool health check failed: {str(e)}",
                timestamp=datetime.now()
            )
    
    async def check_court_health(self, court_number: int) -> CourtHealthStatus:
        """
        Check health of a specific court browser
        
        Performs multiple checks:
        - Page connectivity
        - JavaScript execution
        - Network access to booking site
        - DOM query capability
        
        Args:
            court_number: Court number to check (1, 2, or 3)
            
        Returns:
            CourtHealthStatus with detailed health information
        """
        start_time = datetime.now()
        checks_passed = {
            "page_access": False,
            "javascript": False,
            "network": False,
            "dom_query": False
        }
        
        try:
            # Get page with lock
            async with self.browser_pool.lock:
                page = self.browser_pool.pages.get(court_number)
                if not page:
                    return CourtHealthStatus(
                        court_number=court_number,
                        status=HealthStatus.FAILED,
                        last_check=datetime.now(),
                        error_message="Page not found in pool"
                    )
            
            # Test browser responsiveness
            responsiveness_result = await self.test_browser_responsiveness(page, court_number)
            
            # Update checks based on responsiveness test
            if responsiveness_result.get("url_accessible"):
                checks_passed["page_access"] = True
            if responsiveness_result.get("javascript_works"):
                checks_passed["javascript"] = True
            if responsiveness_result.get("network_ok"):
                checks_passed["network"] = True
            if responsiveness_result.get("dom_queryable"):
                checks_passed["dom_query"] = True
            
            # Calculate response time
            response_time_ms = int((datetime.now() - start_time).total_seconds() * 1000)
            
            # Determine status based on checks
            passed_count = sum(checks_passed.values())
            if passed_count == 4:
                status = HealthStatus.HEALTHY
            elif passed_count >= 3:
                status = HealthStatus.DEGRADED
            elif passed_count >= 1:
                status = HealthStatus.CRITICAL
            else:
                status = HealthStatus.FAILED
            
            # Cache result
            result = CourtHealthStatus(
                court_number=court_number,
                status=status,
                last_check=datetime.now(),
                page_url=responsiveness_result.get("current_url"),
                response_time_ms=response_time_ms,
                checks_passed=checks_passed,
                error_message=responsiveness_result.get("error")
            )
            
            self.court_health_cache[court_number] = result
            
            logger.info(f"Court {court_number} health: {status.value} "
                       f"({passed_count}/4 checks passed in {response_time_ms}ms)")
            
            return result
            
        except Exception as e:
            logger.error(f"Court {court_number} health check error: {e}")
            return CourtHealthStatus(
                court_number=court_number,
                status=HealthStatus.FAILED,
                last_check=datetime.now(),
                error_message=str(e)
            )
    
    async def test_browser_responsiveness(self, page: Page, court_number: int) -> Dict[str, Any]:
        """
        Test if browser can perform basic actions
        
        Tests:
        - URL accessibility
        - JavaScript execution
        - Network connectivity to booking site
        - DOM query capability
        
        Args:
            page: Playwright Page instance
            court_number: Court number for logging
            
        Returns:
            Dict with test results
        """
        results = {
            "url_accessible": False,
            "javascript_works": False,
            "network_ok": False,
            "dom_queryable": False,
            "current_url": None,
            "error": None
        }
        
        try:
            # 1. Test URL access
            try:
                current_url = page.url
                results["current_url"] = current_url
                results["url_accessible"] = True
            except Exception as e:
                logger.warning(f"Court {court_number}: URL access failed - {e}")
                results["error"] = f"URL access failed: {str(e)}"
                return results
            
            # 2. Test JavaScript execution
            try:
                js_result = await page.evaluate("() => 1 + 1")
                if js_result == 2:
                    results["javascript_works"] = True
            except Exception as e:
                logger.warning(f"Court {court_number}: JavaScript execution failed - {e}")
            
            # 3. Test network connectivity (check if on booking site)
            try:
                if current_url and ("clublavilla.as.me" in current_url or "acuityscheduling" in current_url):
                    results["network_ok"] = True
                else:
                    # Try to check if we can reach the booking site
                    can_reach = await page.evaluate("""
                        () => {
                            return window.location.hostname.includes('as.me') || 
                                   window.location.hostname.includes('acuityscheduling');
                        }
                    """)
                    results["network_ok"] = bool(can_reach)
            except Exception as e:
                logger.warning(f"Court {court_number}: Network check failed - {e}")
            
            # 4. Test DOM query capability
            try:
                # Try to find any button element
                button_count = await page.evaluate("() => document.querySelectorAll('button').length")
                results["dom_queryable"] = button_count > 0
            except Exception as e:
                logger.warning(f"Court {court_number}: DOM query failed - {e}")
            
            return results
            
        except Exception as e:
            logger.error(f"Court {court_number}: Responsiveness test failed - {e}")
            results["error"] = f"Responsiveness test failed: {str(e)}"
            return results
    
    def get_court_health_summary(self) -> Dict[int, str]:
        """
        Get summary of all court health statuses
        
        Returns:
            Dict mapping court number to health status string
        """
        summary = {}
        for court_num, health in self.court_health_cache.items():
            summary[court_num] = health.status.value
        return summary
    
    def requires_pool_restart(self) -> bool:
        """
        Check if browser pool requires restart based on health
        
        Returns:
            True if pool should be restarted
        """
        # Check if all courts have failed
        if not self.court_health_cache:
            return False
        
        failed_count = sum(1 for health in self.court_health_cache.values()
                          if health.status == HealthStatus.FAILED)
        
        return failed_count == len(self.court_health_cache) and len(self.court_health_cache) > 0