"""Unified tennis executor utilities and configuration."""

from __future__ import annotations
from utils.tracking import t

import asyncio
import concurrent.futures
import logging
from dataclasses import dataclass
from datetime import datetime
from typing import Any, Dict, List, Optional, Union

from .booking import AsyncBookingExecutor
from .core import ExecutionResult


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
        self.pooled_executor = AsyncBookingExecutor(self.browser_pool, use_natural_flow=True) if self.browser_pool else None

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
        if self.is_pool_available() and self.pooled_executor:
            self.logger.info("Using ASYNC BOOKING EXECUTOR with natural flow for optimized booking")
            user_info = getattr(tennis_config, "_original_user_info", None) or {
                "email": tennis_config.email,
                "first_name": tennis_config.first_name,
                "last_name": tennis_config.last_name,
                "phone": tennis_config.phone,
            }
            target_court = tennis_config.court_preference[0] if tennis_config.court_preference else 1
            target_time = tennis_config.preferred_times[0] if tennis_config.preferred_times else "08:00"

            try:
                return await self.pooled_executor.execute_booking(
                    court_number=target_court,
                    time_slot=target_time,
                    user_info=user_info,
                    target_date=target_date,
                )
            except Exception as exc:
                self.logger.warning("Async booking executor failed, falling back to direct: %s", exc)

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
