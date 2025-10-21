"""Utilities for driving callback flows without hitting the Telegram API."""

from __future__ import annotations

import asyncio
from datetime import date, timedelta
from pathlib import Path
from tempfile import TemporaryDirectory
from typing import Any, Dict, List, Optional

from reservations.queue.reservation_queue import ReservationQueue
from users.manager import UserManager

from botapp.handlers.callback_handlers import CallbackHandler

from .fakes import FakeCallbackQuery, FakeContext, FakeUpdate, FakeUser


class _FakeAvailabilityChecker:
    """Stub implementation that satisfies the handler constructor."""

    async def check_availability(self, *args: Any, **kwargs: Any) -> List[Dict[str, Any]]:
        return []

    async def check_single_court(self, *args: Any, **kwargs: Any) -> Dict[str, Any]:
        return {}


class BotTestHarness:
    """Headless driver for exercising callback flows end-to-end."""

    def __init__(self, *, user_id: Optional[int] = None, queue_path: Optional[str] = None) -> None:
        self._records: List[Dict[str, Any]] = []
        self._tempdir: Optional[TemporaryDirectory] = None

        if queue_path:
            self.reservation_queue = ReservationQueue(queue_path)
        else:
            self._tempdir = TemporaryDirectory()
            queue_file = Path(self._tempdir.name) / "queue.json"
            self.reservation_queue = ReservationQueue(str(queue_file))

        self.user_manager = UserManager('data/users.json')
        all_users = self.user_manager.get_all_users()

        if user_id is not None:
            sample_profile = self.user_manager.get_user(user_id)
            if not sample_profile:
                raise ValueError(f"No user profile found for user_id={user_id}")
            sample_id = user_id
        else:
            try:
                sample_id, sample_profile = next(iter(all_users.items()))
            except StopIteration as exc:  # pragma: no cover - guard for empty datasets
                raise ValueError("UserManager has no user profiles to drive scenarios") from exc

        self.user = FakeUser(
            id=sample_id,
            first_name=sample_profile.get('first_name', 'Test'),
            last_name=sample_profile.get('last_name', 'User'),
            username=sample_profile.get('username', 'test_user'),
        )

        self.context = FakeContext()
        self.handler = CallbackHandler(
            _FakeAvailabilityChecker(),
            self.reservation_queue,
            self.user_manager,
            browser_pool=None,
        )

    @property
    def records(self) -> List[Dict[str, Any]]:
        """Expose accumulated interaction records."""

        return self._records

    def clear_records(self) -> None:
        self._records.clear()

    async def dispatch_callback(self, data: str) -> None:
        """Send a callback payload through the handler routing."""

        query = FakeCallbackQuery(data=data, user=self.user, records=self._records)
        update = FakeUpdate(user=self.user, callback_query=query)
        await self.handler.handle_callback(update, self.context)

    async def run_queue_booking_flow(
        self,
        *,
        target_date: Optional[date] = None,
        target_time: str = "09:00",
        court_callback: str = "queue_court_all",
    ) -> None:
        """Convenience helper that walks through the queue booking happy path."""

        self.clear_records()
        booking_date = target_date or (date.today() + timedelta(days=3))
        self.context.user_data['current_flow'] = 'queue_booking'
        self.context.user_data['queue_booking_date'] = booking_date

        await self.dispatch_callback(
            f"queue_time_{booking_date.strftime('%Y-%m-%d')}_{target_time}"
        )
        await self.dispatch_callback(court_callback)
        await self.dispatch_callback('queue_confirm')

    def close(self) -> None:
        if self._tempdir is not None:
            self._tempdir.cleanup()


def run_async(coro) -> Any:
    """Run an async coroutine, creating a loop if necessary."""

    try:
        loop = asyncio.get_running_loop()
    except RuntimeError:
        loop = asyncio.new_event_loop()
        try:
            asyncio.set_event_loop(loop)
            return loop.run_until_complete(coro)
        finally:
            asyncio.set_event_loop(None)
            loop.close()
    else:
        return loop.run_until_complete(coro)
