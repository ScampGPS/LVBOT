"""Availability detection utilities for LVBot automation."""

from .checker import AvailabilityChecker, AvailabilityCheckerV3
from .support import AcuityTimeParser, DateTimeHelpers, filter_future_times_for_today

__all__ = [
    "AvailabilityChecker",
    "AvailabilityCheckerV3",
    "AvailabilityCheckerV2",
    "AcuityTimeParser",
    "DateTimeHelpers",
    "filter_future_times_for_today",
]


class AvailabilityCheckerV2(AvailabilityChecker):
    """Deprecated alias kept for backwards compatibility."""

    def __init__(self, *args, **kwargs):
        raise RuntimeError("AvailabilityCheckerV2 has been replaced by AvailabilityChecker")
