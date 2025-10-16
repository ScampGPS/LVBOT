"""Domain service encapsulating reservation queue and scheduler."""

from __future__ import annotations

import logging
from datetime import date
from typing import Iterable, List, Optional

from lvbot.reservations.models import ReservationRequest, UserProfile
from lvbot.reservations.queue import ReservationQueue, ReservationScheduler
from lvbot.users.manager import UserManager
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
    ) -> None:
        self.logger = logging.getLogger(self.__class__.__name__)
        self.queue = queue or ReservationQueue()
        self.user_manager = user_manager
        self.scheduler = scheduler or ReservationScheduler(
            config=config,
            queue=self.queue,
            notification_callback=notification_callback,
            browser_pool=browser_pool,
            user_manager=user_manager,
            executor_config=executor_config,
        )

    def enqueue(self, request: ReservationRequest) -> str:
        """Add a reservation request to the queue."""

        reservation_id = self.queue.add_reservation_request(request)
        self.logger.info("Queued reservation %s for user %s", reservation_id, request.user.user_id)
        return reservation_id

    def list_requests(self) -> List[ReservationRequest]:
        """Return all requests as dataclasses."""

        return self.queue.list_reservations()

    def start_scheduler(self) -> None:
        """Start the reservation scheduler thread if not running."""

        if not self.scheduler.running:
            self.logger.info("Starting reservation scheduler")
            self.scheduler.start()

    def stop_scheduler(self) -> None:
        """Stop the reservation scheduler if running."""

        if self.scheduler.running:
            self.logger.info("Stopping reservation scheduler")
            self.scheduler.stop()

    def is_scheduler_running(self) -> bool:
        return self.scheduler.running

    def get_queue_statistics(self) -> dict:
        return self.queue._get_status_counts()

    def build_request(
        self,
        user: UserProfile,
        target_date: date,
        target_time: str,
        court_preferences: Iterable[int],
    ) -> ReservationRequest:
        return ReservationRequest(
            request_id=None,
            user=user,
            target_date=target_date,
            target_time=target_time,
            court_preferences=list(court_preferences),
        )
