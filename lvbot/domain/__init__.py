"""Compatibility package forwarding to lvbot.reservations."""
from importlib import import_module
from typing import Any

__all__ = [
    "queue",
    "models",
    "services",
]


def __getattr__(name: str) -> Any:
    if name in {"queue", "models", "services"}:
        return import_module(f"lvbot.reservations.{name}")
    raise AttributeError(name)
