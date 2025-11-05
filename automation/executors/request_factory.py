"""Factories bridging executor inputs with shared booking contracts."""

from __future__ import annotations
from tracking import t

from datetime import date, datetime
from typing import Any, Dict, Optional, Sequence

from automation.executors.core import ExecutionResult
from automation.shared.booking_contracts import (
    BookingRequest,
    BookingResult,
    BookingSource,
    BookingStatus,
    BookingUser,
    compose_booking_metadata,
)


class ExecutorRequestFactory:
    """Factory helpers for creating executor booking requests and results."""

    REQUIRED_FIELDS = {"first_name", "last_name", "email", "phone"}

    @classmethod
    def build_executor_request(
        cls,
        *,
        source: BookingSource,
        user_info: Dict[str, Any],
        target_date: date,
        time_slot: str,
        courts: Sequence[int],
        request_id: Optional[str] = None,
        metadata: Optional[Dict[str, Any]] = None,
        executor_config: Optional[Dict[str, Any]] = None,
    ) -> BookingRequest:
        """Create a request for executor-driven flows (working/experienced/smart)."""

        t(
            "automation.executors.request_factory.ExecutorRequestFactory.build_executor_request"
        )
        if not courts:
            raise ValueError("Executor booking requires at least one court")

        user = cls._normalise_user(user_info)

        base_metadata = compose_booking_metadata(
            source,
            target_date,
            time_slot,
        )
        if metadata:
            base_metadata.update(metadata)

        return BookingRequest.from_reservation_record(
            request_id=request_id,
            user=user,
            target_date=target_date,
            target_time=time_slot,
            courts=list(courts),
            source=source,
            metadata=base_metadata,
            executor_config=executor_config,
        )

    @classmethod
    def build_retry_request(
        cls,
        *,
        original_request: BookingRequest,
        attempt: int,
        metadata: Optional[Dict[str, Any]] = None,
        executor_config: Optional[Dict[str, Any]] = None,
    ) -> BookingRequest:
        """Clone an existing request for retry workflows with incremented metadata."""

        t(
            "automation.executors.request_factory.ExecutorRequestFactory.build_retry_request"
        )
        base_metadata = {
            **original_request.metadata,
            "source": BookingSource.RETRY.value,
            "retry_attempt": attempt,
        }
        if metadata:
            base_metadata.update(metadata)

        return BookingRequest.from_reservation_record(
            request_id=original_request.request_id,
            user=original_request.user,
            target_date=original_request.target_date,
            target_time=original_request.target_time,
            courts=original_request.court_preference.as_list(),
            source=BookingSource.RETRY,
            metadata=base_metadata,
            executor_config=executor_config or original_request.executor_config,
        )

    @classmethod
    def build_booking_result(
        cls,
        request: BookingRequest,
        execution: ExecutionResult,
        *,
        metadata: Optional[Dict[str, Any]] = None,
        started_at: Optional[datetime] = None,
        completed_at: Optional[datetime] = None,
    ) -> BookingResult:
        """Translate an `ExecutionResult` into the shared `BookingResult` contract."""

        t(
            "automation.executors.request_factory.ExecutorRequestFactory.build_booking_result"
        )
        status = BookingStatus.SUCCESS if execution.success else BookingStatus.FAILURE

        base_metadata: Dict[str, Any] = dict(request.metadata)
        if execution.details:
            base_metadata.setdefault("execution_details", execution.details)
        if execution.available_times:
            base_metadata["available_times"] = execution.available_times
        if execution.available_times_with_dates:
            base_metadata["available_times_with_dates"] = (
                execution.available_times_with_dates
            )
        if execution.court_attempted is not None:
            base_metadata["court_attempted"] = execution.court_attempted
        if execution.execution_time_seconds is not None:
            base_metadata["execution_time_seconds"] = execution.execution_time_seconds
        if execution.google_calendar_link:
            base_metadata["google_calendar_link"] = execution.google_calendar_link
        if execution.cancel_modify_link:
            base_metadata["cancel_modify_link"] = execution.cancel_modify_link
        if execution.ics_calendar_link:
            base_metadata["ics_calendar_link"] = execution.ics_calendar_link
        if metadata:
            base_metadata.update(metadata)

        if execution.success:
            message = execution.message or base_metadata.get("execution_message")
            errors: tuple[str, ...] = ()
        else:
            candidate_errors: list[str] = []
            if execution.error_message:
                candidate_errors.append(str(execution.error_message))
            if execution.details and isinstance(execution.details, dict):
                detail_errors = execution.details.get("errors")
                if isinstance(detail_errors, (list, tuple)):
                    candidate_errors.extend(str(err) for err in detail_errors)
            message = (
                execution.error_message or execution.message or "Booking attempt failed"
            )
            errors = tuple(candidate_errors) if candidate_errors else (message,)

        confirmation_code = execution.confirmation_id
        if confirmation_code is None and execution.details:
            confirmation_code = execution.details.get("confirmation_id")

        return BookingResult(
            status=status,
            user=request.user,
            request_id=request.request_id,
            court_reserved=execution.court_reserved or execution.court_number,
            time_reserved=execution.time_reserved or request.target_time,
            confirmation_code=confirmation_code,
            confirmation_url=execution.confirmation_url,
            message=message,
            errors=errors if status == BookingStatus.FAILURE else tuple(),
            started_at=started_at,
            completed_at=completed_at,
            metadata=base_metadata,
        )

    @classmethod
    def _normalise_user(cls, user_info: Dict[str, Any]) -> BookingUser:
        missing = [field for field in cls.REQUIRED_FIELDS if not user_info.get(field)]
        if missing:
            raise ValueError(f"Executor user info missing fields: {', '.join(missing)}")

        user_id = user_info.get("user_id")
        if user_id is None:
            raise ValueError("Executor user info must include 'user_id'")

        return BookingUser(
            user_id=int(user_id),
            first_name=str(user_info["first_name"]).strip(),
            last_name=str(user_info["last_name"]).strip(),
            email=str(user_info["email"]).strip(),
            phone=str(user_info["phone"]).strip(),
            tier=user_info.get("tier") or user_info.get("tier_name"),
        )


def build_executor_request(**kwargs):
    t('automation.executors.request_factory.build_executor_request')
    return ExecutorRequestFactory.build_executor_request(**kwargs)


def build_retry_request(**kwargs):
    t('automation.executors.request_factory.build_retry_request')
    return ExecutorRequestFactory.build_retry_request(**kwargs)


def build_booking_result_from_execution(
    t('automation.executors.request_factory.build_booking_result_from_execution')
    request: BookingRequest,
    execution: ExecutionResult,
    *,
    metadata: Optional[Dict[str, Any]] = None,
    started_at: Optional[datetime] = None,
    completed_at: Optional[datetime] = None,
):
    return ExecutorRequestFactory.build_booking_result(
        request,
        execution,
        metadata=metadata,
        started_at=started_at,
        completed_at=completed_at,
    )


__all__ = [
    "ExecutorRequestFactory",
    "build_executor_request",
    "build_retry_request",
    "build_booking_result_from_execution",
]
