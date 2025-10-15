"""
Unified Tennis Executor - Intelligent and Asynchronous Execution
"""

import asyncio
import concurrent.futures
import logging
from datetime import datetime
from typing import Dict, Any, Optional, List
from dataclasses import dataclass

# Import our new modular config
from .tennis_config import TennisConfig, create_tennis_config_from_user_info as create_config_from_user_info

# Import PooledTennisExecutor later to avoid circular imports

@dataclass
class ExecutionResult:
    success: bool
    error_message: Optional[str] = None
    execution_time_seconds: float = 0.0
    court_attempted: Optional[int] = None
    court_reserved: Optional[int] = None
    time_reserved: Optional[str] = None
    available_times: Optional[Dict[int, List[str]]] = None
    message: Optional[str] = None
    available_times_with_dates: Optional[Dict[int, Dict[str, List[str]]]] = None
    
    def __post_init__(self):
        if not self.success and not self.error_message:
            self.error_message = "Unknown execution failure"

class TennisExecutor:
    """Intelligent executor that routes to the best available execution method."""

    def __init__(self, browser_pool=None, max_workers: int = 2, timeout_seconds: int = 300):
        self.browser_pool = browser_pool
        self.pooled_executor = None
        if browser_pool:
            # Import here to avoid circular imports
            from utils.async_booking_executor import AsyncBookingExecutor
            self.pooled_executor = AsyncBookingExecutor(browser_pool, use_natural_flow=True)
        self.logger = logging.getLogger(self.__class__.__name__)
        self.max_workers = max_workers
        self.timeout_seconds = timeout_seconds
        self.executor = concurrent.futures.ThreadPoolExecutor(
            max_workers=self.max_workers,
            thread_name_prefix="TennisBot"
        )

    def set_browser_pool(self, browser_pool):
        self.browser_pool = browser_pool
        if browser_pool:
            from utils.async_booking_executor import AsyncBookingExecutor
            self.pooled_executor = AsyncBookingExecutor(browser_pool, use_natural_flow=True)
        else:
            self.pooled_executor = None

    def is_pool_available(self) -> bool:
        if self.browser_pool and hasattr(self.browser_pool, 'is_ready'):
            return self.browser_pool.is_ready()
        return False

    async def execute(self, tennis_config: TennisConfig, target_date: datetime, check_availability_48h: bool = False, get_dates: bool = False) -> ExecutionResult:
        """Execute tennis operation using the best available method."""
        if self.is_pool_available():
            self.logger.info("Using ASYNC BOOKING EXECUTOR with natural flow for optimized booking")
            # Use original user_info if available to preserve all fields
            if hasattr(tennis_config, '_original_user_info'):
                user_info = tennis_config._original_user_info
            else:
                user_info = {
                    'email': tennis_config.email,
                    'first_name': tennis_config.first_name,
                    'last_name': tennis_config.last_name,
                    'phone': tennis_config.phone,
                }
            
            # Get the first preferred court or default to 1
            target_court = tennis_config.court_preference[0] if tennis_config.court_preference else 1
            target_time = tennis_config.preferred_times[0] if tennis_config.preferred_times else "08:00"
            
            try:
                return await self.pooled_executor.execute_booking(
                    court_number=target_court,
                    time_slot=target_time,
                    user_info=user_info,
                    target_date=target_date
                )
            except Exception as e:
                self.logger.warning(f"Async booking executor failed, falling back to direct: {e}")
        
        self.logger.info("Using DIRECT browser execution (pool not available or failed)")
        return await self._execute_direct(tennis_config, target_date, check_availability_48h, get_dates)

    async def _execute_direct(self, tennis_config: TennisConfig, target_date: datetime, check_availability_48h: bool, get_dates: bool) -> ExecutionResult:
        """Execute directly using a thread pool."""
        loop = asyncio.get_event_loop()
        try:
            result = await asyncio.wait_for(
                loop.run_in_executor(
                    self.executor,
                    self._run_sync_bot,
                    tennis_config,
                    target_date,
                    check_availability_48h,
                    get_dates
                ),
                timeout=self.timeout_seconds
            )
            return result
        except asyncio.TimeoutError:
            return ExecutionResult(success=False, error_message="Execution timed out")
        except Exception as e:
            return ExecutionResult(success=False, error_message=str(e))

    def _run_sync_bot(self, tennis_config: TennisConfig, target_date: datetime, check_availability_48h: bool, get_dates: bool) -> ExecutionResult:
        """
        Synchronous bot execution - Currently disabled pending TennisBot refactoring.
        
        TODO: Replace with async components from AsyncAvailabilityChecker and AsyncBrowserPool
        """
        self.logger.warning("Direct bot execution not available - TennisBot requires refactoring")
        return ExecutionResult(
            success=False, 
            error_message="Direct bot execution temporarily disabled. Use pooled execution instead."
        )

# Re-export the config creation function for backward compatibility
create_tennis_config_from_user_info = create_config_from_user_info