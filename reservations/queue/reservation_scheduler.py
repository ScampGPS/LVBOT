"""
Reservation Scheduler with Dynamic Booking Orchestration
Manages the execution of queued reservations with 3 browsers and staggered refresh
"""

from dataclasses import asdict, dataclass, replace
from functools import partial

from tracking import t

import asyncio
import logging
import os
import threading
import time
from datetime import date, datetime
from typing import Any, Dict, List, Optional, Tuple

import pytz

from automation.executors.booking_orchestrator import DynamicBookingOrchestrator
from automation.executors import AsyncExecutorConfig
from automation.browser.manager import BrowserManager
from automation.browser.health.types import HealthStatus
from botapp.booking.immediate_handler import ImmediateBookingHandler
from automation.shared.booking_contracts import BookingRequest, BookingResult
from botapp.booking.request_builder import booking_user_from_profile
from reservations.queue.scheduler import (
    BrowserLifecycle,
    DispatchJob,
    dispatch_to_executors,
    pull_ready_reservations,
    SchedulerStats,
)
from reservations.queue.scheduler.services import (
    OutcomeRecorder,
    ReservationHydrator,
    SchedulerPipeline,
)
from reservations.queue.request_builder import ReservationRequestBuilder
from reservations.queue.persistence import persist_queue_outcome
from botapp.notifications import format_failure_message, format_success_message
from infrastructure.settings import get_test_mode

# Read production mode setting (opt-in; default is false for richer diagnostics)
PRODUCTION_MODE = os.getenv("PRODUCTION_MODE", "false").lower() == "true"


def _booking_result_to_dict(result: BookingResult) -> Dict[str, Any]:
    """Normalize a `BookingResult` into the legacy dict structure used by the scheduler."""

    error_message = None
    if not result.success:
        error_message = result.message or (
            "; ".join(result.errors) if result.errors else "Unknown error"
        )

    return {
        "success": result.success,
        "court": result.court_reserved,
        "time": result.time_reserved,
        "confirmation_code": result.confirmation_code,
        "confirmation_url": result.confirmation_url,
        "message": result.message,
        "error": error_message,
        "errors": list(result.errors),
        "booking_result": result,
    }


def _failure_result_from_reservation(
    reservation: Dict[str, Any], message: str, *, errors: Optional[List[str]] = None
) -> BookingResult:
    """Build a failure result when execution cannot proceed."""

    fallback_user_id = reservation.get("user_id") or 0
    user_profile = {
        "user_id": fallback_user_id,
        "first_name": reservation.get("first_name") or "Unknown",
        "last_name": reservation.get("last_name") or "",
        "email": reservation.get("email") or f"unknown-{fallback_user_id}@example.com",
        "phone": reservation.get("phone") or "000-000-0000",
        "tier_name": reservation.get("tier"),
    }

    booking_user = booking_user_from_profile(user_profile)

    metadata = {
        "source": "queue_scheduler",
        "target_date": reservation.get("target_date"),
        "target_time": reservation.get("target_time"),
    }

    return BookingResult.failure_result(
        booking_user,
        reservation.get("id"),
        message=message,
        errors=errors or [message],
        metadata=metadata,
    )


@dataclass
class EnrichedReservation:
    """Lightweight structure used for booking plan generation."""

    id: str
    user_id: Any
    courts: List[int]
    time: str
    created_at: Optional[datetime]
    priority: int


class ReservationScheduler:
    """
    Background scheduler that executes reservations at the 48-hour mark
    Uses 3 browsers with staggered refresh rates for optimal booking success
    """

    def __init__(
        self,
        config,
        queue,
        notification_callback,
        bot_handler=None,
        browser_pool=None,
        executor_config: Optional[AsyncExecutorConfig] = None,
        user_manager: Optional[Any] = None,
    ):
        # Support both old and new initialization patterns
        t("reservations.queue.reservation_scheduler.ReservationScheduler.__init__")
        if bot_handler:
            self.bot = bot_handler
            self.config = bot_handler.config
            self.queue = bot_handler.queue
            self.user_db = bot_handler.user_db
            self.notification_callback = bot_handler.send_notification
        else:
            # Old style initialization
            self.bot = None
            self.config = config
            self.queue = queue
            self.user_db = user_manager
            self.notification_callback = notification_callback

        self.logger = logging.getLogger("ReservationScheduler")

        # Thread control
        self.running = False
        self.scheduler_thread = None

        # Dynamic booking orchestrator
        self.orchestrator = DynamicBookingOrchestrator()
        self.executor_config = executor_config or AsyncExecutorConfig()

        # Browser manager coordinates pool lifecycle and helpers
        self.browser_manager = BrowserManager(pool=browser_pool)
        self.browser_lifecycle = BrowserLifecycle(
            logger=self.logger,
            browser_manager=self.browser_manager,
            config=self.config,
            production_mode=PRODUCTION_MODE,
            browser_pool=browser_pool,
        )

        # Immediate booking handler reused for queued executions
        self.immediate_booking_handler: Optional[ImmediateBookingHandler] = None
        if self.user_db is not None:
            try:
                self.immediate_booking_handler = ImmediateBookingHandler(
                    self.user_db,
                    browser_pool=self.browser_pool,
                )
            except Exception as exc:  # pragma: no cover - defensive guard
                self.logger.error(
                    f"Failed to initialize ImmediateBookingHandler: {exc}"
                )

        # Performance tracking
        self.stats = SchedulerStats()

        executor_config_dict = (
            asdict(self.executor_config) if self.executor_config else None
        )
        self.request_builder = ReservationRequestBuilder()
        self.hydrator = ReservationHydrator(
            logger=self.logger,
            executor_config=executor_config_dict,
            queue=self.queue,
            persist_queue_outcome=persist_queue_outcome,
            failure_builder=_failure_result_from_reservation,
            on_failure=self._update_reservation_failed,
            builder=self.request_builder,
        )
        self.pipeline = SchedulerPipeline(
            logger=self.logger,
            hydrator=self.hydrator,
            health_check=self._perform_pre_execution_health_check,
            executor=self._execute_reservation_group,
        )
        self.outcome_recorder = OutcomeRecorder(
            scheduler=self,
            persist_queue_outcome=persist_queue_outcome,
            failure_builder=_failure_result_from_reservation,
            result_mapper=_booking_result_to_dict,
        )

    @property
    def browser_pool(self):
        return self.browser_lifecycle.browser_pool

    @browser_pool.setter
    def browser_pool(self, pool):
        self.browser_lifecycle.browser_pool = pool

    @property
    def health_checker(self):
        return self.browser_lifecycle.health_checker

    @health_checker.setter
    def health_checker(self, checker):
        self.browser_lifecycle.health_checker = checker

    @property
    def recovery_service(self):
        return self.browser_lifecycle.recovery_service

    @recovery_service.setter
    def recovery_service(self, service):
        self.browser_lifecycle.recovery_service = service

    @staticmethod
    def _get_reservation_field(
        reservation: Dict[str, Any], field: str, default: Any = None
    ) -> Any:
        """
        Safe getter for reservation dictionary fields

        Provides consistent access to reservation data following DRY principles.
        This centralizes dictionary access patterns used throughout the class.

        Args:
            reservation: Reservation dictionary
            field: Field name to retrieve
            default: Default value if field doesn't exist

        Returns:
            Field value or default
        """
        t(
            "reservations.queue.reservation_scheduler.ReservationScheduler._get_reservation_field"
        )
        return reservation.get(field, default)

    @staticmethod
    def _parse_datetime_field(
        reservation: Dict[str, Any], field: str, as_date: bool = False
    ) -> Any:
        """
        Parse a datetime field from reservation with proper type checking

        Args:
            reservation: Reservation dictionary
            field: Field name to parse
            as_date: If True, return date object instead of datetime

        Returns:
            Parsed datetime/date or current datetime/date as fallback
        """
        t(
            "reservations.queue.reservation_scheduler.ReservationScheduler._parse_datetime_field"
        )
        value = ReservationScheduler._get_reservation_field(reservation, field)

        if isinstance(value, str):
            try:
                parsed = datetime.fromisoformat(value)
                return parsed.date() if as_date else parsed
            except ValueError:
                pass
        elif isinstance(value, datetime):
            return value.date() if as_date else value
        elif isinstance(value, date) and as_date:
            return value

        # Fallback to current time
        current = datetime.now()
        return current.date() if as_date else current

    async def run_async(self):
        """Run the scheduler in the current event loop (new method)"""
        t("reservations.queue.reservation_scheduler.ReservationScheduler.run_async")
        self.logger.info("Starting reservation scheduler in main event loop")
        self.running = True

        # Only initialize browser pool if not provided from main thread
        if not self.browser_pool:
            self.logger.info("=" * 60)
            self.logger.info("STARTUP: Initializing browser pool")
            self.logger.info("=" * 60)
            await self.browser_lifecycle.ensure_browser_pool()
        else:
            self.browser_lifecycle.ensure_services(
                log_prefix="Using pre-initialized browser pool from main thread"
            )

        self.logger.info("Reservation scheduler started with browser pool ready")

        # Check for existing reservations and attempt to book ready ones
        await self._check_startup_reservations()

        # Run the scheduler loop directly in the current event loop
        await self._scheduler_loop()

    async def start(self):
        """Start the reservation scheduler (legacy method - creates separate thread)"""
        t("reservations.queue.reservation_scheduler.ReservationScheduler.start")
        self.logger.info("Starting reservation scheduler")
        self.running = True

        # Only initialize browser pool if not provided from main thread
        if not self.browser_pool:
            self.logger.info("=" * 60)
            self.logger.info("STARTUP: Initializing browser pool")
            self.logger.info("=" * 60)
            await self.browser_lifecycle.ensure_browser_pool()
        else:
            self.browser_lifecycle.ensure_services(
                log_prefix="Using pre-initialized browser pool from main thread"
            )

        self.scheduler_thread = threading.Thread(
            target=lambda: asyncio.run(
                self._scheduler_loop()
            ),  # Run async loop in thread
            daemon=True,
            name="ReservationScheduler",
        )
        self.scheduler_thread.start()

        self.logger.info("Reservation scheduler started with browser pool ready")

        # Check for existing reservations and attempt to book ready ones
        await self._check_startup_reservations()

    async def stop(self):
        """Stop the scheduler"""
        t("reservations.queue.reservation_scheduler.ReservationScheduler.stop")
        self.logger.info("Stopping reservation scheduler")
        self.running = False

        # Note: Browser pool is managed by main app, don't stop it here
        # to avoid interfering with other components

        # Only try to join thread if using legacy start() method
        if hasattr(self, "scheduler_thread") and self.scheduler_thread:
            self.scheduler_thread.join(timeout=5)

        self.logger.info("Reservation scheduler stopped")

    async def _scheduler_loop(self):
        """Main scheduler loop that checks for reservations to execute"""
        t(
            "reservations.queue.reservation_scheduler.ReservationScheduler._scheduler_loop"
        )
        poll_interval = self._poll_interval_seconds()
        while self.running:
            try:
                now = datetime.now(pytz.timezone(self.config.timezone))
                evaluation = self._evaluate_queue(now)
                await self.pipeline.process(evaluation)
                await asyncio.sleep(poll_interval)
            except Exception as exc:  # pragma: no cover - defensive guard
                self.logger.error("Scheduler error: %s", exc)
                await asyncio.sleep(max(poll_interval * 2, 30))

    def _poll_interval_seconds(self) -> float:
        """Return the interval between scheduler iterations."""

        t(
            "reservations.queue.reservation_scheduler.ReservationScheduler._poll_interval_seconds"
        )
        return 15.0

    def _evaluate_queue(self, now: datetime):
        """Evaluate pending reservations and bucket them for execution."""

        t(
            "reservations.queue.reservation_scheduler.ReservationScheduler._evaluate_queue"
        )
        return pull_ready_reservations(
            self.queue,
            now=now,
            logger=self.logger,
        )

    async def _execute_reservation_group(
        self,
        reservations: List[Any],
        *,
        prepared_requests: Optional[Dict[str, BookingRequest]] = None,
    ):
        """
        Execute a group of reservations for the same time slot
        Uses persistent browser pool with dynamic court assignment
        """
        t(
            "reservations.queue.reservation_scheduler.ReservationScheduler._execute_reservation_group"
        )
        if not reservations:
            return
        if not await self._refresh_browser_pool():
            return

        target_date, time_slot = self._extract_time_slot(reservations)
        self.logger.info(
            """🎯 EXECUTING RESERVATION GROUP
        Time slot: %s %s
        Number of reservations: %s
        Reservation IDs: %s
        """,
            target_date.isoformat(),
            time_slot,
            len(reservations),
            [r.get("id", "unknown")[:8] + "..." for r in reservations],
        )

        enriched_reservations = self._enrich_reservations(reservations)
        booking_plan = self.orchestrator.create_booking_plan(
            enriched_reservations,
            time_slot,
            self.user_db,
        )

        self.logger.info(
            """BOOKING PLAN CREATED
        Confirmed (will book): %s
        Waitlisted: %s
        Browser assignments: %s
        """,
            len(booking_plan["confirmed_users"]),
            len(booking_plan["waitlisted_users"]),
            len(booking_plan.get("browser_assignments", [])),
        )

        await self._execute_booking_plan(
            booking_plan,
            target_date,
            reservations,
            prepared_requests=prepared_requests,
        )

        if booking_plan["waitlisted_users"]:
            await self._handle_waitlisted_users(
                booking_plan["waitlisted_users"],
                target_date.isoformat(),
                time_slot,
            )

    async def _refresh_browser_pool(self) -> bool:
        """Ensure the browser pool is available and refreshed before booking."""

        t(
            "reservations.queue.reservation_scheduler.ReservationScheduler._refresh_browser_pool"
        )

        await self.browser_lifecycle.ensure_browser_pool()
        if not self.browser_pool:
            self.logger.error("Browser pool not available")
            return False

        try:
            self.logger.info(
                "🔄 PRE-BOOKING REFRESH: Refreshing browser pages to prevent staleness"
            )
            refresh_start_time = time.time()

            if hasattr(self.browser_pool, "refresh_browser_pages"):
                refresh_results = await self.browser_pool.refresh_browser_pages()
                refresh_duration = time.time() - refresh_start_time
                successful_refreshes = sum(
                    1 for success in refresh_results.values() if success
                )
                total_browsers = len(refresh_results)

                self.logger.info(
                    "🔄 PRE-BOOKING REFRESH COMPLETE: %s/%s browsers refreshed in %.2fs",
                    successful_refreshes,
                    total_browsers,
                    refresh_duration,
                )

                if successful_refreshes == 0 and total_browsers > 0:
                    self.logger.error(
                        "⚠️ WARNING: All browser refreshes failed - browsers may be stale!"
                    )
                elif successful_refreshes < total_browsers * 0.5:
                    self.logger.warning(
                        "⚠️ WARNING: Only %s/%s browsers refreshed successfully",
                        successful_refreshes,
                        total_browsers,
                    )
            else:
                self.logger.warning(
                    "⚠️ Browser pool doesn't support page refresh - using stale browsers"
                )

        except Exception as exc:  # pragma: no cover - defensive guard
            self.logger.error(
                "❌ PRE-BOOKING REFRESH FAILED: %s - proceeding with potentially stale browsers",
                exc,
            )

        return True

    def _extract_time_slot(
        self, reservations: List[Dict[str, Any]]
    ) -> Tuple[date, str]:
        """Extract the target date and time slot from the reservation batch."""

        t(
            "reservations.queue.reservation_scheduler.ReservationScheduler._extract_time_slot"
        )

        first_reservation = reservations[0]
        time_slot = str(self._get_reservation_field(first_reservation, "target_time"))
        raw_date = self._get_reservation_field(first_reservation, "target_date")

        if isinstance(raw_date, date):
            target_date = raw_date
        elif isinstance(raw_date, str):
            try:
                target_date = datetime.fromisoformat(raw_date).date()
            except ValueError:
                self.logger.warning(
                    "Invalid target_date format %s, using current date as fallback",
                    raw_date,
                )
                target_date = datetime.now().date()
        else:
            self.logger.warning(
                "Invalid target_date type %s, using current date as fallback",
                type(raw_date),
            )
            target_date = datetime.now().date()

        return target_date, time_slot

    def _enrich_reservations(
        self, reservations: List[Dict[str, Any]]
    ) -> List[EnrichedReservation]:
        """Prepare reservation data for booking plan generation."""

        t(
            "reservations.queue.reservation_scheduler.ReservationScheduler._enrich_reservations"
        )

        enriched: List[EnrichedReservation] = []
        for reservation in reservations:
            user_id = self._get_reservation_field(reservation, "user_id")
            priority = self._get_reservation_field(reservation, "priority", None)

            if priority is None and self.user_db is not None:
                if hasattr(self.user_db, "is_admin") and self.user_db.is_admin(user_id):
                    priority = 0
                elif hasattr(self.user_db, "is_vip") and self.user_db.is_vip(user_id):
                    priority = 1
                else:
                    priority = 2
            elif priority is None:
                priority = 2

            enriched.append(
                EnrichedReservation(
                    id=str(self._get_reservation_field(reservation, "id")),
                    user_id=user_id,
                    courts=list(
                        self._get_reservation_field(
                            reservation, "court_preferences", []
                        )
                    ),
                    time=str(self._get_reservation_field(reservation, "target_time")),
                    created_at=self._parse_datetime_field(reservation, "created_at"),
                    priority=int(priority),
                )
            )

        return enriched

    async def _execute_booking_plan(
        self,
        booking_plan: Dict[str, Any],
        target_date: date,
        reservations: List[Dict[str, Any]],
        *,
        prepared_requests: Optional[Dict[str, BookingRequest]] = None,
    ) -> None:
        """Execute the booking plan and handle results/notifications."""

        t(
            "reservations.queue.reservation_scheduler.ReservationScheduler._execute_booking_plan"
        )
        await self._execute_with_persistent_pool(
            booking_plan,
            target_date,
            reservations,
            prepared_requests=prepared_requests,
        )

    async def _execute_with_persistent_pool(
        self,
        booking_plan: Dict[str, Any],
        target_date: date,
        reservations: List[Dict[str, Any]],
        *,
        prepared_requests: Optional[Dict[str, BookingRequest]] = None,
    ):
        """
        Execute bookings using persistent browser pool with smart court assignment
        """
        t(
            "reservations.queue.reservation_scheduler.ReservationScheduler._execute_with_persistent_pool"
        )
        prepared_requests = prepared_requests or {}
        jobs, reservation_lookup, initial_results = self._build_dispatch_jobs(
            booking_plan.get("browser_assignments", []),
            reservations,
            prepared_requests,
        )

        results = dict(initial_results)
        if jobs:
            execute_single = partial(
                self._execute_single_booking, target_date=target_date
            )
            dispatch_results, timeouts = await dispatch_to_executors(
                jobs,
                execute_single=execute_single,
                logger=self.logger,
            )
            results.update(dispatch_results)
            await self.outcome_recorder.handle_dispatch_results(
                reservation_lookup,
                results,
                timeouts,
            )

        overflow_count = booking_plan.get("overflow_count", 0)
        if overflow_count > 0:
            self.logger.info("Processing %s overflow reservations", overflow_count)

        self.logger.info(
            "Booking execution complete: %s", self.orchestrator.get_booking_summary()
        )
        self.logger.info("📊 Results dictionary before notification: %s", results)
        await self.outcome_recorder.notify(results)

    def _build_dispatch_jobs(
        self,
        assignments: List[Dict[str, Any]],
        reservations: List[Dict[str, Any]],
        prepared_requests: Dict[str, BookingRequest],
    ) -> Tuple[List[DispatchJob], Dict[str, Dict[str, Any]], Dict[str, Dict[str, Any]]]:
        """Build dispatch jobs and supporting lookups for booking execution."""

        t(
            "reservations.queue.reservation_scheduler.ReservationScheduler._build_dispatch_jobs"
        )

        reservation_lookup = {
            str(self._get_reservation_field(reservation, "id")): reservation
            for reservation in reservations
        }

        results: Dict[str, Dict[str, Any]] = {}
        jobs: List[DispatchJob] = []
        total_assignments = len(assignments)

        for index, assignment in enumerate(assignments, start=1):
            attempt = assignment.get("attempt")
            if not attempt:
                continue

            reservation_id = str(getattr(attempt, "reservation_id", None))
            reservation = reservation_lookup.get(reservation_id)

            if not reservation:
                self.logger.error(
                    "❌ Reservation %s not found in lookup", reservation_id[:8]
                )
                results[reservation_id] = {
                    "success": False,
                    "error": "Reservation not found",
                }
                continue

            jobs.append(
                DispatchJob(
                    reservation_id=reservation_id,
                    assignment=assignment,
                    reservation=reservation,
                    index=index,
                    total=total_assignments,
                    prebuilt_request=prepared_requests.get(reservation_id),
                )
            )

        return jobs, reservation_lookup, results

    async def _execute_single_booking(
        self,
        assignment: Dict,
        reservation: Dict,
        index: int,
        total: int,
        *,
        target_date: date,
        prebuilt_request: Optional[BookingRequest] = None,
    ) -> Dict:
        """Execute a single queued booking using the unified booking contracts."""

        t(
            "reservations.queue.reservation_scheduler.ReservationScheduler._execute_single_booking"
        )
        import time

        execution_start = time.time()
        attempt = assignment["attempt"]
        reservation_id = attempt.reservation_id

        self.logger.info(
            """🔄 PROCESSING QUEUED BOOKING {index}/{total}
        Reservation ID: {reservation_id_short}...
        Assigned browser: {browser_id}
        Target court: {target_court}
        """.format(
                index=index,
                total=total,
                reservation_id_short=reservation_id[:8],
                browser_id=assignment.get("browser_id", "Unknown"),
                target_court=attempt.target_court,
            )
        )

        if not self.immediate_booking_handler:
            self.logger.error(
                "Immediate booking handler not initialized; cannot execute queued booking"
            )
            failure = _failure_result_from_reservation(
                reservation, "Booking handler unavailable"
            )
            persist_queue_outcome(reservation_id, failure, queue=self.queue)
            return _booking_result_to_dict(failure)

        user_id = self._get_reservation_field(reservation, "user_id")
        self.logger.info(f"👤 User: {user_id}")

        user_profile = self.user_db.get_user(user_id) if self.user_db else None
        if not user_profile:
            self.logger.error(
                f"❌ User {user_id} not found for reservation {reservation_id[:8]}..."
            )
            failure = _failure_result_from_reservation(reservation, "User not found")
            persist_queue_outcome(reservation_id, failure, queue=self.queue)
            return _booking_result_to_dict(failure)

        attempt_number = getattr(attempt, "attempt_number", None)
        if attempt_number is None:
            attempt_number = getattr(attempt, "attempt", None)

        base_metadata = {
            "queue_reservation_id": reservation_id,
            "queue_attempt": attempt_number,
            "assigned_browser": assignment.get("browser_id"),
        }

        try:
            if prebuilt_request is not None:
                booking_request = replace(
                    prebuilt_request,
                    metadata={**prebuilt_request.metadata, **base_metadata},
                )
            else:
                booking_request = self.request_builder.from_dict(
                    reservation,
                    user_profile=user_profile,
                    metadata=base_metadata,
                )
        except ValueError as exc:
            self.logger.error(
                "Failed to build booking request for reservation %s: %s",
                reservation_id[:8],
                exc,
            )
            failure = _failure_result_from_reservation(reservation, str(exc))
            persist_queue_outcome(reservation_id, failure, queue=self.queue)
            return _booking_result_to_dict(failure)

        try:
            if hasattr(self.immediate_booking_handler, "execute_queue_booking"):
                booking_result = (
                    await self.immediate_booking_handler.execute_queue_booking(
                        booking_request
                    )
                )
            else:  # Backwards compatibility with older handlers/tests
                booking_result = await self.immediate_booking_handler._execute_booking(
                    booking_request
                )
        except Exception as exc:  # pragma: no cover - defensive guard
            self.logger.error(
                "❌ Immediate booking execution error for %s: %s",
                reservation_id,
                exc,
            )
            booking_result = BookingResult.failure_result(
                booking_request.user,
                booking_request.request_id,
                message=str(exc),
                errors=[str(exc)],
                metadata={
                    **booking_request.metadata,
                    "flow": "queue_execution_exception",
                },
            )

        execution_time = time.time() - execution_start
        booking_result = booking_result.merge_metadata(
            {
                "queue_execution_time_seconds": execution_time,
                "queue_attempt": attempt_number,
                "assigned_browser": assignment.get("browser_id"),
                "target_date": booking_request.target_date.isoformat(),
                "target_time": booking_request.target_time,
            }
        )

        persist_queue_outcome(reservation_id, booking_result, queue=self.queue)

        if booking_result.success:
            self.logger.info(
                """✅ QUEUE BOOKING SUCCESSFUL
                Reservation ID: {reservation_id}
                Court booked: {court}
                Confirmation: {confirmation}
                Execution time: {elapsed:.2f}s (Immediate flow)
                """.format(
                    reservation_id=reservation_id[:8],
                    court=booking_result.court_reserved or "Unknown",
                    confirmation=booking_result.confirmation_code or "Pending",
                    elapsed=execution_time,
                )
            )
        else:
            self.logger.warning(
                """❌ QUEUE BOOKING FAILED
                Reservation ID: {reservation_id}
                Error: {error}
                Execution time: {elapsed:.2f}s (Immediate flow)
                """.format(
                    reservation_id=reservation_id[:8],
                    error=booking_result.message
                    or "; ".join(booking_result.errors)
                    or "Unknown error",
                    elapsed=execution_time,
                )
            )

        return _booking_result_to_dict(booking_result)

    def _update_reservation_success(self, reservation_id: str, result: Dict):
        """Update reservation status to completed"""
        t(
            "reservations.queue.reservation_scheduler.ReservationScheduler._update_reservation_success"
        )
        self.queue.update_reservation_status(reservation_id, "completed")
        execution_time = None
        booking_result = (
            result.get("booking_result") if isinstance(result, dict) else None
        )
        if isinstance(booking_result, BookingResult):
            execution_time = booking_result.metadata.get("queue_execution_time_seconds")
        elif isinstance(result, dict):
            execution_time = result.get("queue_execution_time_seconds")

        self.stats.record_success(execution_time)
        self.logger.info(f"Reservation {reservation_id} completed successfully")

    def _update_reservation_failed(self, reservation_id: str, error: str):
        """Update reservation status to failed and remove from queue"""
        t(
            "reservations.queue.reservation_scheduler.ReservationScheduler._update_reservation_failed"
        )
        # Get reservation details for logging
        reservation = self._get_reservation_by_id(reservation_id)
        if reservation:
            user_id = self._get_reservation_field(reservation, "user_id")
            target_date = self._get_reservation_field(reservation, "target_date")
            target_time = self._get_reservation_field(reservation, "target_time")

            self.logger.info(
                f"""MARKING RESERVATION AS FAILED
            Reservation ID: {reservation_id[:8]}...
            User ID: {user_id}
            Date/Time: {target_date} {target_time}
            Error: {error}
            """
            )

        # Update status to failed
        self.queue.update_reservation_status(reservation_id, "failed", error=error)
        self.stats.record_failure()

        config = get_test_mode()
        if config.enabled and config.retain_failed_reservations:
            self.logger.info(
                "🧪 TEST MODE: Keeping failed reservation %s... in queue for retry",
                reservation_id[:8],
            )
            return

        removed = self.queue.remove_reservation(reservation_id)

        if removed:
            self.logger.info(
                "✅ Failed reservation %s... successfully removed from queue",
                reservation_id[:8],
            )
        else:
            self.logger.warning(
                "⚠️ Could not remove failed reservation %s... from queue (may have been already removed)",
                reservation_id[:8],
            )

    async def _notify_booking_results(self, results: Dict[str, Any]):
        """Send notifications to users about booking results"""
        t(
            "reservations.queue.reservation_scheduler.ReservationScheduler._notify_booking_results"
        )
        self.logger.info(
            f"📢 _notify_booking_results called with {len(results)} results"
        )
        for reservation_id, result in results.items():
            self.logger.info(
                f"Processing notification for reservation {reservation_id[:8]}...: {result}"
            )
            reservation = self._get_reservation_by_id(reservation_id)
            if not reservation:
                continue

            user_id = self._get_reservation_field(reservation, "user_id")
            user = self.user_db.get_user(user_id)
            if not user:
                continue

            # Format notification message
            target_date = self._get_reservation_field(reservation, "target_date")
            time = self._get_reservation_field(reservation, "target_time")

            booking_result = (
                result.get("booking_result") if isinstance(result, dict) else None
            )

            if isinstance(booking_result, BookingResult):
                if booking_result.success:
                    message = format_success_message(booking_result)
                else:
                    message = format_failure_message(booking_result)
            else:
                if result.get("success"):
                    court = result.get("court", "Unknown")
                    message = (
                        f"✅ **Reservation Successful!**\n\n"
                        f"🎾 Court {court} booked\n"
                        f"📅 {target_date}\n"
                        f"⏰ {time}\n\n"
                        f"See you on the court!"
                    )
                else:
                    error = result.get("error", "Unknown error")
                    message = (
                        f"❌ **Reservation Failed**\n\n"
                        f"📅 {target_date} at {time}\n"
                        f"Reason: {error}\n\n"
                        f"Your reservation has been removed from the queue.\n"
                        f"Please try booking manually or create a new reservation."
                    )

            # Send notification (async)
            self.logger.info(f"📨 Sending notification to user {user_id}")
            self.logger.info(f"Message preview: {message[:100]}...")
            try:
                await self.bot.send_notification(user_id, message)
                self.logger.info(f"✅ Notification sent successfully to user {user_id}")
            except Exception as e:
                self.logger.error(
                    f"❌ Failed to send notification to user {user_id}: {e}"
                )

    def _get_reservation_by_id(self, reservation_id: str):
        """Get reservation by ID from queue (checks all reservations including completed)"""
        t(
            "reservations.queue.reservation_scheduler.ReservationScheduler._get_reservation_by_id"
        )
        # Use the queue's get_reservation method which searches all reservations
        reservation = self.queue.get_reservation(reservation_id)
        if reservation:
            self.logger.info(
                f"Found reservation {reservation_id[:8]}... (status: {reservation.get('status')})"
            )
        else:
            self.logger.warning(f"Reservation {reservation_id[:8]}... not found")
        return reservation

    async def _handle_waitlisted_users(
        self, waitlisted_users, target_date: str, target_time: str
    ):
        """Handle users who were waitlisted due to capacity"""
        t(
            "reservations.queue.reservation_scheduler.ReservationScheduler._handle_waitlisted_users"
        )
        self.logger.info(
            f"Processing {len(waitlisted_users)} waitlisted users for {target_date} {target_time}"
        )

        # Update reservation status to waitlisted
        for i, user in enumerate(waitlisted_users):
            position = i + 1
            self.queue.add_to_waitlist(user.reservation_id, position)

            # Send waitlist notification
            message = (
                f"📋 **Added to Waitlist**\n\n"
                f"You are #{position} on the waitlist for:\n"
                f"📅 {target_date}\n"
                f"⏰ {target_time}\n\n"
                f"You'll be notified if a spot opens up!"
            )
            await self.bot.send_notification(user.user_id, message)

    async def handle_cancellation(self, reservation_id: str):
        """
        Handle reservation cancellation and promote from waitlist if applicable

        Args:
            reservation_id: ID of cancelled reservation
        """
        t(
            "reservations.queue.reservation_scheduler.ReservationScheduler.handle_cancellation"
        )
        self.logger.info(f"HANDLING CANCELLATION for reservation {reservation_id}")

        # Get the cancelled reservation
        reservation = self.queue.get_reservation(reservation_id)
        if not reservation:
            self.logger.warning(
                f"Reservation {reservation_id} not found for cancellation"
            )
            return

        target_date = reservation.get("target_date")
        target_time = reservation.get("time") or reservation.get("target_time")
        user_id = reservation.get("user_id")

        self.logger.info(
            f"""CANCELLATION DETAILS
        User ID: {user_id}
        Date: {target_date}
        Time: {target_time}
        Status: {reservation.get('status')}
        """
        )

        # Update status to cancelled
        self.queue.update_reservation_status(reservation_id, "cancelled")

        # Check if there's a waitlist for this slot
        waitlist = self.queue.get_waitlist_for_slot(target_date, target_time)

        if waitlist:
            self.logger.info(f"Found {len(waitlist)} users on waitlist for this slot")

            # Promote first person from waitlist
            promoted = waitlist[0]
            promoted_id = promoted.get("id")

            # Update their status to confirmed
            self.queue.update_reservation_status(promoted_id, "confirmed")

            # Notify promoted user
            promoted_user_id = promoted.get("user_id")
            promoted_name = promoted.get("first_name", "Unknown")

            self.logger.info(
                f"""WAITLIST PROMOTION
            Promoted User ID: {promoted_user_id}
            Promoted User Name: {promoted_name}
            Original Waitlist Position: 1
            New Status: confirmed
            """
            )

            message = (
                f"🎉 **Promoted from Waitlist!**\n\n"
                f"Good news! A spot opened up for:\n"
                f"📅 {target_date}\n"
                f"⏰ {target_time}\n\n"
                f"Your reservation is now confirmed!"
            )
            await self.bot.send_notification(promoted_user_id, message)

            # Update positions for remaining waitlist
            self.logger.info(
                f"Updating positions for {len(waitlist) - 1} remaining waitlisted users"
            )

            for i, res in enumerate(waitlist[1:]):
                new_position = i + 1
                self.queue.update_reservation_status(
                    res["id"], "waitlisted", waitlist_position=new_position
                )
                self.logger.debug(
                    f"  User {res.get('user_id')}: Position {res.get('waitlist_position', 'unknown')} → {new_position}"
                )

            self.logger.info(
                f"PROMOTION COMPLETE: User {promoted_user_id} promoted from waitlist"
            )
        else:
            self.logger.info(
                "No users on waitlist for this slot - cancellation complete"
            )

    async def force_browser_refresh(self) -> Dict[str, bool]:
        """
        Force immediate refresh of all browser pages.

        This is a manual trigger for browser refresh that can be called
        when browsers are suspected to be stale or unresponsive.

        Returns:
            Dict[str, bool]: browser_id -> success status
        """
        t(
            "reservations.queue.reservation_scheduler.ReservationScheduler.force_browser_refresh"
        )
        self.logger.info("🔄 MANUAL BROWSER REFRESH: Force refresh requested")

        if not self.browser_pool:
            self.logger.error("Cannot refresh: Browser pool not initialized")
            return {}

        try:
            if hasattr(self.browser_pool, "refresh_browser_pages"):
                results = await self.browser_pool.refresh_browser_pages()

                successful = sum(1 for success in results.values() if success)
                total = len(results)

                self.logger.info(
                    f"🔄 MANUAL BROWSER REFRESH COMPLETE: {successful}/{total} browsers refreshed successfully"
                )
                return results
            else:
                self.logger.warning("Browser pool doesn't support page refresh")
                return {}

        except Exception as e:
            self.logger.error(f"Manual browser refresh failed: {e}")
            return {}

    def get_performance_report(self) -> str:
        """Get scheduler performance statistics"""
        t(
            "reservations.queue.reservation_scheduler.ReservationScheduler.get_performance_report"
        )
        sections = [self.stats.format_report()]

        if self.recovery_service:
            recovery_stats = self.recovery_service.get_recovery_stats()
            if recovery_stats["total_recovery_attempts"] > 0:
                sections.append(
                    f"\n🔧 **Recovery Statistics**\n"
                    f"Total Recoveries: {recovery_stats['total_recovery_attempts']}\n"
                    f"Successful: {recovery_stats['successful_recoveries']}\n"
                    f"Success Rate: {recovery_stats['success_rate']*100:.1f}%\n"
                )
                if recovery_stats["emergency_browser_active"]:
                    sections.append("⚠️ Emergency browser is active")

        if self.browser_pool and hasattr(self.browser_pool, "get_stats"):
            try:
                pool_stats = self.browser_pool.get_stats()
                sections.append(
                    f"\n🌐 **Browser Pool Status**\n"
                    f"Active Browsers: {pool_stats.get('browser_count', 0)}\n"
                    f"Max Browsers: {pool_stats.get('max_browsers', 0)}\n"
                    f"Browsers Recycled: {pool_stats.get('browsers_recycled', 0)}\n"
                )

                browser_details = pool_stats.get("browser_details", {})
                if browser_details:
                    healthy_browsers = sum(
                        1
                        for details in browser_details.values()
                        if details.get("healthy", False)
                    )
                    sections.append(
                        f"Healthy Browsers: {healthy_browsers}/{len(browser_details)}"
                    )

                    avg_age = sum(
                        details.get("age_minutes", 0)
                        for details in browser_details.values()
                    ) / len(browser_details)
                    sections.append(f"Avg Browser Age: {avg_age:.1f} minutes")

                    old_browsers = [
                        bid
                        for bid, details in browser_details.items()
                        if details.get("age_minutes", 0) > 60
                    ]

                    if old_browsers:
                        sections.append("\n⚠️ **Staleness Warning**")
                        sections.append(
                            f"{len(old_browsers)} browser(s) older than 1 hour - may need refresh"
                        )
            except Exception as exc:  # pragma: no cover - best effort stats
                self.logger.debug(f"Could not get browser pool stats: {exc}")

        return "\n".join([section for section in sections if section])

    async def _check_startup_reservations(self):
        """Check for existing reservations at startup and attempt to book ready ones"""
        t(
            "reservations.queue.reservation_scheduler.ReservationScheduler._check_startup_reservations"
        )
        self.logger.info("🔍 Checking for existing reservations at startup...")

        config = get_test_mode()

        if config.enabled:
            # Get all reservations regardless of status
            all_reservations = self.queue.queue  # Direct access to all reservations
            self.logger.info(
                "🧪 TEST MODE: Checking all reservations including failed ones"
            )
        else:
            # Production mode: only check pending/scheduled reservations
            all_reservations = self.queue.get_pending_reservations()

        if not all_reservations:
            self.logger.info("No existing reservations found")
            return

        self.logger.info(f"Found {len(all_reservations)} existing reservations")

        # Check which ones are ready for execution
        ready_count = 0
        failed_count = 0
        for reservation in all_reservations:
            reservation_id = reservation.get("id", "Unknown")
            target_date = reservation.get("target_date", "Unknown")
            target_time = reservation.get("target_time", "Unknown")
            status = reservation.get("status", "Unknown")

            if (
                config.enabled
                and config.retain_failed_reservations
                and status == "failed"
            ):
                failed_count += 1
                self.logger.info(
                    f"🔄 TEST MODE: Resetting failed reservation {reservation_id[:8]}... to scheduled status"
                )
                self.queue.update_reservation_status(reservation_id, "scheduled")
                status = "scheduled"  # Update local status for processing

            # Parse scheduled execution time
            execution_time_str = reservation.get("scheduled_execution_time")
            if execution_time_str:
                try:
                    from datetime import datetime
                    import pytz

                    # Parse the execution time
                    if "+" in execution_time_str or "Z" in execution_time_str:
                        # ISO format with timezone
                        execution_time = datetime.fromisoformat(
                            execution_time_str.replace("Z", "+00:00")
                        )
                    else:
                        # Assume it's already a datetime string, add Mexico timezone
                        execution_time = datetime.fromisoformat(execution_time_str)
                        mexico_tz = pytz.timezone("America/Mexico_City")
                        execution_time = mexico_tz.localize(execution_time)

                    # Check if it's ready for execution
                    current_time = datetime.now(pytz.timezone("America/Mexico_City"))
                    if execution_time <= current_time:
                        ready_count += 1
                        self.logger.info(
                            f"🎯 Reservation {reservation_id[:8]}... ({target_date} {target_time}) is ready for execution"
                        )
                    else:
                        time_until = execution_time - current_time
                        self.logger.info(
                            f"⏳ Reservation {reservation_id[:8]}... ({target_date} {target_time}) scheduled in {time_until}"
                        )

                except Exception as e:
                    self.logger.warning(
                        f"Could not parse execution time for reservation {reservation_id[:8]}...: {e}"
                    )
            else:
                self.logger.info(
                    f"📋 Reservation {reservation_id[:8]}... ({target_date} {target_time}) - Status: {status}"
                )

        # Summary
        if config.enabled and config.retain_failed_reservations and failed_count > 0:
            self.logger.info(
                f"🔄 TEST MODE: Reset {failed_count} failed reservations to scheduled status"
            )

        if ready_count > 0:
            self.logger.info(
                f"🚀 Found {ready_count} reservations ready for immediate execution"
            )
            # The scheduler loop will pick these up automatically
        else:
            self.logger.info("✓ All reservations are scheduled for future execution")

    async def _perform_pre_execution_health_check(
        self, reservations: List[Dict[str, Any]]
    ) -> bool:
        """
        Perform health check before executing reservations

        Args:
            reservations: List of reservations about to be executed

        Returns:
            True if system is healthy or recovery successful, False otherwise
        """
        t(
            "reservations.queue.reservation_scheduler.ReservationScheduler._perform_pre_execution_health_check"
        )
        if not self.health_checker:
            self.logger.warning(
                "Health checker not initialized - skipping health check"
            )
            return True

        try:
            self.stats.record_health_check()

            # Perform comprehensive health check
            health_result = await self.health_checker.perform_pre_booking_health_check()

            self.logger.info(
                f"""🏥 HEALTH CHECK RESULT
            Status: {health_result.status.value}
            Message: {health_result.message}
            Details: {health_result.details}
            """
            )

            # If healthy, proceed
            if health_result.is_healthy():
                self.logger.info("✓ Browser pool is healthy - proceeding with bookings")
                return True

            # If degraded but functional, log warning but proceed
            if health_result.status == HealthStatus.DEGRADED:
                self.logger.warning(
                    "⚠️ Browser pool is degraded but functional - proceeding with caution"
                )

                # Notify users of potential issues
                for reservation in reservations:
                    user_id = self._get_reservation_field(reservation, "user_id")
                    await self._send_health_warning(user_id, health_result)

                return True

            # If critical or failed, attempt recovery
            if health_result.status in [HealthStatus.CRITICAL, HealthStatus.FAILED]:
                self.logger.error(
                    f"🚑 Browser pool health is {health_result.status.value} - attempting recovery"
                )

                # Identify failed courts from health check details
                failed_courts = []
                if health_result.details and "courts" in health_result.details:
                    for court_str, status in health_result.details["courts"].items():
                        if status in ["critical", "failed", "error"]:
                            court_num = int(court_str.replace("court_", ""))
                            failed_courts.append(court_num)

                # Attempt recovery
                if self.recovery_service:
                    self.stats.record_recovery_attempt()
                    recovery_result = await self.recovery_service.recover_browser_pool(
                        failed_courts=failed_courts if failed_courts else None,
                        error_context=health_result.message,
                    )

                    self.logger.info(
                        f"""🔧 RECOVERY RESULT
                    Success: {recovery_result.success}
                    Strategy: {recovery_result.strategy_used.value}
                    Message: {recovery_result.message}
                    Courts recovered: {recovery_result.courts_recovered}
                    Courts failed: {recovery_result.courts_failed}
                    Duration: {recovery_result.total_duration_seconds:.1f}s
                    """
                    )

                    if recovery_result.success:
                        # Notify users of recovery
                        for reservation in reservations:
                            user_id = self._get_reservation_field(
                                reservation, "user_id"
                            )
                            await self._send_recovery_notification(
                                user_id, recovery_result
                            )

                        # Check if we're using emergency browser
                        if recovery_result.strategy_used.value == "emergency_fallback":
                            self.logger.warning(
                                "🚑 Using emergency browser - limited functionality"
                            )
                            # Update court preferences to use emergency browser (court 99)
                            for reservation in reservations:
                                reservation["court_preferences"] = [99]

                        return True
                    else:
                        # Recovery failed - notify users
                        for reservation in reservations:
                            user_id = self._get_reservation_field(
                                reservation, "user_id"
                            )
                            target_date = self._get_reservation_field(
                                reservation, "target_date"
                            )
                            target_time = self._get_reservation_field(
                                reservation, "target_time"
                            )

                            message = (
                                f"❌ **Booking System Issue**\n\n"
                                f"Unable to process your reservation for:\n"
                                f"📅 {target_date}\n"
                                f"⏰ {target_time}\n\n"
                                f"The booking system is experiencing technical difficulties. "
                                f"Your reservation remains in the queue and we'll retry when the system recovers.\n\n"
                                f"You may want to try booking manually as a backup."
                            )
                            await self.bot.send_notification(user_id, message)

                        return False
                else:
                    self.logger.error(
                        "Recovery service not available - cannot attempt recovery"
                    )
                    return False

            return True

        except Exception as e:
            self.logger.error(f"Error during pre-execution health check: {e}")
            # On error, proceed with caution
            return True

    async def _send_health_warning(self, user_id: str, health_result):
        """
        Send health warning to user
        """
        t(
            "reservations.queue.reservation_scheduler.ReservationScheduler._send_health_warning"
        )
        try:
            message = (
                "⚠️ **System Notice**\n\n"
                "The booking system is experiencing minor issues:\n"
                f"{health_result.message}\n\n"
                "We'll still attempt your booking but success rates may be reduced."
            )
            await self.bot.send_notification(user_id, message)
        except Exception as e:
            self.logger.error(f"Failed to send health warning to user {user_id}: {e}")

    async def _send_recovery_notification(self, user_id: str, recovery_result):
        """
        Send recovery notification to user
        """
        t(
            "reservations.queue.reservation_scheduler.ReservationScheduler._send_recovery_notification"
        )
        try:
            if recovery_result.strategy_used.value == "emergency_fallback":
                message = (
                    "🚑 **Using Backup System**\n\n"
                    "The main booking system had issues but we've activated a backup system. "
                    "Your booking will proceed with limited functionality."
                )
            elif recovery_result.courts_failed:
                message = (
                    "🔧 **System Partially Recovered**\n\n"
                    f"We've recovered {len(recovery_result.courts_recovered)} out of "
                    f"{len(recovery_result.courts_recovered) + len(recovery_result.courts_failed)} courts. "
                    f"Your booking will proceed with available courts."
                )
            else:
                message = (
                    "✅ **System Recovered**\n\n"
                    "The booking system has been successfully recovered. "
                    "Your booking will proceed normally."
                )

            await self.bot.send_notification(user_id, message)
        except Exception as e:
            self.logger.error(
                f"Failed to send recovery notification to user {user_id}: {e}"
            )
