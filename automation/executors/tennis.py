"""Unified tennis executor utilities and configuration."""

from __future__ import annotations
from tracking import t

import asyncio
import concurrent.futures
import logging
from dataclasses import dataclass
from datetime import datetime
from typing import Any, Dict, List, Optional, Union

from .booking import BookingFlowExecutor
from .core import ExecutionResult
from .request_factory import build_tennis_booking_request


@dataclass
class TennisConfig:
    """Configuration for tennis booking operations."""

    email: str
    first_name: str
    last_name: str
    phone: str
    user_id: Union[str, int]
    preferred_time: str
    target_time: str
    fallback_times: List[str]
    court_preference: List[int]
    preferred_times: Optional[List[str]] = None

    def __post_init__(self) -> None:
        t('automation.executors.tennis.TennisConfig.__post_init__')
        if self.preferred_times is None:
            self.preferred_times = [self.preferred_time]


def create_tennis_config_from_user_info(user_info: Dict[str, Any]) -> TennisConfig:
    t('automation.executors.tennis.create_tennis_config_from_user_info')
    preferred_time = user_info.get("preferred_time", "09:00")
    preferred_times = user_info.get("preferred_times", [preferred_time])
    if "preferred_times" in user_info and "preferred_time" not in user_info:
        preferred_time = preferred_times[0] if preferred_times else "09:00"

    return TennisConfig(
        email=user_info.get("email", ""),
        first_name=user_info.get("first_name", ""),
        last_name=user_info.get("last_name", ""),
        phone=user_info.get("phone", ""),
        user_id=user_info.get("user_id", 0),
        preferred_time=preferred_time,
        target_time=user_info.get("target_time", preferred_time),
        fallback_times=user_info.get("fallback_times", []),
        court_preference=user_info.get("court_preference", [1, 2, 3]),
        preferred_times=preferred_times,
    )


class TennisExecutor:
    """Intelligent executor that routes to the best available execution method."""

    def __init__(self, browser_pool: Optional[Any] = None, max_workers: int = 2, timeout_seconds: int = 300) -> None:
        t('automation.executors.tennis.TennisExecutor.__init__')
        self.browser_pool = browser_pool
        self.logger = logging.getLogger(self.__class__.__name__)
        self.max_workers = max_workers
        self.timeout_seconds = timeout_seconds
        self.executor = concurrent.futures.ThreadPoolExecutor(
            max_workers=self.max_workers,
            thread_name_prefix="TennisBot",
        )
        self._build_pooled_executor()

    def _build_pooled_executor(self) -> None:
        t('automation.executors.tennis.TennisExecutor._build_pooled_executor')
        self.flow_executor = BookingFlowExecutor(self.browser_pool, mode="natural") if self.browser_pool else None

    def set_browser_pool(self, browser_pool: Optional[Any]) -> None:
        t('automation.executors.tennis.TennisExecutor.set_browser_pool')
        self.browser_pool = browser_pool
        self._build_pooled_executor()

    def is_pool_available(self) -> bool:
        t('automation.executors.tennis.TennisExecutor.is_pool_available')
        if self.browser_pool and hasattr(self.browser_pool, "is_ready"):
            return self.browser_pool.is_ready()
        return False

    async def execute(
        self,
        tennis_config: TennisConfig,
        target_date: datetime,
        check_availability_48h: bool = False,
        get_dates: bool = False,
    ) -> ExecutionResult:
        t('automation.executors.tennis.TennisExecutor.execute')
        request_date = target_date.date() if isinstance(target_date, datetime) else target_date
        booking_request = build_tennis_booking_request(
            tennis_config=tennis_config,
            target_date=request_date,
            metadata={
                "check_availability_48h": check_availability_48h,
                "get_dates": get_dates,
            },
        )

        preferred_times = list(tennis_config.preferred_times or [tennis_config.preferred_time])
        fallback_times = [time for time in tennis_config.fallback_times if time not in preferred_times]
        time_candidates = preferred_times + fallback_times
        court_candidates = booking_request.court_preference.as_list()

        if self.is_pool_available() and getattr(self, "flow_executor", None):
            self.logger.info("Using BookingFlowExecutor natural flow for tennis booking")
            last_failure: Optional[ExecutionResult] = None

            for time_slot in time_candidates or [booking_request.target_time]:
                for court in court_candidates:
                    self.logger.info("Attempting booking for Court %s at %s", court, time_slot)
                    try:
                        execution = await self.flow_executor.execute_request(
                            booking_request,
                            court_number=court,
                            time_slot=time_slot,
                        )
                        if execution.success:
                            return execution
                        last_failure = execution
                    except Exception as exc:  # pragma: no cover - defensive guard
                        self.logger.warning("Booking attempt failed for Court %s at %s: %s", court, time_slot, exc)

            if last_failure:
                return last_failure

        self.logger.info("Using direct execution (pool not available or failed)")
        return await self._execute_direct(tennis_config, target_date, check_availability_48h, get_dates)

    async def _execute_direct(
        self,
        tennis_config: TennisConfig,
        target_date: datetime,
        check_availability_48h: bool,
        get_dates: bool,
    ) -> ExecutionResult:
        t('automation.executors.tennis.TennisExecutor._execute_direct')
        loop = asyncio.get_event_loop()
        try:
            result = await asyncio.wait_for(
                loop.run_in_executor(
                    self.executor,
                    self._run_sync_bot,
                    tennis_config,
                    target_date,
                    check_availability_48h,
                    get_dates,
                ),
                timeout=self.timeout_seconds,
            )
            return result
        except asyncio.TimeoutError:
            return ExecutionResult(success=False, error_message="Execution timed out")
        except Exception as exc:
            return ExecutionResult(success=False, error_message=str(exc))

    def _run_sync_bot(
        self,
        tennis_config: TennisConfig,
        target_date: datetime,
        check_availability_48h: bool,
        get_dates: bool,
    ) -> ExecutionResult:
        t('automation.executors.tennis.TennisExecutor._run_sync_bot')
        self.logger.warning("Direct bot execution not available - TennisBot requires refactoring")
        return ExecutionResult(
            success=False,
            error_message="Direct bot execution temporarily disabled. Use pooled execution instead.",
        )


__all__ = [
    "TennisConfig",
    "TennisExecutor",
    "create_tennis_config_from_user_info",
]
