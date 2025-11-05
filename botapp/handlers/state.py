"""Typed conversation state helpers for Telegram callback flows."""

from __future__ import annotations
from dataclasses import dataclass, field
from typing import Any, Dict, List, Optional

from telegram.ext import ContextTypes


@dataclass
class QueueBookingState:
    """State bucket for queue booking flows."""

    selected_date: Optional[str] = None
    booking_date: Optional[str] = None
    booking_time: Optional[str] = None
    courts: List[int] = field(default_factory=list)
    summary: Dict[str, Any] = field(default_factory=dict)
    selected_year: Optional[int] = None
    selected_month: Optional[str] = None
    complete_matrix: Dict[str, Any] = field(default_factory=dict)
    available_dates: List[str] = field(default_factory=list)
    modifying_reservation_id: Optional[str] = None
    modifying_option: Optional[str] = None


@dataclass
class ProfileEditState:
    """State bucket for profile edit flows."""

    editing_field: Optional[str] = None
    phone_input: str = ""
    name_input: str = ""
    editing_name_field: Optional[str] = None
    email_input: str = ""
    court_preference: Optional[list] = None


@dataclass
class CallbackSessionState:
    """Aggregate per-user callback session state."""

    flow: str = "availability_check"
    queue: QueueBookingState = field(default_factory=QueueBookingState)
    profile: ProfileEditState = field(default_factory=ProfileEditState)


SESSION_KEY = "callback_state"


def get_session_state(context: ContextTypes.DEFAULT_TYPE) -> CallbackSessionState:
    """Retrieve (or create) the callback session state for the current user."""

    state = context.user_data.get(SESSION_KEY)
    if isinstance(state, CallbackSessionState):
        return state

    state = CallbackSessionState()
    context.user_data[SESSION_KEY] = state
    return state


def reset_flow(context: ContextTypes.DEFAULT_TYPE, flow: str) -> CallbackSessionState:
    """Set the active flow identifier while returning the updated state."""

    state = get_session_state(context)
    state.flow = flow
    return state


def clear_session_state(context: ContextTypes.DEFAULT_TYPE) -> None:
    """Remove all callback session state for the current user."""

    context.user_data.pop(SESSION_KEY, None)


__all__ = [
    "CallbackSessionState",
    "QueueBookingState",
    "ProfileEditState",
    "get_session_state",
    "reset_flow",
    "clear_session_state",
]
