"""Runtime helpers for tracking how often functions execute in production."""

from __future__ import annotations

import json
import threading
from pathlib import Path
from tempfile import NamedTemporaryFile
from typing import Dict, Optional

_LOCK = threading.RLock()
_TRACKING_DIR = Path(__file__).resolve().parent
_TRACKING_FILE = _TRACKING_DIR / "function_call_counts.json"
_COUNTS: Dict[str, int] = {}


def _load_counts() -> None:
    if not _TRACKING_FILE.exists():
        return

    try:
        with _TRACKING_FILE.open("r", encoding="utf-8") as handle:
            data = json.load(handle)
    except (OSError, ValueError, TypeError):
        return

    if not isinstance(data, dict):
        return

    for name, raw_count in data.items():
        if not name:
            continue
        try:
            count = int(raw_count)
        except (TypeError, ValueError):
            continue
        _COUNTS[str(name)] = max(count, 0)


def _persist_counts_locked() -> None:
    """Persist the in-memory counts to disk. Caller must hold ``_LOCK``."""
    _TRACKING_FILE.parent.mkdir(parents=True, exist_ok=True)

    tmp_path: Optional[Path] = None
    try:
        with NamedTemporaryFile(
            "w", encoding="utf-8", dir=_TRACKING_FILE.parent, delete=False
        ) as handle:
            json.dump(_COUNTS, handle, sort_keys=True)
            handle.write("\n")
            handle.flush()
            tmp_path = Path(handle.name)

        if tmp_path is not None:
            tmp_path.replace(_TRACKING_FILE)
    except OSError:
        if tmp_path is not None:
            try:
                tmp_path.unlink()
            except OSError:
                pass


def t(func_name: str) -> None:
    """Record the provided function name each time it runs."""
    if not func_name:
        return

    with _LOCK:
        _COUNTS[func_name] = _COUNTS.get(func_name, 0) + 1
        _persist_counts_locked()


_load_counts()
