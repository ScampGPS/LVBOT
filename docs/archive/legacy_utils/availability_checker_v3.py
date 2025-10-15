"""Compatibility shim for migrated module."""
from importlib import import_module

_module = import_module("lvbot.automation.availability.availability_checker_v3")

globals().update(_module.__dict__)
__all__ = getattr(_module, '__all__', [name for name in globals() if not name.startswith('_')])
