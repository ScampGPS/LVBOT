"""Runtime helpers for tracking which functions execute in production."""

from __future__ import annotations

import threading
from pathlib import Path
from typing import Set

_LOCK = threading.RLock()
_TRACKING_DIR = Path(__file__).resolve().parent
_TRACKING_FILE = _TRACKING_DIR / "functions_in_use.txt"
_LEGACY_TRACKING_FILE = _TRACKING_DIR.parent / "logs" / "functions_in_use.txt"
_SEEN: Set[str] = set()


def _read_existing_entries(path: Path) -> Set[str]:
    if not path.exists():
        return set()
    try:
        with path.open("r", encoding="utf-8") as handle:
            return {line.strip() for line in handle if line.strip()}
    except OSError:
        return set()


def _initialize_seen_cache() -> None:
    current_entries = _read_existing_entries(_TRACKING_FILE)
    legacy_entries = _read_existing_entries(_LEGACY_TRACKING_FILE)
    _SEEN.update(current_entries)
    _SEEN.update(legacy_entries)

    missing_in_current = _SEEN.difference(current_entries)
    if missing_in_current:
        _TRACKING_FILE.parent.mkdir(parents=True, exist_ok=True)
        try:
            with _TRACKING_FILE.open("a", encoding="utf-8") as handle:
                for name in sorted(missing_in_current):
                    handle.write(f"{name}\n")
        except OSError:
            # If we cannot persist the merged cache we still keep it in-memory.
            pass


_initialize_seen_cache()


def t(func_name: str) -> None:
    """Record the provided function name the first time it runs in this process."""
    if not func_name:
        return

    with _LOCK:
        if func_name in _SEEN:
            return

        _TRACKING_FILE.parent.mkdir(parents=True, exist_ok=True)
        try:
            with _TRACKING_FILE.open("a", encoding="utf-8") as handle:
                handle.write(f"{func_name}\n")
        except OSError:
            return

        _SEEN.add(func_name)
