"""Consolidated booking executors and related helpers."""

from __future__ import annotations
from tracking import t

import asyncio
import logging
from datetime import datetime
from typing import Any, Dict, List, Optional

from playwright.async_api import Page

from automation.shared.booking_contracts import BookingRequest

from .core import AsyncExecutorConfig, DEFAULT_EXECUTOR_CONFIG, ExecutionResult
from .flows.fast_flow import execute_fast_flow
from .flows.natural_flow import execute_natural_flow


NATURAL_INITIAL_DELAY_RANGE = (28.0, 32.0)


class BookingFlowExecutor:
    """Unified booking executor supporting natural and fast flows."""

    def __init__(self, browser_pool: Optional[Any] = None, mode: str = "natural") -> None:
        t('automation.executors.booking.BookingFlowExecutor.__init__')
        if mode not in {"natural", "fast"}:
            raise ValueError(f"Unknown booking flow mode: {mode}")

        self.browser_pool = browser_pool
        self.mode = mode
        self.logger = logging.getLogger("BookingFlowExecutor")
        self.initial_delay_range = NATURAL_INITIAL_DELAY_RANGE

    async def execute_booking(
        self,
        court_number: int,
        target_date: datetime,
        time_slot: str,
        user_info: Dict[str, str],
    ) -> ExecutionResult:
        t('automation.executors.booking.BookingFlowExecutor.execute_booking')
        if not self.browser_pool:
            return ExecutionResult(success=False, error_message="Browser pool not initialized")

        try:
            page = await self.browser_pool.get_page(court_number)
            if not page:
                return ExecutionResult(
                    success=False,
                    error_message=f"Could not get page for court {court_number}",
                    court_number=court_number,
                )
            return await self._execute_booking_internal(page, court_number, target_date, time_slot, user_info)
        except Exception as exc:  # pragma: no cover - defensive guard
            self.logger.error("Booking execution error: %s", exc)
            return ExecutionResult(success=False, error_message=str(exc), court_number=court_number)

    async def execute_request(
        self,
        booking_request: BookingRequest,
        *,
        court_number: Optional[int] = None,
        time_slot: Optional[str] = None,
    ) -> ExecutionResult:
        """Execute a shared `BookingRequest` using this flow executor."""

        t('automation.executors.booking.BookingFlowExecutor.execute_request')

        target_court = court_number or booking_request.court_preference.primary
        target_slot = time_slot or booking_request.target_time
        target_datetime = datetime.combine(booking_request.target_date, datetime.min.time())

        user_info = booking_request.user.as_executor_payload(user_id_as_str=True)

        return await self.execute_booking(
            court_number=target_court,
            target_date=target_datetime,
            time_slot=target_slot,
            user_info=user_info,
        )

    async def _execute_booking_internal(
        self,
        page: Page,
        court_number: int,
        target_date: datetime,
        time_slot: str,
        user_info: Dict[str, str],
    ) -> ExecutionResult:
        t('automation.executors.booking.BookingFlowExecutor._execute_booking_internal')
        self.logger.info("Starting booking (%s mode): Court %s at %s on %s", self.mode, court_number, time_slot, target_date)

        if self.mode == "fast":
            return await self._execute_fast(page, court_number, target_date, time_slot, user_info)

        return await self._execute_natural(page, court_number, target_date, time_slot, user_info)

    async def _execute_natural(
        self,
        page: Page,
        court_number: int,
        target_date: datetime,
        time_slot: str,
        user_info: Dict[str, str],
    ) -> ExecutionResult:
        delay_min, delay_max = self.initial_delay_range
        return await execute_natural_flow(
            page,
            court_number,
            target_date,
            time_slot,
            user_info,
            logger=self.logger,
            initial_delay_range=(delay_min, delay_max),
        )

    async def _execute_fast(
        self,
        page: Page,
        court_number: int,
        target_date: datetime,
        time_slot: str,
        user_info: Dict[str, str],
    ) -> ExecutionResult:
        return await execute_fast_flow(
            page,
            court_number,
            target_date,
            time_slot,
            user_info,
            logger=self.logger,
        )


# ---------------------------------------------------------------------------
# Async booking executor (multi-court orchestration)
# ---------------------------------------------------------------------------

class AsyncBookingExecutor:
    """Async booking executor that orchestrates bookings across courts."""

    TIMEOUTS = {
        "total_execution": 60.0,
        "navigation": 15.0,
        "form_filling": 20.0,
        "confirmation": 10.0,
        "element_wait": 5.0,
        "health_check": 2.0,
        "form_detection": 3.0,
    }

    def __init__(self, browser_pool: Optional[Any] = None, use_natural_flow: bool = False, experienced_mode: bool = True) -> None:
        t('automation.executors.booking.AsyncBookingExecutor.__init__')
        self.browser_pool = browser_pool
        self.use_natural_flow = use_natural_flow
        self.experienced_mode = experienced_mode
        self.logger = logging.getLogger(self.__class__.__name__)

        mode = "natural" if use_natural_flow else ("fast" if experienced_mode else "natural")
        self._flow_executor = BookingFlowExecutor(browser_pool, mode=mode)

    async def execute_parallel_booking(
        self,
        court_numbers: List[int],
        time_slot: str,
        user_info: Dict[str, str],
        target_date: datetime,
        max_concurrent: int = 3,
    ) -> Dict[str, Any]:
        t('automation.executors.booking.AsyncBookingExecutor.execute_parallel_booking')
        self.logger.info("Starting parallel booking for courts %s at %s", court_numbers, time_slot)

        tasks: List[Tuple[int, asyncio.Task]] = []
        for court_number in court_numbers[:max_concurrent]:
            task = asyncio.create_task(
                self.execute_booking(court_number, time_slot, user_info, target_date),
                name=f"court_{court_number}_booking",
            )
            tasks.append((court_number, task))

        results: Dict[int, ExecutionResult] = {}
        successful_court: Optional[int] = None

        try:
            for court_number, task in tasks:
                try:
                    result = await asyncio.wait_for(task, timeout=self.TIMEOUTS["total_execution"])
                    results[court_number] = result

                    if result.success and not successful_court:
                        successful_court = court_number
                        self.logger.info("✅ Successfully booked Court %s!", court_number)
                        for other_court, other_task in tasks:
                            if other_court != court_number and not other_task.done():
                                other_task.cancel()
                        break
                except asyncio.TimeoutError:
                    self.logger.error("Court %s booking timed out", court_number)
                    results[court_number] = ExecutionResult(
                        success=False,
                        error_message="Booking timed out",
                        court_attempted=court_number,
                        court_number=court_number,
                    )
                except Exception as exc:  # pragma: no cover - defensive guard
                    self.logger.error("Court %s booking failed: %s", court_number, exc)
                    results[court_number] = ExecutionResult(
                        success=False,
                        error_message=str(exc),
                        court_attempted=court_number,
                        court_number=court_number,
                    )

            remaining_tasks = [task for _, task in tasks if not task.done()]
            if remaining_tasks:
                await asyncio.gather(*remaining_tasks, return_exceptions=True)
        finally:
            pass

        return {
            "success": successful_court is not None,
            "successful_court": successful_court,
            "results": results,
            "courts_attempted": court_numbers,
        }

    async def execute_booking(
        self,
        court_number: int,
        time_slot: str,
        user_info: Dict[str, str],
        target_date: datetime,
    ) -> ExecutionResult:
        t('automation.executors.booking.AsyncBookingExecutor.execute_booking')
        if not self.browser_pool:
            return ExecutionResult(success=False, error_message="Browser pool not initialized", court_number=court_number)

        try:
            return await self._flow_executor.execute_booking(court_number, target_date, time_slot, user_info)
        except Exception as exc:  # pragma: no cover - defensive guard
            self.logger.error("Booking failed for court %s: %s", court_number, exc)
            return ExecutionResult(success=False, error_message=str(exc), court_number=court_number)


# ---------------------------------------------------------------------------
# Unified async booking executor facade
# ---------------------------------------------------------------------------

class UnifiedAsyncBookingExecutor:
    """Route booking requests to the appropriate executor based on config."""

    def __init__(self, browser_pool: Optional[Any] = None, config: AsyncExecutorConfig = DEFAULT_EXECUTOR_CONFIG) -> None:
        t('automation.executors.booking.UnifiedAsyncBookingExecutor.__init__')
        self.config = config
        self.browser_pool = browser_pool
        self._executor = self._build_executor()

    def _build_executor(self) -> Any:
        t('automation.executors.booking.UnifiedAsyncBookingExecutor._build_executor')
        use_natural = self.config.natural_flow
        use_fast = self.config.use_experienced_mode or self.config.use_smart_navigation

        return AsyncBookingExecutor(
            browser_pool=self.browser_pool,
            use_natural_flow=use_natural,
            experienced_mode=use_fast,
        )

    def __getattr__(self, item: str) -> Any:
        t('automation.executors.booking.UnifiedAsyncBookingExecutor.__getattr__')
        return getattr(self._executor, item)

    def with_config(self, config: AsyncExecutorConfig) -> "UnifiedAsyncBookingExecutor":
        t('automation.executors.booking.UnifiedAsyncBookingExecutor.with_config')
        return UnifiedAsyncBookingExecutor(browser_pool=self.browser_pool, config=config)


__all__ = [
    "AsyncBookingExecutor",
    "BookingFlowExecutor",
    "UnifiedAsyncBookingExecutor",
]
