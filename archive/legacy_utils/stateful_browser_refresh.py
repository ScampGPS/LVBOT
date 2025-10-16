"""Compatibility shim for archived stateful browser refresh helper."""

from importlib import util
from pathlib import Path

_archive_path = Path(__file__).resolve().parents[1] / "legacy_modules" / "browser_cleanup" / "stateful_browser_refresh.py"

if not _archive_path.exists():  # pragma: no cover - defensive guard
    raise ImportError("Stateful browser refresh helper has been removed from the active code base.")

_spec = util.spec_from_file_location("lvbot.archive.browser_cleanup.stateful_browser_refresh", _archive_path)
if _spec is None or _spec.loader is None:  # pragma: no cover - defensive guard
    raise ImportError(f"Unable to load archived stateful browser refresh module at {_archive_path}")

_module = util.module_from_spec(_spec)
_spec.loader.exec_module(_module)

globals().update(_module.__dict__)
__all__ = getattr(_module, '__all__', [name for name in globals() if not name.startswith('_')])
