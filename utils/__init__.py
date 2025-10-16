# Utils package for Tennis Bot
"""
Helper modules for the Tennis Reservation Bot
"""

# Only import modules that exist and are safe to import

from __future__ import annotations

from importlib import import_module
from typing import TYPE_CHECKING

if TYPE_CHECKING:  # pragma: no cover
    from lvbot.automation.browser.async_browser_helpers import BrowserHelpers
    from lvbot.automation.executors.booking_orchestrator import DynamicBookingOrchestrator
    from lvbot.automation.browser.browser_allocation import BrowserAllocationHelper


__all__ = [
    'BrowserHelpers',
    'DynamicBookingOrchestrator', 
    'BrowserAllocationHelper'
]


def __getattr__(name: str):
    if name == 'BrowserHelpers':
        module = import_module('lvbot.automation.browser.async_browser_helpers')
    elif name == 'DynamicBookingOrchestrator':
        module = import_module('lvbot.automation.executors.booking_orchestrator')
    elif name == 'BrowserAllocationHelper':
        module = import_module('lvbot.automation.browser.browser_allocation')
    else:
        raise AttributeError(name)
    return getattr(module, name)
