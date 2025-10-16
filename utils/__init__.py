# Utils package for Tennis Bot
"""
Helper modules for the Tennis Reservation Bot
"""

# Only import modules that exist and are safe to import

from __future__ import annotations
from utils.tracking import t

from importlib import import_module
from typing import TYPE_CHECKING

if TYPE_CHECKING:  # pragma: no cover
    from automation.browser import BrowserHelpers
    from automation.executors.booking_orchestrator import DynamicBookingOrchestrator


__all__ = [
    'BrowserHelpers',
    'DynamicBookingOrchestrator',
]


def __getattr__(name: str):
    t('utils.__getattr__')
    if name == 'BrowserHelpers':
        module = import_module('automation.browser')
    elif name == 'DynamicBookingOrchestrator':
        module = import_module('automation.executors.booking_orchestrator')
    else:
        raise AttributeError(name)
    return getattr(module, name)
