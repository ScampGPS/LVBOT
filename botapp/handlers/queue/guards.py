"""Session guard helpers for queue handlers."""

from __future__ import annotations

from typing import Iterable, Mapping, Sequence

from telegram.ext import ContextTypes

from botapp.handlers.queue.session import QueueSessionStore


class QueueSessionError(RuntimeError):
    """Base error for queue session guard failures."""


class MissingQueueSummaryError(QueueSessionError):
    """Raised when the queue booking summary is absent."""


class IncompleteProfileError(QueueSessionError):
    """Raised when the user profile is missing required fields."""

    def __init__(self, missing_fields: Sequence[str]) -> None:
        missing = tuple(missing_fields)
        super().__init__(", ".join(missing))
        self.missing_fields = missing


class MissingModificationContextError(QueueSessionError):
    """Raised when the reservation modification context is absent."""


def ensure_summary(context: ContextTypes.DEFAULT_TYPE) -> Mapping[str, object]:
    """Return the queue booking summary or raise if missing."""

    summary = QueueSessionStore(context).summary
    if not summary:
        raise MissingQueueSummaryError()
    return summary


def ensure_modification(context: ContextTypes.DEFAULT_TYPE) -> tuple[str | None, str | None]:
    """Return the reservation modification tuple or raise if missing."""

    modifying_id, option = QueueSessionStore(context).modification
    if not modifying_id:
        raise MissingModificationContextError()
    return modifying_id, option


def ensure_profile_fields(
    profile: Mapping[str, object] | None,
    required_fields: Iterable[str],
) -> None:
    """Validate required profile fields for queue booking flows."""

    required = list(required_fields)
    if not profile:
        raise IncompleteProfileError(required)

    missing = [field for field in required if not profile.get(field)]
    if missing:
        raise IncompleteProfileError(missing)
