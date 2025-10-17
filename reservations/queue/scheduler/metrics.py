"""Statistics helpers for the reservation scheduler."""

from __future__ import annotations

from dataclasses import dataclass
from typing import Optional


@dataclass
class SchedulerStats:
    """Mutable counters tracking queue execution performance."""

    total_attempts: int = 0
    successful_bookings: int = 0
    failed_bookings: int = 0
    total_execution_time: float = 0.0
    health_checks_performed: int = 0
    recovery_attempts: int = 0

    def record_success(self, execution_time: Optional[float] = None) -> None:
        self.successful_bookings += 1
        self.total_attempts += 1
        self._record_execution_time(execution_time)

    def record_failure(self, execution_time: Optional[float] = None) -> None:
        self.failed_bookings += 1
        self.total_attempts += 1
        self._record_execution_time(execution_time)

    def record_health_check(self) -> None:
        self.health_checks_performed += 1

    def record_recovery_attempt(self) -> None:
        self.recovery_attempts += 1

    def _record_execution_time(self, execution_time: Optional[float]) -> None:
        if execution_time is None:
            return
        try:
            value = float(execution_time)
        except (TypeError, ValueError):
            return
        if value < 0:
            return
        self.total_execution_time += value

    @property
    def avg_execution_time(self) -> float:
        completed = self.successful_bookings + self.failed_bookings
        if completed == 0:
            return 0.0
        return self.total_execution_time / completed

    @property
    def success_rate(self) -> float:
        if self.total_attempts == 0:
            return 0.0
        return (self.successful_bookings / self.total_attempts) * 100

    def format_report(self) -> str:
        lines = [
            "📊 Reservation Scheduler Performance Report",
            f"✅ Successful: {self.successful_bookings}",
            f"❌ Failed: {self.failed_bookings}",
            f"📈 Total Attempts: {self.total_attempts}",
            f"🏆 Success Rate: {self.success_rate:.2f}%",
            f"⏱️ Avg Execution Time: {self.avg_execution_time:.2f}s",
        ]
        if self.health_checks_performed:
            lines.append(f"🩺 Health Checks: {self.health_checks_performed}")
        if self.recovery_attempts:
            lines.append(f"🛠️ Recovery Attempts: {self.recovery_attempts}")
        return "\n".join(lines)
