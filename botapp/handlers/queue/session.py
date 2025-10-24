"""Typed helpers for storing queue booking session data."""

from __future__ import annotations
from tracking import t

from dataclasses import dataclass, field
from datetime import date
from typing import Any, Dict, Iterable, List, Optional

from telegram.ext import ContextTypes

from botapp.handlers.state import get_session_state


@dataclass
class QueueSessionData:
    """Represents the queue booking session values stored in user data."""

    selected_date: Optional[date] = None
    selected_time: Optional[str] = None
    selected_courts: List[int] = field(default_factory=list)
    summary: Dict[str, Any] = field(default_factory=dict)
    modifying_reservation_id: Optional[str] = None
    modifying_option: Optional[str] = None


LEGACY_DATE_KEY = 'queue_booking_date'
LEGACY_TIME_KEY = 'queue_booking_time'
LEGACY_COURTS_KEY = 'queue_booking_courts'
LEGACY_SUMMARY_KEY = 'queue_booking_summary'
LEGACY_MODIFY_ID_KEY = 'modifying_reservation_id'
LEGACY_MODIFY_OPTION_KEY = 'modifying_option'


_MISSING = object()


class QueueSessionStore:
    """Stateful helper encapsulating queue booking session persistence."""

    def __init__(self, context: ContextTypes.DEFAULT_TYPE) -> None:
        t('botapp.handlers.queue.session.QueueSessionStore.__init__')
        self._context = context

    @classmethod
    def from_context(cls, context: ContextTypes.DEFAULT_TYPE) -> 'QueueSessionStore':
        """Alternate constructor for compatibility with legacy helpers."""

        t('botapp.handlers.queue.session.QueueSessionStore.from_context')
        return cls(context)

    def _load(self) -> QueueSessionData:
        return _ensure_state(self._context)

    def _persist(self, data: QueueSessionData) -> None:
        _persist_state(self._context, data)

    def update(
        self,
        *,
        date: Optional[date] = _MISSING,
        time: Optional[str] = _MISSING,
        courts: Optional[Iterable[int]] = _MISSING,
        summary: Optional[Dict[str, Any]] = _MISSING,
        modifying_reservation_id: Optional[str] = _MISSING,
        modifying_option: Optional[str] = _MISSING,
    ) -> QueueSessionData:
        """Mutate stored values and persist in a single operation."""

        t('botapp.handlers.queue.session.QueueSessionStore.update')
        data = self._load()

        if date is not _MISSING:
            data.selected_date = date

        if time is not _MISSING:
            data.selected_time = time

        if courts is not _MISSING:
            cleaned: List[int] = []
            if courts:
                cleaned = sorted({int(court) for court in courts})
            data.selected_courts = cleaned

        if summary is not _MISSING:
            data.summary = dict(summary or {})

        if modifying_reservation_id is not _MISSING:
            data.modifying_reservation_id = modifying_reservation_id

        if modifying_option is not _MISSING:
            data.modifying_option = modifying_option

        self._persist(data)
        return data

    def clear(self) -> None:
        """Reset all stored values."""

        t('botapp.handlers.queue.session.QueueSessionStore.clear')
        self._persist(QueueSessionData())

    @property
    def selected_date(self) -> Optional[date]:
        return self._load().selected_date

    @selected_date.setter
    def selected_date(self, value: Optional[date]) -> None:
        self.update(date=value)

    @property
    def selected_time(self) -> Optional[str]:
        return self._load().selected_time

    @selected_time.setter
    def selected_time(self, value: Optional[str]) -> None:
        self.update(time=value)

    @property
    def selected_courts(self) -> List[int]:
        return list(self._load().selected_courts)

    @selected_courts.setter
    def selected_courts(self, values: Iterable[int]) -> None:
        self.update(courts=values)

    @property
    def summary(self) -> Dict[str, Any]:
        return dict(self._load().summary)

    @summary.setter
    def summary(self, value: Dict[str, Any]) -> None:
        self.update(summary=value)

    @property
    def modification(self) -> tuple[Optional[str], Optional[str]]:
        data = self._load()
        return data.modifying_reservation_id, data.modifying_option

    def set_modification(
        self,
        reservation_id: Optional[str],
        option: Optional[str],
    ) -> None:
        self.update(
            modifying_reservation_id=reservation_id,
            modifying_option=option,
        )

    def clear_summary(self) -> None:
        self.update(summary={})


def _ensure_state(context: ContextTypes.DEFAULT_TYPE) -> QueueSessionData:
    """Return a mutable data object backed by the typed session state."""

    t('botapp.handlers.queue.session._ensure_state')
    state = get_session_state(context).queue
    data = QueueSessionData(
        selected_date=_coerce_date(state.booking_date),
        selected_time=state.booking_time,
        selected_courts=list(state.courts or []),
        summary=dict(state.summary or {}),
        modifying_reservation_id=state.modifying_reservation_id,
        modifying_option=state.modifying_option,
    )
    user_data = context.user_data
    if data.selected_date is None and LEGACY_DATE_KEY in user_data:
        data.selected_date = _coerce_date(user_data.get(LEGACY_DATE_KEY))
    if data.selected_time is None and LEGACY_TIME_KEY in user_data:
        data.selected_time = user_data.get(LEGACY_TIME_KEY)
    if not data.selected_courts and LEGACY_COURTS_KEY in user_data:
        data.selected_courts = list(user_data.get(LEGACY_COURTS_KEY) or [])
    if not data.summary and LEGACY_SUMMARY_KEY in user_data:
        raw_summary = user_data.get(LEGACY_SUMMARY_KEY) or {}
        if isinstance(raw_summary, dict):
            data.summary = dict(raw_summary)
    if data.modifying_reservation_id is None and LEGACY_MODIFY_ID_KEY in user_data:
        data.modifying_reservation_id = user_data.get(LEGACY_MODIFY_ID_KEY)
    if data.modifying_option is None and LEGACY_MODIFY_OPTION_KEY in user_data:
        data.modifying_option = user_data.get(LEGACY_MODIFY_OPTION_KEY)
    return data


def _persist_state(context: ContextTypes.DEFAULT_TYPE, data: QueueSessionData) -> None:
    """Persist the provided data into both typed state and legacy keys."""

    t('botapp.handlers.queue.session._persist_state')
    state = get_session_state(context).queue
    state.booking_date = data.selected_date.isoformat() if data.selected_date else None
    state.booking_time = data.selected_time
    state.courts = list(data.selected_courts)
    state.summary = dict(data.summary)
    state.modifying_reservation_id = data.modifying_reservation_id
    state.modifying_option = data.modifying_option

    user_data = context.user_data
    if data.selected_date is not None:
        user_data[LEGACY_DATE_KEY] = data.selected_date
    else:
        user_data.pop(LEGACY_DATE_KEY, None)

    if data.selected_time is not None:
        user_data[LEGACY_TIME_KEY] = data.selected_time
    else:
        user_data.pop(LEGACY_TIME_KEY, None)

    if data.selected_courts:
        user_data[LEGACY_COURTS_KEY] = list(data.selected_courts)
    else:
        user_data.pop(LEGACY_COURTS_KEY, None)

    if data.summary:
        user_data[LEGACY_SUMMARY_KEY] = dict(data.summary)
    else:
        user_data.pop(LEGACY_SUMMARY_KEY, None)

    if data.modifying_reservation_id:
        user_data[LEGACY_MODIFY_ID_KEY] = data.modifying_reservation_id
    else:
        user_data.pop(LEGACY_MODIFY_ID_KEY, None)

    if data.modifying_option:
        user_data[LEGACY_MODIFY_OPTION_KEY] = data.modifying_option
    else:
        user_data.pop(LEGACY_MODIFY_OPTION_KEY, None)


def _coerce_date(value: Optional[Any]) -> Optional[date]:
    """Convert stored date representations into `date` objects."""

    t('botapp.handlers.queue.session._coerce_date')
    if isinstance(value, date):
        return value
    if isinstance(value, str) and value:
        try:
            return date.fromisoformat(value)
        except ValueError:
            return None
    return None
__all__ = ['QueueSessionStore']
