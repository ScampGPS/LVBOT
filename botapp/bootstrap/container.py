"""Dependency container wiring bot runtime components together."""

from __future__ import annotations
from tracking import t

from dataclasses import dataclass
from typing import Any, Callable, Dict, Optional

from automation.availability import AvailabilityChecker
from automation.browser.async_browser_pool import AsyncBrowserPool
from automation.browser.manager import BrowserManager
from reservations.queue import ReservationQueue, ReservationScheduler
from reservations.services import ReservationService
from users.manager import UserManager

from botapp.config import BotAppConfig
from botapp.handlers.callback_handlers import CallbackHandler

from .browser_pool_factory import build_browser_resources
from .reservation_setup import build_reservation_components


@dataclass(frozen=True)
class BotDependencies:
    """Concrete dependency snapshot for the Telegram bot runtime."""

    config: BotAppConfig
    browser_pool: AsyncBrowserPool
    browser_manager: BrowserManager
    availability_checker: AvailabilityChecker
    user_manager: UserManager
    reservation_service: ReservationService
    reservation_queue: ReservationQueue
    scheduler: ReservationScheduler
    callback_handler: CallbackHandler

    def as_dict(self) -> Dict[str, Any]:
        """Return dependencies as a mapping keyed by attribute name."""

        return {
            'config': self.config,
            'browser_pool': self.browser_pool,
            'browser_manager': self.browser_manager,
            'availability_checker': self.availability_checker,
            'user_manager': self.user_manager,
            'reservation_service': self.reservation_service,
            'reservation_queue': self.reservation_queue,
            'scheduler': self.scheduler,
            'callback_handler': self.callback_handler,
        }


class DependencyContainer:
    """Lazy dependency container with optional override support."""

    def __init__(
        self,
        config: BotAppConfig,
        overrides: Optional[Dict[str, Any]] = None,
    ) -> None:
        t('botapp.bootstrap.container.DependencyContainer.__init__')
        self.config = config
        self._cache: Dict[str, Any] = {}
        if overrides:
            self._cache.update(overrides)

    # ------------------------------------------------------------------
    # Internal helpers
    def _resolve(self, key: str, factory: Callable[[], Any]) -> Any:
        if key not in self._cache:
            self._cache[key] = factory()
        return self._cache[key]

    def _browser_bundle(self) -> tuple[AsyncBrowserPool, BrowserManager, AvailabilityChecker]:
        def factory() -> tuple[AsyncBrowserPool, BrowserManager, AvailabilityChecker]:
            pool, manager, checker = build_browser_resources(self.config)
            return pool, manager, checker

        return self._resolve('_browser_bundle', factory)

    # ------------------------------------------------------------------
    # Core dependencies
    @property
    def browser_pool(self) -> AsyncBrowserPool:
        t('botapp.bootstrap.container.DependencyContainer.browser_pool')
        pool, _, _ = self._browser_bundle()
        return self._cache.setdefault('browser_pool', pool)

    @property
    def browser_manager(self) -> BrowserManager:
        t('botapp.bootstrap.container.DependencyContainer.browser_manager')
        _, manager, _ = self._browser_bundle()
        return self._cache.setdefault('browser_manager', manager)

    @property
    def availability_checker(self) -> AvailabilityChecker:
        t('botapp.bootstrap.container.DependencyContainer.availability_checker')
        _, _, checker = self._browser_bundle()
        return self._cache.setdefault('availability_checker', checker)

    @property
    def user_manager(self) -> UserManager:
        t('botapp.bootstrap.container.DependencyContainer.user_manager')

        def factory() -> UserManager:
            return UserManager(self.config.paths.users_file)

        return self._resolve('user_manager', factory)

    @property
    def reservation_queue(self) -> ReservationQueue:
        t('botapp.bootstrap.container.DependencyContainer.reservation_queue')

        def factory() -> ReservationQueue:
            return ReservationQueue(self.config.paths.queue_file)

        return self._resolve('reservation_queue', factory)

    def build_reservation_service(
        self,
        notification_callback: Callable[[int, str], Any],
        *,
        executor_config: Optional[Any] = None,
    ) -> ReservationService:
        """Construct the reservation service if not already available."""

        t('botapp.bootstrap.container.DependencyContainer.build_reservation_service')

        def factory() -> ReservationService:
            service, queue, scheduler = build_reservation_components(
                self.config,
                notification_callback,
                self.user_manager,
                self.browser_pool,
                queue=self.reservation_queue,
            )

            # Cache queue and scheduler so subsequent lookups return the same objects.
            self._cache['reservation_queue'] = queue
            self._cache['scheduler'] = scheduler
            return service

        service: ReservationService = self._resolve('reservation_service', factory)

        if executor_config is not None:
            service.scheduler.executor_config = executor_config

        return service

    @property
    def scheduler(self) -> ReservationScheduler:
        t('botapp.bootstrap.container.DependencyContainer.scheduler')

        if 'scheduler' not in self._cache:
            raise RuntimeError(
                "Reservation service has not been initialised; call "
                "build_reservation_service() before requesting the scheduler."
            )
        return self._cache['scheduler']

    @property
    def callback_handler(self) -> CallbackHandler:
        t('botapp.bootstrap.container.DependencyContainer.callback_handler')

        def factory() -> CallbackHandler:
            return CallbackHandler(
                self.availability_checker,
                self.reservation_queue,
                self.user_manager,
                self.browser_pool,
            )

        return self._resolve('callback_handler', factory)

    # ------------------------------------------------------------------
    def build_dependencies(
        self,
        notification_callback,
        *,
        executor_config: Optional[Any] = None,
    ) -> BotDependencies:
        """Materialise and return all core dependencies."""

        t('botapp.bootstrap.container.DependencyContainer.build_dependencies')

        service = self.build_reservation_service(
            notification_callback,
            executor_config=executor_config,
        )

        return BotDependencies(
            config=self.config,
            browser_pool=self.browser_pool,
            browser_manager=self.browser_manager,
            availability_checker=self.availability_checker,
            user_manager=self.user_manager,
            reservation_service=service,
            reservation_queue=self.reservation_queue,
            scheduler=service.scheduler,
            callback_handler=self.callback_handler,
        )


__all__ = ['BotDependencies', 'DependencyContainer']
