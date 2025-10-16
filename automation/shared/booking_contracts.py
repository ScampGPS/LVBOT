"""Shared booking request/result contracts for bot, scheduler, and executors."""

from __future__ import annotations

from dataclasses import dataclass, field
from datetime import date, datetime
from enum import Enum
from typing import Dict, Iterable, List, Optional, Sequence, Tuple


class BookingSource(Enum):
    """Indicates which subsystem originated the booking request."""

    IMMEDIATE = "immediate"
    QUEUED = "queued"
    TENNIS = "tennis"
    ADMIN = "admin"
    RETRY = "retry"


@dataclass(frozen=True)
class CourtPreference:
    """Preferred courts in order of priority."""

    primary: int
    fallbacks: Tuple[int, ...] = field(default_factory=tuple)

    @classmethod
    def from_sequence(cls, courts: Sequence[int]) -> "CourtPreference":
        if not courts:
            raise ValueError("At least one court must be provided")
        primary, *rest = courts
        return cls(primary=primary, fallbacks=tuple(rest))

    def as_list(self) -> List[int]:
        return [self.primary, *self.fallbacks]


@dataclass(frozen=True)
class BookingUser:
    """Minimal user data required for bookings and messaging."""

    user_id: int
    first_name: str
    last_name: str
    email: str
    phone: str
    tier: Optional[str] = None


@dataclass(frozen=True)
class BookingRequest:
    """Canonical payload consumed by executors and schedulers."""

    request_id: Optional[str]
    source: BookingSource
    user: BookingUser
    target_date: date
    target_time: str
    court_preference: CourtPreference
    created_at: datetime = field(default_factory=datetime.utcnow)
    metadata: Dict[str, object] = field(default_factory=dict)
    executor_config: Optional[Dict[str, object]] = None

    def preferred_courts(self) -> List[int]:
        """Return courts in priority order."""

        return self.court_preference.as_list()

    @classmethod
    def from_immediate_payload(
        cls,
        user: BookingUser,
        target_date: date,
        time_slot: str,
        court_number: int,
        *,
        metadata: Optional[Dict[str, object]] = None,
        executor_config: Optional[Dict[str, object]] = None,
    ) -> "BookingRequest":
        """Build a request for immediate bookings triggered by the bot."""

        return cls(
            request_id=None,
            source=BookingSource.IMMEDIATE,
            user=user,
            target_date=target_date,
            target_time=time_slot,
            court_preference=CourtPreference(primary=court_number, fallbacks=tuple()),
            metadata=dict(metadata or {}),
            executor_config=dict(executor_config or {}) if executor_config else None,
        )

    @classmethod
    def from_reservation_record(
        cls,
        request_id: str,
        user: BookingUser,
        target_date: date,
        target_time: str,
        courts: Iterable[int],
        *,
        source: BookingSource = BookingSource.QUEUED,
        metadata: Optional[Dict[str, object]] = None,
        executor_config: Optional[Dict[str, object]] = None,
    ) -> "BookingRequest":
        """Create a request based on a queued reservation record."""

        preference = CourtPreference.from_sequence(list(courts))
        return cls(
            request_id=request_id,
            source=source,
            user=user,
            target_date=target_date,
            target_time=target_time,
            court_preference=preference,
            metadata=dict(metadata or {}),
            executor_config=dict(executor_config or {}) if executor_config else None,
        )


class BookingStatus(Enum):
    """Overall result of a booking attempt."""

    SUCCESS = "success"
    FAILURE = "failure"
    PARTIAL = "partial"


@dataclass(frozen=True)
class BookingResult:
    """Canonical result surfaced to messaging, persistence, and monitoring."""

    status: BookingStatus
    user: BookingUser
    request_id: Optional[str]
    court_reserved: Optional[int]
    time_reserved: Optional[str]
    confirmation_code: Optional[str]
    confirmation_url: Optional[str]
    message: Optional[str] = None
    errors: Tuple[str, ...] = field(default_factory=tuple)
    started_at: Optional[datetime] = None
    completed_at: Optional[datetime] = None
    metadata: Dict[str, object] = field(default_factory=dict)

    @property
    def success(self) -> bool:
        return self.status == BookingStatus.SUCCESS

    @classmethod
    def success_result(
        cls,
        user: BookingUser,
        request_id: Optional[str],
        court_reserved: int,
        time_reserved: str,
        *,
        confirmation_code: Optional[str] = None,
        confirmation_url: Optional[str] = None,
        message: Optional[str] = None,
        metadata: Optional[Dict[str, object]] = None,
        started_at: Optional[datetime] = None,
        completed_at: Optional[datetime] = None,
    ) -> "BookingResult":
        return cls(
            status=BookingStatus.SUCCESS,
            user=user,
            request_id=request_id,
            court_reserved=court_reserved,
            time_reserved=time_reserved,
            confirmation_code=confirmation_code,
            confirmation_url=confirmation_url,
            message=message,
            metadata=dict(metadata or {}),
            started_at=started_at,
            completed_at=completed_at,
        )

    @classmethod
    def failure_result(
        cls,
        user: BookingUser,
        request_id: Optional[str],
        *,
        message: Optional[str] = None,
        errors: Optional[Iterable[str]] = None,
        metadata: Optional[Dict[str, object]] = None,
        started_at: Optional[datetime] = None,
        completed_at: Optional[datetime] = None,
    ) -> "BookingResult":
        return cls(
            status=BookingStatus.FAILURE,
            user=user,
            request_id=request_id,
            court_reserved=None,
            time_reserved=None,
            confirmation_code=None,
            confirmation_url=None,
            message=message,
            errors=tuple(errors or ()),
            metadata=dict(metadata or {}),
            started_at=started_at,
            completed_at=completed_at,
        )

    def merge_metadata(self, extra: Dict[str, object]) -> "BookingResult":
        """Return a new result with metadata merged in."""

        merged = {**self.metadata, **extra}
        return BookingResult(
            status=self.status,
            user=self.user,
            request_id=self.request_id,
            court_reserved=self.court_reserved,
            time_reserved=self.time_reserved,
            confirmation_code=self.confirmation_code,
            confirmation_url=self.confirmation_url,
            message=self.message,
            errors=self.errors,
            started_at=self.started_at,
            completed_at=self.completed_at,
            metadata=merged,
        )

