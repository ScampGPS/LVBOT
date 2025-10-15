"""
Browser Pool Recovery Service - Handles browser pool failures and recovery
==========================================================================

PURPOSE: Provides recovery strategies for browser pool failures to maintain bot availability
PATTERN: Multiple escalating recovery strategies from individual court to full restart
SCOPE: Browser pool recovery and emergency fallback mechanisms

This module provides resilient recovery from browser failures while maintaining
thread safety and async compatibility.
"""

import asyncio
import logging
from typing import Dict, List, Optional, Any, Tuple
from datetime import datetime
from enum import Enum
from dataclasses import dataclass, field
import traceback

logger = logging.getLogger(__name__)


class RecoveryStrategy(Enum):
    """Enumeration of available recovery strategies"""
    INDIVIDUAL_COURT = "individual_court"
    PARTIAL_POOL = "partial_pool"
    FULL_RESTART = "full_restart"
    EMERGENCY_FALLBACK = "emergency_fallback"


@dataclass
class RecoveryAttempt:
    """Track individual recovery attempt details"""
    strategy: RecoveryStrategy
    timestamp: datetime
    courts_affected: List[int]
    success: bool
    error_message: Optional[str] = None
    duration_seconds: float = 0.0


@dataclass
class RecoveryResult:
    """Result of a recovery operation"""
    success: bool
    strategy_used: RecoveryStrategy
    courts_recovered: List[int]
    courts_failed: List[int]
    message: str
    error_details: Optional[str] = None
    attempts: List[RecoveryAttempt] = field(default_factory=list)
    total_duration_seconds: float = 0.0


class BrowserPoolRecoveryService:
    """
    Service for recovering browser pool from various failure scenarios
    
    Recovery strategies escalate from least to most disruptive:
    1. Individual court recovery - Recreate single browser
    2. Partial pool recovery - Recreate multiple affected browsers
    3. Full pool restart - Complete pool recreation
    4. Emergency fallback - Activate minimal backup system
    """
    
    def __init__(self, browser_pool):
        """
        Initialize recovery service
        
        Args:
            browser_pool: AsyncBrowserPool instance to manage
        """
        self.browser_pool = browser_pool
        self.recovery_history: List[RecoveryAttempt] = []
        self.emergency_browser = None
        self.recovery_lock = asyncio.Lock()
        self.max_recovery_attempts = 3
        self.recovery_timeout = 60  # seconds per attempt
        
    async def recover_browser_pool(self, failed_courts: List[int] = None, 
                                  error_context: str = None) -> RecoveryResult:
        """
        Main recovery method that determines and executes appropriate recovery strategy
        
        Args:
            failed_courts: List of court numbers that failed (None = all courts)
            error_context: Description of the error that triggered recovery
            
        Returns:
            RecoveryResult with recovery outcome details
        """
        async with self.recovery_lock:
            start_time = datetime.now()
            all_attempts = []
            
            logger.warning(f"🔧 Starting browser pool recovery. Failed courts: {failed_courts}, Error: {error_context}")
            
            # Determine initial strategy based on failure scope
            if failed_courts is None:
                # Complete failure - start with full restart
                strategies = [RecoveryStrategy.FULL_RESTART, RecoveryStrategy.EMERGENCY_FALLBACK]
            elif len(failed_courts) == 1:
                # Single court failure
                strategies = [RecoveryStrategy.INDIVIDUAL_COURT, RecoveryStrategy.PARTIAL_POOL, 
                            RecoveryStrategy.FULL_RESTART, RecoveryStrategy.EMERGENCY_FALLBACK]
            else:
                # Multiple court failure
                strategies = [RecoveryStrategy.PARTIAL_POOL, RecoveryStrategy.FULL_RESTART, 
                            RecoveryStrategy.EMERGENCY_FALLBACK]
            
            # Try strategies in order until one succeeds
            for strategy in strategies:
                logger.info(f"🔄 Attempting recovery strategy: {strategy.value}")
                
                try:
                    if strategy == RecoveryStrategy.INDIVIDUAL_COURT:
                        result = await self.recover_individual_court(failed_courts[0])
                    elif strategy == RecoveryStrategy.PARTIAL_POOL:
                        result = await self.recover_partial_pool(failed_courts or self.browser_pool.courts)
                    elif strategy == RecoveryStrategy.FULL_RESTART:
                        result = await self.perform_full_pool_restart()
                    elif strategy == RecoveryStrategy.EMERGENCY_FALLBACK:
                        result = await self.activate_emergency_fallback()
                    
                    all_attempts.extend(result.attempts)
                    
                    if result.success:
                        total_duration = (datetime.now() - start_time).total_seconds()
                        result.total_duration_seconds = total_duration
                        result.attempts = all_attempts
                        logger.info(f"✅ Recovery successful using {strategy.value} in {total_duration:.1f}s")
                        return result
                    else:
                        logger.warning(f"❌ Recovery strategy {strategy.value} failed: {result.message}")
                        
                except Exception as e:
                    logger.error(f"💥 Exception during {strategy.value} recovery: {e}")
                    logger.error(traceback.format_exc())
                    
                    # Record failed attempt
                    attempt = RecoveryAttempt(
                        strategy=strategy,
                        timestamp=datetime.now(),
                        courts_affected=failed_courts or self.browser_pool.courts,
                        success=False,
                        error_message=str(e),
                        duration_seconds=(datetime.now() - start_time).total_seconds()
                    )
                    all_attempts.append(attempt)
            
            # All strategies failed
            total_duration = (datetime.now() - start_time).total_seconds()
            return RecoveryResult(
                success=False,
                strategy_used=RecoveryStrategy.EMERGENCY_FALLBACK,
                courts_recovered=[],
                courts_failed=failed_courts or self.browser_pool.courts,
                message="All recovery strategies failed",
                error_details=f"Tried {len(strategies)} strategies over {total_duration:.1f}s",
                attempts=all_attempts,
                total_duration_seconds=total_duration
            )
    
    async def recover_individual_court(self, court_number: int) -> RecoveryResult:
        """
        Recover a single court browser
        
        Args:
            court_number: Court number to recover (1, 2, or 3)
            
        Returns:
            RecoveryResult with recovery outcome
        """
        start_time = datetime.now()
        attempt = RecoveryAttempt(
            strategy=RecoveryStrategy.INDIVIDUAL_COURT,
            timestamp=start_time,
            courts_affected=[court_number],
            success=False
        )
        
        try:
            logger.info(f"🔧 Recovering individual court: {court_number}")
            
            # Close existing page and context if they exist
            if court_number in self.browser_pool.pages:
                try:
                    await self.browser_pool.pages[court_number].close()
                except Exception as e:
                    logger.debug(f"Error closing page for court {court_number}: {e}")
                del self.browser_pool.pages[court_number]
            
            if court_number in self.browser_pool.contexts:
                try:
                    await self.browser_pool.contexts[court_number].close()
                except Exception as e:
                    logger.debug(f"Error closing context for court {court_number}: {e}")
                del self.browser_pool.contexts[court_number]
            
            # Recreate the court page with retry logic
            success = await self.browser_pool._create_and_navigate_court_page_with_retry(court_number)
            
            attempt.success = success
            attempt.duration_seconds = (datetime.now() - start_time).total_seconds()
            
            if success:
                return RecoveryResult(
                    success=True,
                    strategy_used=RecoveryStrategy.INDIVIDUAL_COURT,
                    courts_recovered=[court_number],
                    courts_failed=[],
                    message=f"Successfully recovered court {court_number}",
                    attempts=[attempt]
                )
            else:
                return RecoveryResult(
                    success=False,
                    strategy_used=RecoveryStrategy.INDIVIDUAL_COURT,
                    courts_recovered=[],
                    courts_failed=[court_number],
                    message=f"Failed to recover court {court_number}",
                    attempts=[attempt]
                )
                
        except Exception as e:
            attempt.error_message = str(e)
            attempt.duration_seconds = (datetime.now() - start_time).total_seconds()
            
            return RecoveryResult(
                success=False,
                strategy_used=RecoveryStrategy.INDIVIDUAL_COURT,
                courts_recovered=[],
                courts_failed=[court_number],
                message=f"Exception during court {court_number} recovery",
                error_details=str(e),
                attempts=[attempt]
            )
    
    async def recover_partial_pool(self, court_numbers: List[int]) -> RecoveryResult:
        """
        Recover multiple courts in the pool
        
        Args:
            court_numbers: List of court numbers to recover
            
        Returns:
            RecoveryResult with recovery outcome
        """
        start_time = datetime.now()
        attempt = RecoveryAttempt(
            strategy=RecoveryStrategy.PARTIAL_POOL,
            timestamp=start_time,
            courts_affected=court_numbers,
            success=False
        )
        
        courts_recovered = []
        courts_failed = []
        
        try:
            logger.info(f"🔧 Recovering partial pool: courts {court_numbers}")
            
            # Close all affected courts first
            for court_number in court_numbers:
                if court_number in self.browser_pool.pages:
                    try:
                        await self.browser_pool.pages[court_number].close()
                    except Exception:
                        pass
                    del self.browser_pool.pages[court_number]
                
                if court_number in self.browser_pool.contexts:
                    try:
                        await self.browser_pool.contexts[court_number].close()
                    except Exception:
                        pass
                    del self.browser_pool.contexts[court_number]
            
            # Recreate courts in parallel with staggered starts
            tasks = []
            for i, court_number in enumerate(court_numbers):
                delay = i * 1.5  # Stagger by 1.5 seconds
                tasks.append(self.browser_pool._create_and_navigate_court_page_with_stagger(court_number, delay))
            
            # Wait for all courts with error handling
            results = await asyncio.gather(*tasks, return_exceptions=True)
            
            # Process results
            for court_number, result in zip(court_numbers, results):
                if isinstance(result, Exception):
                    logger.error(f"Failed to recover court {court_number}: {result}")
                    courts_failed.append(court_number)
                else:
                    logger.info(f"Successfully recovered court {court_number}")
                    courts_recovered.append(court_number)
            
            # Update partial readiness if needed
            if courts_recovered:
                self.browser_pool.is_partially_ready = len(courts_recovered) < len(self.browser_pool.courts)
            
            attempt.success = len(courts_recovered) > 0
            attempt.duration_seconds = (datetime.now() - start_time).total_seconds()
            
            return RecoveryResult(
                success=len(courts_recovered) > 0,
                strategy_used=RecoveryStrategy.PARTIAL_POOL,
                courts_recovered=courts_recovered,
                courts_failed=courts_failed,
                message=f"Recovered {len(courts_recovered)}/{len(court_numbers)} courts",
                attempts=[attempt]
            )
            
        except Exception as e:
            attempt.error_message = str(e)
            attempt.duration_seconds = (datetime.now() - start_time).total_seconds()
            
            return RecoveryResult(
                success=False,
                strategy_used=RecoveryStrategy.PARTIAL_POOL,
                courts_recovered=[],
                courts_failed=court_numbers,
                message="Exception during partial pool recovery",
                error_details=str(e),
                attempts=[attempt]
            )
    
    async def perform_full_pool_restart(self) -> RecoveryResult:
        """
        Perform complete browser pool restart
        
        Returns:
            RecoveryResult with recovery outcome
        """
        start_time = datetime.now()
        attempt = RecoveryAttempt(
            strategy=RecoveryStrategy.FULL_RESTART,
            timestamp=start_time,
            courts_affected=self.browser_pool.courts,
            success=False
        )
        
        try:
            logger.warning("🔄 Performing full browser pool restart")
            
            # Store original court configuration
            original_courts = self.browser_pool.courts.copy()
            
            # Stop the entire pool
            await self.browser_pool.stop()
            
            # Clear all state
            self.browser_pool.pages.clear()
            self.browser_pool.contexts.clear()
            self.browser_pool.browser = None
            self.browser_pool.playwright = None
            
            # Wait a moment for resources to be fully released
            await asyncio.sleep(2)
            
            # Restart the pool
            self.browser_pool.courts = original_courts
            await self.browser_pool.start()
            
            # Check which courts were successfully initialized
            courts_recovered = self.browser_pool.get_available_courts()
            courts_failed = [c for c in original_courts if c not in courts_recovered]
            
            attempt.success = len(courts_recovered) > 0
            attempt.duration_seconds = (datetime.now() - start_time).total_seconds()
            
            return RecoveryResult(
                success=len(courts_recovered) > 0,
                strategy_used=RecoveryStrategy.FULL_RESTART,
                courts_recovered=courts_recovered,
                courts_failed=courts_failed,
                message=f"Full restart completed: {len(courts_recovered)}/{len(original_courts)} courts ready",
                attempts=[attempt]
            )
            
        except Exception as e:
            attempt.error_message = str(e)
            attempt.duration_seconds = (datetime.now() - start_time).total_seconds()
            
            return RecoveryResult(
                success=False,
                strategy_used=RecoveryStrategy.FULL_RESTART,
                courts_recovered=[],
                courts_failed=self.browser_pool.courts,
                message="Exception during full pool restart",
                error_details=str(e),
                attempts=[attempt]
            )
    
    async def activate_emergency_fallback(self) -> RecoveryResult:
        """
        Activate emergency fallback browser as last resort
        
        Returns:
            RecoveryResult with recovery outcome
        """
        start_time = datetime.now()
        attempt = RecoveryAttempt(
            strategy=RecoveryStrategy.EMERGENCY_FALLBACK,
            timestamp=start_time,
            courts_affected=[99],  # Special court number for emergency browser
            success=False
        )
        
        try:
            logger.critical("🚨 Activating emergency fallback browser")
            
            # Create a minimal single browser instance
            from playwright.async_api import async_playwright
            
            if self.emergency_browser:
                try:
                    await self.emergency_browser.close()
                except Exception:
                    pass
            
            # Start emergency playwright instance
            emergency_playwright = await async_playwright().start()
            self.emergency_browser = await emergency_playwright.chromium.launch(
                headless=False,
                args=['--no-sandbox', '--disable-dev-shm-usage']
            )
            
            # Create a single context and page
            context = await self.emergency_browser.new_context(
                viewport={'width': 1920, 'height': 1080},
                locale='es-GT',
                timezone_id='America/Guatemala'
            )
            page = await context.new_page()
            
            # Navigate to booking site
            await page.goto("https://clublavilla.as.me", wait_until='domcontentloaded', timeout=30000)
            
            # Store emergency browser in special slot
            self.browser_pool.pages[99] = page
            self.browser_pool.contexts[99] = context
            
            attempt.success = True
            attempt.duration_seconds = (datetime.now() - start_time).total_seconds()
            
            logger.info("✅ Emergency fallback browser activated")
            
            return RecoveryResult(
                success=True,
                strategy_used=RecoveryStrategy.EMERGENCY_FALLBACK,
                courts_recovered=[99],
                courts_failed=[],
                message="Emergency browser activated - limited functionality available",
                attempts=[attempt]
            )
            
        except Exception as e:
            attempt.error_message = str(e)
            attempt.duration_seconds = (datetime.now() - start_time).total_seconds()
            
            return RecoveryResult(
                success=False,
                strategy_used=RecoveryStrategy.EMERGENCY_FALLBACK,
                courts_recovered=[],
                courts_failed=[99],
                message="Failed to activate emergency fallback",
                error_details=str(e),
                attempts=[attempt]
            )
    
    async def is_recovery_needed(self) -> Tuple[bool, List[int]]:
        """
        Check if recovery is needed and identify failed courts
        
        Returns:
            Tuple of (needs_recovery, list_of_failed_courts)
        """
        failed_courts = []
        
        # Check if browser pool is initialized
        if not self.browser_pool.browser:
            return True, self.browser_pool.courts
        
        # Check each court's health
        for court_number in self.browser_pool.courts:
            try:
                page = self.browser_pool.pages.get(court_number)
                if not page:
                    failed_courts.append(court_number)
                else:
                    # Test page connection
                    _ = page.url
            except Exception:
                failed_courts.append(court_number)
        
        return len(failed_courts) > 0, failed_courts
    
    def get_recovery_stats(self) -> Dict[str, Any]:
        """
        Get recovery statistics
        
        Returns:
            Dict with recovery history and statistics
        """
        total_attempts = len(self.recovery_history)
        successful_attempts = sum(1 for a in self.recovery_history if a.success)
        
        strategy_counts = {}
        for attempt in self.recovery_history:
            strategy = attempt.strategy.value
            if strategy not in strategy_counts:
                strategy_counts[strategy] = {'total': 0, 'successful': 0}
            strategy_counts[strategy]['total'] += 1
            if attempt.success:
                strategy_counts[strategy]['successful'] += 1
        
        return {
            'total_recovery_attempts': total_attempts,
            'successful_recoveries': successful_attempts,
            'success_rate': successful_attempts / total_attempts if total_attempts > 0 else 0,
            'strategy_stats': strategy_counts,
            'last_recovery': self.recovery_history[-1] if self.recovery_history else None,
            'emergency_browser_active': self.emergency_browser is not None
        }