"""Shared data structures and config for booking executors."""

from __future__ import annotations

from dataclasses import dataclass
from typing import Any, Dict, List, Optional


@dataclass
class ExecutionResult:
    """Unified booking execution result representation."""

    success: bool
    message: Optional[str] = None
    error_message: Optional[str] = None
    court_number: Optional[int] = None
    court_reserved: Optional[int] = None
    time_reserved: Optional[str] = None
    court_attempted: Optional[int] = None
    confirmation_url: Optional[str] = None
    confirmation_id: Optional[str] = None
    user_name: Optional[str] = None
    details: Optional[Dict[str, Any]] = None
    execution_time_seconds: Optional[float] = None
    available_times: Optional[Dict[int, List[str]]] = None
    available_times_with_dates: Optional[Dict[int, Dict[str, List[str]]]] = None


@dataclass(frozen=True)
class AsyncExecutorConfig:
    """Feature toggles for the unified async executor."""

    use_experienced_mode: bool = False
    use_smart_navigation: bool = False
    natural_flow: bool = False


DEFAULT_EXECUTOR_CONFIG = AsyncExecutorConfig()


__all__ = [
    "ExecutionResult",
    "AsyncExecutorConfig",
    "DEFAULT_EXECUTOR_CONFIG",
]
