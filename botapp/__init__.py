"""Telegram application layer with lazy exports to avoid heavy imports."""
from tracking import t

__all__ = ["CleanBot", "BotApplication"]


def __getattr__(name):
    t('botapp.__getattr__')
    if name == "CleanBot":
        from .app import CleanBot as _CleanBot

        return _CleanBot
    if name == "BotApplication":
        from .runtime.bot_application import BotApplication as _BotApplication

        return _BotApplication
    raise AttributeError(f"module 'botapp' has no attribute {name!r}")
