"""Compatibility shim for archived reservation helper utilities."""

from importlib import util
from pathlib import Path

_archive_path = (
    Path(__file__).resolve().parents[1]
    / "legacy_modules"
    / "reservations_queue"
    / "reservation_helpers.py"
)

if not _archive_path.exists():  # pragma: no cover
    raise ImportError("ReservationHelpers have been archived and are no longer available.")

_spec = util.spec_from_file_location("lvbot.archive.reservations_queue.reservation_helpers", _archive_path)
if _spec is None or _spec.loader is None:  # pragma: no cover
    raise ImportError(f"Unable to load archived reservation helpers at {_archive_path}")

_module = util.module_from_spec(_spec)
_spec.loader.exec_module(_module)

globals().update(_module.__dict__)
__all__ = getattr(_module, '__all__', [name for name in globals() if not name.startswith('_')])
