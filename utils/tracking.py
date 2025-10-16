"""Utilities for tracking runtime function usage."""

from __future__ import annotations

import threading
from pathlib import Path
from typing import Set

# Global lock guards access to the seen cache and file writes.
_LOCK = threading.RLock()
# Persist discovered function names alongside other run-time logs.
_TRACKING_FILE = Path(__file__).resolve().parents[1] / "logs" / "functions_in_use.txt"
# Cache of function names already written this run to avoid duplicate writes.
_SEEN: Set[str] = set()


def _initialize_seen_cache() -> None:
    """Populate the in-memory cache with any already-recorded function names."""
    if not _TRACKING_FILE.exists():
        return
    try:
        with _TRACKING_FILE.open("r", encoding="utf-8") as handle:
            _SEEN.update(line.strip() for line in handle if line.strip())
    except OSError:
        # If the file cannot be read, we continue without pre-populating the cache.
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
