"""Shared recovery strategy types."""

from __future__ import annotations

from dataclasses import dataclass, field
from datetime import datetime
from enum import Enum
from typing import List, Optional


class RecoveryStrategy(Enum):
    """Enumeration of available recovery strategies."""

    INDIVIDUAL_COURT = "individual_court"
    PARTIAL_POOL = "partial_pool"
    FULL_RESTART = "full_restart"
    EMERGENCY_FALLBACK = "emergency_fallback"


@dataclass
class RecoveryAttempt:
    """Track details about a single recovery attempt."""

    strategy: RecoveryStrategy
    timestamp: datetime
    courts_affected: List[int]
    success: bool
    error_message: Optional[str] = None
    duration_seconds: float = 0.0


@dataclass
class RecoveryResult:
    """Structured result returned by recovery strategies."""

    success: bool
    strategy_used: RecoveryStrategy
    courts_recovered: List[int]
    courts_failed: List[int]
    message: str
    error_details: Optional[str] = None
    attempts: List[RecoveryAttempt] = field(default_factory=list)
    total_duration_seconds: float = 0.0
