"""Domain model definitions for LVBot."""

from .time_slot import TimeSlot
from .reservation import ReservationRequest, BookingResult, UserProfile

__all__ = ["TimeSlot", "ReservationRequest", "BookingResult", "UserProfile"]
