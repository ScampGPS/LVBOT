"""Shared fakes and utilities for unit tests."""

from __future__ import annotations
from tracking import t

from typing import Any, Dict, List, Tuple


class DummyLogger:
    """Lightweight stand-in for ``logging.Logger`` that records calls."""

    def __init__(self) -> None:
        t('tests.helpers.DummyLogger.__init__')
        self.records: List[Tuple[str, Tuple[Any, ...], Dict[str, Any]]] = []
        # ``entries`` is kept for compatibility with existing assertions.
        self.entries = self.records

    def _record(self, level: str, *args: Any, **kwargs: Any) -> None:
        t('tests.helpers.DummyLogger._record')
        self.records.append((level, args, kwargs))

    def debug(self, *args: Any, **kwargs: Any) -> None:
        t('tests.helpers.DummyLogger.debug')
        self._record("debug", *args, **kwargs)

    def info(self, *args: Any, **kwargs: Any) -> None:
        t('tests.helpers.DummyLogger.info')
        self._record("info", *args, **kwargs)

    def warning(self, *args: Any, **kwargs: Any) -> None:
        t('tests.helpers.DummyLogger.warning')
        self._record("warning", *args, **kwargs)

    def error(self, *args: Any, **kwargs: Any) -> None:
        t('tests.helpers.DummyLogger.error')
        self._record("error", *args, **kwargs)

    def critical(self, *args: Any, **kwargs: Any) -> None:
        t('tests.helpers.DummyLogger.critical')
        self._record("critical", *args, **kwargs)

    def exception(self, *args: Any, **kwargs: Any) -> None:
        t('tests.helpers.DummyLogger.exception')
        self._record("exception", *args, **kwargs)

    @property
    def messages(self) -> List[Tuple[str, Any]]:
        """Return formatted messages for quick assertions."""
        t('tests.helpers.DummyLogger.messages')

        formatted: List[Tuple[str, Any]] = []
        for level, args, kwargs in self.records:
            message: Any = kwargs.get("msg")
            if args:
                template = args[0]
                if isinstance(template, str) and len(args) > 1:
                    try:
                        message = template % args[1:]
                    except (TypeError, ValueError):
                        message = template
                else:
                    message = template
            formatted.append((level, message))
        return formatted

    def clear(self) -> None:
        t('tests.helpers.DummyLogger.clear')
        self.records.clear()

    def last(self, level: str | None = None) -> Tuple[str, Tuple[Any, ...], Dict[str, Any]] | None:
        """Return the most recent record, optionally filtered by level."""
        t('tests.helpers.DummyLogger.last')

        if not self.records:
            return None
        if level is None:
            return self.records[-1]
        for entry in reversed(self.records):
            if entry[0] == level:
                return entry
        return None
