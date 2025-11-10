"""Helpers for orchestrating queued reservation execution pipelines."""

from __future__ import annotations

from dataclasses import dataclass, field
from datetime import date, datetime
from typing import Any, Dict, List, Optional

from tracking import t

from automation.shared.booking_contracts import BookingRequest
from reservations.queue.request_builder import (
    DEFAULT_BUILDER,
    ReservationRequestBuilder,
)


@dataclass
class ReservationBatch:
    """A collection of reservations targeting the same time slot."""

    time_key: str
    target_date: str
    target_time: str
    reservations: List[Dict[str, Any]]


@dataclass
class PipelineEvaluation:
    """Buckets produced after evaluating pending reservations."""

    ready_for_execution: List[ReservationBatch] = field(default_factory=list)
    requires_health_check: List[ReservationBatch] = field(default_factory=list)
    evaluated: List[Dict[str, Any]] = field(default_factory=list)


@dataclass
class HydratedBatch:
    """A batch of reservations with their constructed booking requests."""

    batch: ReservationBatch
    requests: List[BookingRequest] = field(default_factory=list)
    failures: List["HydrationFailure"] = field(default_factory=list)


@dataclass
class HydrationFailure:
    """Represents a reservation that failed to hydrate into a booking request."""

    reservation: Dict[str, Any]
    error: Exception


def pull_ready_reservations(
    queue_service: Any,
    *,
    now: datetime,
    logger: Optional[Any] = None,
) -> PipelineEvaluation:
    """Group pending reservations by execution readiness and time slot."""

    t("reservations.queue.scheduler.pipeline.pull_ready_reservations")

    pending: List[Dict[str, Any]] = queue_service.get_pending_reservations()
    evaluation = PipelineEvaluation(evaluated=pending)

    if logger and pending:
        logger.info(
            "SCHEDULER CHECK\nCurrent time: %s\nPending reservations: %s\n",
            now,
            len(pending),
        )

    execution_groups: Dict[str, List[Dict[str, Any]]] = {}
    health_check_groups: Dict[str, List[Dict[str, Any]]] = {}

    for reservation in pending:
        status = reservation.get("status")
        if status not in {"pending", "scheduled", "attempting"}:
            continue

        exec_time = _coerce_scheduled_datetime(reservation.get("scheduled_execution"))
        if exec_time is None:
            if logger:
                logger.warning(
                    "Invalid scheduled_execution for reservation %s", _reservation_id_prefix(reservation)
                )
            continue

        comparison_now = now
        try:
            time_until = exec_time - comparison_now
        except TypeError:
            if exec_time.tzinfo is None and comparison_now.tzinfo is not None:
                comparison_now = comparison_now.replace(tzinfo=None)
            elif exec_time.tzinfo is not None and comparison_now.tzinfo is None:
                comparison_now = comparison_now.replace(tzinfo=exec_time.tzinfo)
            else:
                if logger:
                    logger.warning(
                        "Skipping reservation %s due to incompatible datetime formats",
                        _reservation_id_prefix(reservation),
                    )
                continue

            try:
                time_until = exec_time - comparison_now
            except TypeError:
                if logger:
                    logger.warning(
                        "Skipping reservation %s due to datetime arithmetic error",
                        _reservation_id_prefix(reservation),
                    )
                continue
        hours_until = time_until.total_seconds() / 3600

        if logger:
            logger.info(
                "RESERVATION STATUS CHECK\n"
                "ID: %s\n"
                "Target: %s %s\n"
                "Scheduled execution: %s\n"
                "Time until execution: %.1f hours\n"
                "Status: %s\n",
                _reservation_id_prefix(reservation),
                _stringified_date(reservation.get("target_date")),
                reservation.get("target_time"),
                exec_time,
                hours_until,
                "READY TO EXECUTE" if exec_time <= now else "WAITING",
            )

        target_date = _stringified_date(reservation.get("target_date"))
        target_time = str(reservation.get("target_time"))
        key = f"{target_date}_{target_time}"

        if exec_time <= now:
            if logger:
                logger.info(
                    "✅ ENTERING 48H WINDOW - Reservation %s is ready for execution!",
                    _reservation_id_prefix(reservation),
                )
            execution_groups.setdefault(key, []).append(reservation)
        elif hours_until <= 0.1:
            if logger:
                logger.info(
                    "🎯 PRE-EXECUTION HEALTH CHECK - Reservation %s will execute in %.1f minutes",
                    _reservation_id_prefix(reservation),
                    hours_until * 60,
                )
            health_check_groups.setdefault(key, []).append(reservation)

    evaluation.ready_for_execution = _build_batches(execution_groups)
    evaluation.requires_health_check = _build_batches(health_check_groups)
    return evaluation


def hydrate_reservation_batch(
    batch: ReservationBatch,
    *,
    executor_config: Optional[Dict[str, Any]] = None,
    logger: Optional[Any] = None,
    builder: Optional[ReservationRequestBuilder] = None,
) -> HydratedBatch:
    """Convert reservations in a batch into booking requests."""

    t("reservations.queue.scheduler.pipeline.hydrate_reservation_batch")

    builder = builder or DEFAULT_BUILDER
    requests: List[BookingRequest] = []
    failures: List[HydrationFailure] = []

    for reservation in batch.reservations:
        try:
            request = builder.from_dict(
                reservation,
                executor_config=executor_config,
            )
            requests.append(request)
        except Exception as exc:  # pragma: no cover - defensive logging
            failures.append(HydrationFailure(reservation=reservation, error=exc))
            if logger:
                logger.error(
                    "Failed to build booking request for reservation %s: %s",
                    _reservation_id_prefix(reservation),
                    exc,
                )

    return HydratedBatch(batch=batch, requests=requests, failures=failures)


def _build_batches(groups: Dict[str, List[Dict[str, Any]]]) -> List[ReservationBatch]:
    t('reservations.queue.scheduler.pipeline._build_batches')
    batches: List[ReservationBatch] = []
    for key, reservations in groups.items():
        if not reservations:
            continue
        target_date = _stringified_date(reservations[0].get("target_date"))
        target_time = str(reservations[0].get("target_time"))
        batches.append(
            ReservationBatch(
                time_key=key,
                target_date=target_date,
                target_time=target_time,
                reservations=reservations,
            )
        )
    return batches


def _reservation_id_prefix(reservation: Dict[str, Any]) -> str:
    t('reservations.queue.scheduler.pipeline._reservation_id_prefix')
    identifier = str(reservation.get("id", "unknown"))
    return f"{identifier[:8]}..." if identifier else "unknown"


def _stringified_date(value: Any) -> str:
    t('reservations.queue.scheduler.pipeline._stringified_date')
    if isinstance(value, date):
        return value.isoformat()
    if isinstance(value, datetime):
        return value.date().isoformat()
    return str(value)


def _coerce_scheduled_datetime(value: Any) -> Optional[datetime]:
    t('reservations.queue.scheduler.pipeline._coerce_scheduled_datetime')
    if isinstance(value, datetime):
        return value
    if isinstance(value, str):
        try:
            return datetime.fromisoformat(value)
        except ValueError:
            return None
    return None
