"""Browser pool recovery orchestration service."""

from __future__ import annotations

import asyncio
import logging
import traceback
from datetime import datetime
from typing import Any, Dict, List, Optional, Tuple

from tracking import t

from automation.browser.recovery.strategies.base import RecoveryContext, RecoveryStrategyExecutor
from automation.browser.recovery.strategies.emergency_fallback import EmergencyFallbackRecovery
from automation.browser.recovery.strategies.full_restart import FullRestartRecovery
from automation.browser.recovery.strategies.individual_court import IndividualCourtRecovery
from automation.browser.recovery.strategies.partial_pool import PartialPoolRecovery
from automation.browser.recovery.types import RecoveryAttempt, RecoveryResult, RecoveryStrategy


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
        t('automation.browser.browser_pool_recovery.BrowserPoolRecoveryService.__init__')
        self.browser_pool = browser_pool
        self.logger = logging.getLogger(__name__)
        self.recovery_history: List[RecoveryAttempt] = []
        self.emergency_browser = None
        self.recovery_lock = asyncio.Lock()
        self.max_recovery_attempts = 3
        self.recovery_timeout = 60  # seconds per attempt

        self._strategy_registry: Dict[RecoveryStrategy, RecoveryStrategyExecutor] = {
            RecoveryStrategy.INDIVIDUAL_COURT: IndividualCourtRecovery(),
            RecoveryStrategy.PARTIAL_POOL: PartialPoolRecovery(),
            RecoveryStrategy.FULL_RESTART: FullRestartRecovery(),
            RecoveryStrategy.EMERGENCY_FALLBACK: EmergencyFallbackRecovery(),
        }

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
        t('automation.browser.browser_pool_recovery.BrowserPoolRecoveryService.recover_browser_pool')
        async with self.recovery_lock:
            start_time = datetime.now()
            all_attempts = []
            
            self.logger.warning(
                "🔧 Starting browser pool recovery. Failed courts: %s, Error: %s",
                failed_courts,
                error_context,
            )
            
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
                executor = self._strategy_registry[strategy]
                self.logger.info("🔄 Attempting recovery strategy: %s", strategy.value)

                try:
                    context_obj = RecoveryContext(self, failed_courts, error_context)
                    result = await executor.execute(context_obj)
                    all_attempts.extend(result.attempts)
                    self.recovery_history.extend(result.attempts)

                    if result.success:
                        total_duration = (datetime.now() - start_time).total_seconds()
                        result.total_duration_seconds = total_duration
                        result.attempts = all_attempts
                        self.logger.info(
                            "✅ Recovery successful using %s in %.1fs",
                            strategy.value,
                            total_duration,
                        )
                        return result

                    self.logger.warning(
                        "❌ Recovery strategy %s failed: %s",
                        strategy.value,
                        result.message,
                    )

                except Exception as exc:
                    self.logger.error(
                        "💥 Exception during %s recovery: %s",
                        strategy.value,
                        exc,
                    )
                    self.logger.error(traceback.format_exc())

                    attempt = RecoveryAttempt(
                        strategy=strategy,
                        timestamp=datetime.now(),
                        courts_affected=failed_courts or self.browser_pool.courts,
                        success=False,
                        error_message=str(exc),
                        duration_seconds=(datetime.now() - start_time).total_seconds(),
                    )
                    all_attempts.append(attempt)
                    self.recovery_history.append(attempt)
            
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
                total_duration_seconds=total_duration,
            )
    async def is_recovery_needed(self) -> Tuple[bool, List[int]]:
        """
        Check if recovery is needed and identify failed courts
        
        Returns:
            Tuple of (needs_recovery, list_of_failed_courts)
        """
        t('automation.browser.browser_pool_recovery.BrowserPoolRecoveryService.is_recovery_needed')
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
        t('automation.browser.browser_pool_recovery.BrowserPoolRecoveryService.get_recovery_stats')
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
