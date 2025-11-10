"""Domain service encapsulating reservation queue and scheduler."""

from __future__ import annotations
from tracking import t

import logging
from datetime import date
from typing import Iterable, List, Optional

from reservations.models import ReservationRequest, UserProfile
from reservations.queue import ReservationQueue, ReservationScheduler
from reservations.queue.reservation_tracker import ReservationTracker
from users.manager import UserManager
from automation.executors import AsyncExecutorConfig


class ReservationService:
    """High-level API for reservation orchestration."""

    def __init__(
        self,
        config,
        notification_callback,
        queue: Optional[ReservationQueue] = None,
        scheduler: Optional[ReservationScheduler] = None,
        user_manager: Optional[UserManager] = None,
        browser_pool=None,
        executor_config: Optional[AsyncExecutorConfig] = None,
        bot_handler=None,
        reservation_tracker: Optional[ReservationTracker] = None,
    ) -> None:
        t('reservations.services.reservation_service.ReservationService.__init__')
        self.logger = logging.getLogger(self.__class__.__name__)
        self.queue = queue or ReservationQueue()
        self.reservation_tracker = reservation_tracker or ReservationTracker()
        self.user_manager = user_manager
        self.scheduler = scheduler or ReservationScheduler(
            config=config,
            queue=self.queue,
            notification_callback=notification_callback,
            browser_pool=browser_pool,
            user_manager=user_manager,
            executor_config=executor_config,
            bot_handler=bot_handler,
            reservation_tracker=self.reservation_tracker,
        )

    def enqueue(self, request: ReservationRequest) -> str:
        """Add a reservation request to the queue."""
        t('reservations.services.reservation_service.ReservationService.enqueue')

        reservation_id = self.queue.add_reservation_request(request)
        self.logger.info("Queued reservation %s for user %s", reservation_id, request.user.user_id)
        return reservation_id

    def list_requests(self) -> List[ReservationRequest]:
        """Return all requests as dataclasses."""
        t('reservations.services.reservation_service.ReservationService.list_requests')

        return self.queue.list_reservations()

    def start_scheduler(self) -> None:
        """Start the reservation scheduler thread if not running."""
        t('reservations.services.reservation_service.ReservationService.start_scheduler')

        if not self.scheduler.running:
            self.logger.info("Starting reservation scheduler")
            self.scheduler.start()

    def stop_scheduler(self) -> None:
        """Stop the reservation scheduler if running."""
        t('reservations.services.reservation_service.ReservationService.stop_scheduler')

        if self.scheduler.running:
            self.logger.info("Stopping reservation scheduler")
            self.scheduler.stop()

    def is_scheduler_running(self) -> bool:
        t('reservations.services.reservation_service.ReservationService.is_scheduler_running')
        return self.scheduler.running

    def get_queue_statistics(self) -> dict:
        t('reservations.services.reservation_service.ReservationService.get_queue_statistics')
        return self.queue._get_status_counts()

    def build_request(
        self,
        user: UserProfile,
        target_date: date,
        target_time: str,
        court_preferences: Iterable[int],
    ) -> ReservationRequest:
        t('reservations.services.reservation_service.ReservationService.build_request')
        return ReservationRequest(
            request_id=None,
            user=user,
            target_date=target_date,
            target_time=target_time,
            court_preferences=list(court_preferences),
        )
