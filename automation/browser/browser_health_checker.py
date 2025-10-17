"""
Browser Health Checker Module
============================

PURPOSE: Monitor and validate browser pool health before critical operations
PATTERN: Proactive health monitoring to prevent booking failures
SCOPE: AsyncBrowserPool health validation

This module provides comprehensive health checks for the browser pool to
ensure bookings have the best chance of success by detecting issues early.
"""
from tracking import t

import asyncio
import logging
from typing import Dict, List, Optional, Any
from datetime import datetime
from playwright.async_api import Page

from infrastructure.constants import BrowserTimeouts, COURT_CONFIG
from automation.browser.health.collectors import collect_court_signals, collect_pool_signals
from automation.browser.health.evaluators import (
    build_court_health_status,
    evaluate_court_signals,
    evaluate_pool_health,
    summarise_courts,
)
from automation.browser.health.types import CourtHealthStatus, HealthCheckResult, HealthStatus

logger = logging.getLogger(__name__)


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
        t('automation.browser.browser_health_checker.BrowserHealthChecker.__init__')
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
        t('automation.browser.browser_health_checker.BrowserHealthChecker.perform_pre_booking_health_check')
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

            healthy_courts = 0
            degraded_courts = 0
            failed_courts = 0
            court_statuses: List[CourtHealthStatus] = []

            for i, result in enumerate(court_results):
                court_num = available_courts[i]
                if isinstance(result, Exception):
                    logger.error("Court %s health check failed: %s", court_num, result)
                    failed_courts += 1
                    court_statuses.append(
                        CourtHealthStatus(
                            court_number=court_num,
                            status=HealthStatus.FAILED,
                            last_check=datetime.now(),
                            error_message=str(result),
                        )
                    )
                    continue
                court_statuses.append(result)
                if result.status == HealthStatus.HEALTHY:
                    healthy_courts += 1
                elif result.status == HealthStatus.DEGRADED:
                    degraded_courts += 1
                else:
                    failed_courts += 1

            court_details = summarise_courts(court_statuses)
            
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
        t('automation.browser.browser_health_checker.BrowserHealthChecker.check_pool_health')
        try:
            signals = await collect_pool_signals(self.browser_pool)
            return evaluate_pool_health(signals)
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
        t('automation.browser.browser_health_checker.BrowserHealthChecker.check_court_health')
        start_time = datetime.now()

        try:
            async with self.browser_pool.lock:
                page = self.browser_pool.pages.get(court_number)
                if not page:
                    return CourtHealthStatus(
                        court_number=court_number,
                        status=HealthStatus.FAILED,
                        last_check=datetime.now(),
                        error_message="Page not found in pool",
                    )

            signals = await collect_court_signals(page, logger=logger, court_number=court_number)
            response_time_ms = int((datetime.now() - start_time).total_seconds() * 1000)
            evaluation = evaluate_court_signals(court_number, signals, response_time_ms=response_time_ms)
            result = build_court_health_status(
                court_number,
                evaluation,
                signals,
                response_time_ms=response_time_ms,
            )

            self.court_health_cache[court_number] = result
            logger.info(
                "Court %s health: %s (%s/4 checks passed in %sms)",
                court_number,
                result.status.value,
                sum(evaluation.checks_passed.values()),
                response_time_ms,
            )

            return result

        except Exception as e:
            logger.error(f"Court {court_number} health check error: {e}")
            return CourtHealthStatus(
                court_number=court_number,
                status=HealthStatus.FAILED,
                last_check=datetime.now(),
                error_message=str(e),
            )
    
            
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
        t('automation.browser.browser_health_checker.BrowserHealthChecker.get_court_health_summary')
        return summarise_courts(self.court_health_cache.values())
    
    def requires_pool_restart(self) -> bool:
        """
        Check if browser pool requires restart based on health
        
        Returns:
            True if pool should be restarted
        """
        t('automation.browser.browser_health_checker.BrowserHealthChecker.requires_pool_restart')
        # Check if all courts have failed
        if not self.court_health_cache:
            return False
        
        failed_count = sum(1 for health in self.court_health_cache.values()
                          if health.status == HealthStatus.FAILED)
        
        return failed_count == len(self.court_health_cache) and len(self.court_health_cache) > 0
