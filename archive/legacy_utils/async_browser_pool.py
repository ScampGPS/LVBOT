"""Compatibility shim for migrated module."""
from importlib import import_module

_module = import_module("lvbot.automation.browser.async_browser_pool")

globals().update(_module.__dict__)
__all__ = getattr(_module, '__all__', [name for name in globals() if not name.startswith('_')])
