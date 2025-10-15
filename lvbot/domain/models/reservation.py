"""Domain dataclasses for reservations and results."""

from __future__ import annotations

from dataclasses import dataclass, field
from datetime import date, datetime
from typing import List, Optional


@dataclass(frozen=True)
class UserProfile:
    """Minimal user profile required for queueing and scheduling."""

    user_id: int
    first_name: str
    last_name: str
    email: str
    phone: str
    tier: Optional[str] = None


@dataclass(frozen=True)
class ReservationRequest:
    """Represents a reservation request placed in the queue."""

    request_id: Optional[str]
    user: UserProfile
    target_date: date
    target_time: str
    court_preferences: List[int] = field(default_factory=list)
    created_at: datetime = field(default_factory=datetime.utcnow)
    status: str = "pending"


@dataclass(frozen=True)
class BookingResult:
    """Outcome of a booking attempt."""

    success: bool
    message: Optional[str] = None
    court_reserved: Optional[int] = None
    time_reserved: Optional[str] = None
    confirmation_code: Optional[str] = None
