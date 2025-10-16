"""
Async Booking Executor - Clean Version
Uses the proven working method from court_booking_final.py
"""

import asyncio
import logging
import time
from datetime import datetime
from typing import Dict, Any, Optional, Tuple
from dataclasses import dataclass, field

@dataclass
class ExecutionResult:
    """Result of a booking execution attempt"""
    success: bool
    message: Optional[str] = None
    error_message: Optional[str] = None
    court_reserved: Optional[int] = None
    time_reserved: Optional[str] = None
    court_attempted: Optional[int] = None
    confirmation_url: Optional[str] = None
    confirmation_id: Optional[str] = None
    user_name: Optional[str] = None

class AsyncBookingExecutor:
    """
    Async booking executor that uses the proven working method
    """
    
    # Timeout configuration optimized for booking flow
    TIMEOUTS = {
        'total_execution': 60.0,     # Total time for entire booking
        'navigation': 15.0,          # Time for page navigation  
        'form_filling': 20.0,        # Time to fill form
        'confirmation': 10.0,        # Time to wait for confirmation
        'element_wait': 5.0,         # Time to wait for elements
        'health_check': 2.0,         # Quick health checks
        'form_detection': 3.0        # Form detection timeout
    }
    
    def __init__(self, browser_pool=None, use_natural_flow=False):
        """
        Initialize the AsyncBookingExecutor
        
        Args:
            browser_pool: AsyncBrowserPool instance
            use_natural_flow: Whether to use natural flow (ignored - always uses working method)
        """
        self.browser_pool = browser_pool
        self.use_natural_flow = use_natural_flow  # Kept for compatibility but ignored
        self.logger = logging.getLogger(self.__class__.__name__)
        
    async def execute_parallel_booking(
        self, 
        court_numbers: list,
        time_slot: str,
        user_info: Dict[str, str],
        target_date: datetime,
        max_concurrent: int = 3
    ) -> Dict[str, Any]:
        """
        Execute booking attempts on multiple courts in parallel
        """
        self.logger.info(f"Starting parallel booking for courts {court_numbers} at {time_slot}")
        
        # Always use the working method regardless of use_natural_flow
        self.logger.info("Using PROVEN WORKING METHOD from court_booking_final.py")
        
        # Create tasks for each court
        tasks = []
        for court_number in court_numbers[:max_concurrent]:
            task = asyncio.create_task(
                self.execute_booking(court_number, time_slot, user_info, target_date),
                name=f"court_{court_number}_booking"
            )
            tasks.append((court_number, task))
        
        # Wait for first successful booking or all to complete
        results = {}
        successful_court = None
        
        try:
            # Use asyncio.as_completed to process results as they come in
            for court_number, task in tasks:
                try:
                    result = await asyncio.wait_for(task, timeout=self.TIMEOUTS['total_execution'])
                    results[court_number] = result
                    
                    if result.success and not successful_court:
                        successful_court = court_number
                        self.logger.info(f"✅ Successfully booked Court {court_number}!")
                        
                        # Cancel remaining tasks
                        for other_court, other_task in tasks:
                            if other_court != court_number and not other_task.done():
                                other_task.cancel()
                                self.logger.info(f"Cancelling booking attempt for Court {other_court}")
                        
                        break
                        
                except asyncio.TimeoutError:
                    self.logger.error(f"Court {court_number} booking timed out")
                    results[court_number] = ExecutionResult(
                        success=False,
                        error_message="Booking timed out",
                        court_attempted=court_number
                    )
                except Exception as e:
                    self.logger.error(f"Court {court_number} booking failed: {e}")
                    results[court_number] = ExecutionResult(
                        success=False,
                        error_message=str(e),
                        court_attempted=court_number
                    )
            
            # Wait for any remaining tasks to complete or be cancelled
            remaining_tasks = [task for _, task in tasks if not task.done()]
            if remaining_tasks:
                await asyncio.gather(*remaining_tasks, return_exceptions=True)
                
        except Exception as e:
            self.logger.error(f"Parallel booking error: {e}")
            
        return {
            'success': successful_court is not None,
            'successful_court': successful_court,
            'results': results,
            'courts_attempted': court_numbers
        }
    
    async def execute_booking(
        self,
        court_number: int,
        time_slot: str, 
        user_info: Dict[str, str],
        target_date: datetime
    ) -> ExecutionResult:
        """
        Execute a single booking attempt using the working method
        """
        execution_start = time.time()
        
        try:
            # Quick browser pool health check
            if not self.browser_pool:
                return ExecutionResult(
                    success=False,
                    error_message="Browser pool not initialized",
                    court_attempted=court_number
                )
            
            # Use timeout for entire execution
            result = await asyncio.wait_for(
                self._execute_booking_internal(court_number, time_slot, user_info, target_date),
                timeout=self.TIMEOUTS['total_execution']
            )
            
            execution_time = time.time() - execution_start
            self.logger.info(f"Booking execution completed in {execution_time:.1f}s")
            
            return result
            
        except asyncio.TimeoutError:
            execution_time = time.time() - execution_start
            error_msg = f"Booking timed out after {execution_time:.1f}s (limit: {self.TIMEOUTS['total_execution']}s)"
            self.logger.error(error_msg)
            return ExecutionResult(
                success=False,
                error_message=error_msg,
                court_attempted=court_number
            )
        except asyncio.CancelledError:
            execution_time = time.time() - execution_start
            self.logger.warning(f"Booking task was cancelled externally after {execution_time:.1f}s")
            raise  # Re-raise to maintain cancellation signal
        except Exception as e:
            execution_time = time.time() - execution_start
            self.logger.error(f"Booking failed after {execution_time:.1f}s: {e}", exc_info=True)
            return ExecutionResult(
                success=False,
                error_message=str(e),
                court_attempted=court_number
            )
    
    async def _execute_booking_internal(
        self, 
        court_number: int,
        time_slot: str,
        user_info: Dict[str, str],
        target_date: datetime
    ) -> ExecutionResult:
        """
        Internal booking execution - always uses the working method
        """
        try:
            # Always use the PROVEN WORKING METHOD from court_booking_final.py
            self.logger.info(f"Using WORKING solution from court_booking_final.py for Court {court_number}")
            
            # Import and use the working executor
            from .working_booking_executor import WorkingBookingExecutor
            working_executor = WorkingBookingExecutor(self.browser_pool)
            
            # Delegate to the working executor
            working_result = await working_executor.execute_booking(
                court_number=court_number,
                target_date=target_date,
                time_slot=time_slot,
                user_info=user_info
            )
            
            # Convert WorkingExecutionResult to ExecutionResult
            if working_result.success:
                return ExecutionResult(
                    success=True,
                    message=f"Successfully booked {time_slot} on Court {court_number}",
                    confirmation_url=working_result.confirmation_url,
                    confirmation_id=working_result.confirmation_id,
                    user_name=working_result.user_name,
                    court_reserved=court_number,
                    time_reserved=time_slot
                )
            else:
                return ExecutionResult(
                    success=False,
                    error_message=working_result.error_message,
                    court_attempted=court_number
                )
                
        except asyncio.CancelledError:
            self.logger.warning(f"Internal booking execution cancelled for court {court_number}")
            raise  # Re-raise to propagate cancellation
        except Exception as e:
            self.logger.error(f"Internal booking error: {e}", exc_info=True)
            return ExecutionResult(
                success=False,
                error_message=f"Internal error: {str(e)}",
                court_attempted=court_number
            )