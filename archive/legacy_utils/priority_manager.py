"""Compatibility shim for the relocated priority manager."""

from importlib import import_module

_module = import_module("automation.executors.priority_manager")

globals().update(_module.__dict__)
__all__ = getattr(_module, '__all__', [name for name in globals() if not name.startswith('_')])
