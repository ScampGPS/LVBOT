"""Support services for the reservation scheduler."""

from __future__ import annotations

from dataclasses import dataclass
from typing import Any, Awaitable, Callable, Dict, Iterable, List, Optional

from automation.shared.booking_contracts import BookingRequest, BookingResult
from botapp.notifications import format_failure_message, format_success_message
from reservations.queue.scheduler.pipeline import (
    HydrationFailure,
    ReservationBatch,
    hydrate_reservation_batch,
)
from reservations.queue.request_builder import ReservationRequestBuilder, DEFAULT_BUILDER
from reservations.queue.scheduler import outcome as outcome_module
from tracking import t


@dataclass
class HydratedReservations:
    """Hydrated reservations paired with their prepared booking requests."""

    reservations: List[Dict[str, Any]]
    prepared_requests: Dict[str, BookingRequest]


class ReservationHydrator:
    """Hydrates reservation batches into executable requests."""

    def __init__(
        self,
        *,
        logger,
        executor_config,
        queue,
        persist_queue_outcome: Callable[[str, BookingResult, Any], None],
        failure_builder: Callable[..., BookingResult],
        on_failure: Callable[[str, str], None],
        builder: ReservationRequestBuilder = DEFAULT_BUILDER,
    ) -> None:
        self._logger = logger
        self._executor_config = executor_config
        self._queue = queue
        self._persist_queue_outcome = persist_queue_outcome
        self._failure_builder = failure_builder
        self._on_failure = on_failure
        self._builder = builder

    def hydrate(self, batch: ReservationBatch) -> HydratedReservations:
        """Return filtered reservations and their prepared booking requests."""

        t('reservations.queue.scheduler.services.ReservationHydrator.hydrate')
        hydrated = hydrate_reservation_batch(
            batch,
            executor_config=self._executor_config,
            logger=self._logger,
            builder=self._builder,
        )

        reservations = self._filter_failures(batch, hydrated.failures)
        prepared_requests = self._map_prepared_requests(reservations, hydrated.requests)
        return HydratedReservations(reservations, prepared_requests)

    def _filter_failures(
        self,
        batch: ReservationBatch,
        failures: Iterable[HydrationFailure],
    ) -> List[Dict[str, Any]]:
        if not failures:
            return list(batch.reservations)

        failed_ids: set[str] = set()
        for failure in failures:
            reservation = failure.reservation
            reservation_id = reservation.get('id')
            if reservation_id is None:
                continue
            str_id = str(reservation_id)
            failed_ids.add(str_id)
            error_message = f"Failed to prepare booking request: {failure.error}"
            result = self._failure_builder(reservation, error_message)
            self._persist_queue_outcome(str_id, result, queue=self._queue)
            self._on_failure(str_id, error_message)

        return [
            reservation
            for reservation in batch.reservations
            if str(reservation.get('id')) not in failed_ids
        ]

    def _map_prepared_requests(
        self,
        reservations: Iterable[Dict[str, Any]],
        requests: Iterable[BookingRequest],
    ) -> Dict[str, BookingRequest]:
        reservation_ids = {
            str(reservation.get('id'))
            for reservation in reservations
            if reservation.get('id') is not None
        }

        return {
            str(request.request_id): request
            for request in requests
            if request.request_id is not None
            and str(request.request_id) in reservation_ids
        }


class SchedulerPipeline:
    """Coordinates scheduler stages (health checks, hydration, execution)."""

    def __init__(
        self,
        *,
        logger,
        hydrator: ReservationHydrator,
        health_check: Callable[[List[Dict[str, Any]]], Awaitable[bool]],
        executor: Callable[..., Awaitable[None]],
    ) -> None:
        self._logger = logger
        self._hydrator = hydrator
        self._health_check = health_check
        self._executor = executor

    async def process(self, evaluation) -> None:
        """Process scheduler evaluation buckets."""

        t('reservations.queue.scheduler.services.SchedulerPipeline.process')
        await self._run_health_checks(evaluation.requires_health_check)
        await self._execute_batches(evaluation.ready_for_execution)

    async def _run_health_checks(self, batches: Iterable[ReservationBatch]) -> None:
        for batch in batches:
            reservations = list(getattr(batch, 'reservations', []) or [])
            if not reservations:
                continue
            await self._health_check(reservations)

    async def _execute_batches(self, batches: Iterable[ReservationBatch]) -> None:
        for batch in batches:
            reservations = getattr(batch, 'reservations', None)
            if not reservations:
                continue
            hydrated = self._hydrator.hydrate(batch)
            if hydrated.reservations:
                await self._executor(
                    hydrated.reservations,
                    prepared_requests=hydrated.prepared_requests,
                )


class OutcomeRecorder:
    """Records booking outcomes and notifies users."""

    def __init__(
        self,
        *,
        scheduler,
        persist_queue_outcome: Callable[[str, BookingResult, Any], None],
        failure_builder: Callable[..., BookingResult],
        result_mapper: Callable[[BookingResult], Dict[str, Any]],
    ) -> None:
        self._scheduler = scheduler
        self._logger = scheduler.logger
        self._queue = scheduler.queue
        self._persist_queue_outcome = persist_queue_outcome
        self._failure_builder = failure_builder
        self._result_mapper = result_mapper

    async def handle_dispatch_results(
        self,
        reservation_lookup: Dict[str, Dict[str, Any]],
        results: Dict[str, Dict[str, Any]],
        timeouts: Dict[str, str],
    ) -> None:
        """Persist outcomes, handle timeouts, and update orchestrator state."""

        t('reservations.queue.scheduler.services.OutcomeRecorder.handle_dispatch_results')
        browser_pool = getattr(self._scheduler, 'browser_pool', None)

        if timeouts and browser_pool and hasattr(browser_pool, 'set_critical_operation'):
            try:
                await browser_pool.set_critical_operation(False)
                self._logger.info(
                    "✅ Critical operation flag forcibly cleared after task cancellation"
                )
            except Exception as cleanup_error:  # pragma: no cover - defensive guard
                self._logger.error(
                    "❌ Failed to clear critical operation flag after cancellation: %s",
                    cleanup_error,
                )

        for reservation_id, timeout_message in timeouts.items():
            reservation_data = reservation_lookup.get(reservation_id, {})
            failure_result = self._failure_builder(
                reservation_data,
                timeout_message,
                errors=[timeout_message],
            )
            self._persist_queue_outcome(reservation_id, failure_result, queue=self._queue)
            results[reservation_id] = self._result_mapper(failure_result)

        for reservation_id, result in results.items():
            outcome_module.record_outcome(self._scheduler, reservation_id, result)

    async def notify(self, results: Dict[str, Any]) -> None:
        """Send user notifications for booking results."""

        t('reservations.queue.scheduler.services.OutcomeRecorder.notify')
        self._logger.info("🔔 Starting notification process for %d result(s)", len(results))

        bot = getattr(self._scheduler, 'bot', None)
        user_db = getattr(self._scheduler, 'user_db', None)

        if not bot:
            self._logger.warning("⚠️  No bot instance available - skipping notifications")
            return
        if not user_db:
            self._logger.warning("⚠️  No user_db instance available - skipping notifications")
            return

        self._logger.info("✓ Bot and user_db available, processing notifications...")

        for reservation_id, result in results.items():
            self._logger.info("📝 Processing notification for reservation %s", reservation_id)

            if result.get('retry_scheduled'):
                self._logger.info(
                    "⏳ Retry in progress for reservation %s - deferring notification",
                    reservation_id,
                )
                continue

            reservation = self._scheduler._get_reservation_by_id(reservation_id)
            booking_result = result.get('booking_result')

            if reservation:
                user_id = self._scheduler._get_reservation_field(reservation, 'user_id')
            elif isinstance(booking_result, BookingResult):
                user_id = booking_result.user.user_id
                self._logger.warning(
                    "⚠️  Reservation %s missing from queue; using booking result metadata",
                    reservation_id,
                )
                reservation = {
                    'target_date': booking_result.metadata.get('target_date'),
                    'target_time': booking_result.metadata.get('target_time'),
                    'court_reserved': booking_result.court_reserved,
                    'user_id': user_id,
                }
            else:
                self._logger.warning(
                    "⚠️  Reservation %s not found and no booking result available",
                    reservation_id,
                )
                continue

            self._logger.info("👤 User ID: %s", user_id)

            user = user_db.get_user(user_id) if user_db else None
            if not user:
                self._logger.warning("⚠️  User %s not found in database", user_id)
                continue

            self._logger.info("📤 Formatting message for user %s...", user_id)
            try:
                message = self._format_message(reservation, result)
                self._logger.debug("📄 Message content (first 200 chars): %s", message[:200] if message else "None")
            except Exception as fmt_exc:
                self._logger.error("❌ Failed to format message for user %s: %s", user_id, fmt_exc, exc_info=True)
                continue

            try:
                self._logger.info("📨 Sending notification to user %s...", user_id)
                await bot.send_notification(user_id, message)
                self._logger.info("✅ Notification sent successfully to user %s", user_id)
            except Exception as exc:  # pragma: no cover - notification safety
                self._logger.error(
                    "❌ Failed to send notification to user %s: %s",
                    user_id,
                    exc,
                    exc_info=True
                )

        self._logger.info("✅ Notification process completed")

    def _format_message(self, reservation: Dict[str, Any], result: Dict[str, Any]) -> str:
        booking_result = result.get('booking_result')
        target_date = self._scheduler._get_reservation_field(reservation, 'target_date')
        target_time = self._scheduler._get_reservation_field(reservation, 'target_time')

        if isinstance(booking_result, BookingResult):
            if booking_result.success:
                return format_success_message(booking_result)
            return format_failure_message(booking_result)

        if result.get('success'):
            court = result.get('court', 'Unknown')
            return (
                "✅ **Reservation Successful!**\n\n"
                f"🎾 Court {court} booked\n"
                f"📅 {target_date}\n"
                f"⏰ {target_time}\n\n"
                "See you on the court!"
            )

        error = result.get('error', 'Unknown error')
        return (
            "❌ **Reservation Failed**\n\n"
            f"📅 {target_date} at {target_time}\n"
            f"Reason: {error}\n\n"
            "Your reservation has been removed from the queue.\n"
            "Please try booking manually or create a new reservation."
        )
