"""Shared dependency container for callback domain handlers."""

from __future__ import annotations
from dataclasses import dataclass
from typing import Any

from botapp.booking.immediate_handler import ImmediateBookingHandler


@dataclass
class CallbackDependencies:
    logger: Any
    availability_checker: Any
    reservation_queue: Any
    user_manager: Any
    browser_pool: Any
    booking_handler: ImmediateBookingHandler
    reservation_tracker: Any


__all__ = ["CallbackDependencies"]
