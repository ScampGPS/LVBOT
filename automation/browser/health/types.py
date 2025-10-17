"""Shared types for browser health checks."""

from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime
from enum import Enum
from typing import Any, Dict, Optional

from tracking import t


class HealthStatus(Enum):
    """Health status levels for browser components."""

    HEALTHY = "healthy"
    DEGRADED = "degraded"
    CRITICAL = "critical"
    FAILED = "failed"


@dataclass
class HealthCheckResult:
    """Result of a health check operation."""

    status: HealthStatus
    message: str
    timestamp: datetime
    details: Optional[Dict[str, Any]] = None

    def is_healthy(self) -> bool:
        t('automation.browser.health.types.HealthCheckResult.is_healthy')
        return self.status == HealthStatus.HEALTHY


@dataclass
class CourtHealthStatus:
    """Health status for an individual court browser."""

    court_number: int
    status: HealthStatus
    last_check: datetime
    page_url: Optional[str] = None
    error_message: Optional[str] = None
    response_time_ms: Optional[int] = None
    checks_passed: Optional[Dict[str, bool]] = None
