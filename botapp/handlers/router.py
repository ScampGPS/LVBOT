"""Declarative callback routing utilities."""

from __future__ import annotations
from tracking import t
from dataclasses import dataclass
from typing import Awaitable, Callable, List, Optional, Tuple

from telegram import Update
from telegram.ext import ContextTypes

CallbackHandlerFn = Callable[[Update, ContextTypes.DEFAULT_TYPE], Awaitable[object]]
Predicate = Callable[[str], bool]


@dataclass
class CallbackRoute:
    """Route definition for exact matches."""

    token: str
    handler: CallbackHandlerFn


@dataclass
class PrefixRoute:
    """Route definition for prefix-based matches."""

    prefix: str
    handler: CallbackHandlerFn


@dataclass
class PredicateRoute:
    """Route definition for predicate-based matches."""

    predicate: Predicate
    handler: CallbackHandlerFn


class CallbackRouter:
    """Routes callback query data to async handlers."""

    def __init__(self, default_handler: CallbackHandlerFn) -> None:
        t('botapp.handlers.router.CallbackRouter.__init__')
        self._default_handler = default_handler
        self._exact_routes: dict[str, CallbackHandlerFn] = {}
        self._prefix_routes: List[PrefixRoute] = []
        self._predicate_routes: List[PredicateRoute] = []

    def add_exact(self, token: str, handler: CallbackHandlerFn) -> None:
        t('botapp.handlers.router.CallbackRouter.add_exact')
        self._exact_routes[token] = handler

    def add_prefix(self, prefix: str, handler: CallbackHandlerFn) -> None:
        t('botapp.handlers.router.CallbackRouter.add_prefix')
        self._prefix_routes.append(PrefixRoute(prefix=prefix, handler=handler))

    def add_predicate(self, predicate: Predicate, handler: CallbackHandlerFn) -> None:
        t('botapp.handlers.router.CallbackRouter.add_predicate')
        self._predicate_routes.append(PredicateRoute(predicate=predicate, handler=handler))

    async def dispatch(self, update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
        t('botapp.handlers.router.CallbackRouter.dispatch')
        query = update.callback_query
        if not query or not query.data:
            await self._default_handler(update, context)
            return

        data = query.data

        handler = self._exact_routes.get(data)
        if handler:
            await handler(update, context)
            return

        for route in self._prefix_routes:
            if data.startswith(route.prefix):
                await route.handler(update, context)
                return

        for route in self._predicate_routes:
            if route.predicate(data):
                await route.handler(update, context)
                return

        await self._default_handler(update, context)


__all__ = [
    "CallbackRouter",
    "CallbackRoute",
    "PrefixRoute",
    "PredicateRoute",
]
