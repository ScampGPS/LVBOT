"""Compatibility package forwarding to reservations modules."""
from importlib import import_module
from typing import Any
import sys

__all__ = [
    "queue",
    "models",
    "services",
]


def __getattr__(name: str) -> Any:
    if name in {"queue", "models", "services"}:
        module = import_module(f"reservations.{name}")
        sys.modules.setdefault(f"{__name__}.{name}", module)
        return module
    raise AttributeError(name)
