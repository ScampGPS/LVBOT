"""Archived browser-related modules kept for reference."""

from importlib import import_module
from typing import Any

__all__ = []


def _legacy_import(name: str) -> Any:
    module = import_module(f"archive.legacy_modules.browser_cleanup.{name}")
    return module


def __getattr__(name: str) -> Any:
    module = _legacy_import(name)
    return module
