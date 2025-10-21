"""Bootstrap helpers for wiring bot infrastructure components."""

from .browser_pool_factory import build_browser_resources
from .reservation_setup import build_reservation_components
from .container import BotDependencies, DependencyContainer

__all__ = [
    'build_browser_resources',
    'build_reservation_components',
    'BotDependencies',
    'DependencyContainer',
]
