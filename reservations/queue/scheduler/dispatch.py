"""Helpers for dispatching queued booking assignments to executors."""

from __future__ import annotations

import asyncio
import logging
from dataclasses import dataclass
from typing import Any, Awaitable, Callable, Dict, List, Optional, Tuple

from automation.shared.booking_contracts import BookingRequest


@dataclass
class DispatchJob:
    """Encapsulates a single queued booking assignment to execute."""

    reservation_id: str
    assignment: Dict[str, Any]
    reservation: Dict[str, Any]
    index: int
    total: int
    prebuilt_request: Optional[BookingRequest] = None


async def dispatch_to_executors(
    jobs: List[DispatchJob],
    *,
    execute_single: Callable[[
        Dict[str, Any],
        Dict[str, Any],
        int,
        int,
        Optional[BookingRequest],
    ], Awaitable[Dict[str, Any]]],
    logger: Optional[logging.Logger] = None,
    timeout_seconds: float = 60.0,
) -> Tuple[Dict[str, Dict[str, Any]], Dict[str, str]]:
    """Execute queued booking jobs concurrently and return results/timeouts."""

    if not jobs:
        return {}, {}

    task_map: Dict[asyncio.Task[Dict[str, Any]], DispatchJob] = {}

    for job in jobs:
        task = asyncio.create_task(
            execute_single(
                job.assignment,
                job.reservation,
                job.index,
                job.total,
                prebuilt_request=job.prebuilt_request,
            ),
            name=f"booking-{job.reservation_id[:8]}",
        )
        task_map[task] = job

    tasks = list(task_map.keys())
    done, pending = await asyncio.wait(
        tasks,
        return_when=asyncio.ALL_COMPLETED,
        timeout=timeout_seconds,
    )

    timeouts: Dict[str, str] = {}
    if pending:
        if logger:
            logger.warning("Found %s hanging booking tasks - cancelling them", len(pending))
        for task in pending:
            job = task_map[task]
            if logger:
                logger.warning(
                    "Cancelling hanging task for reservation %s...",
                    job.reservation_id[:8],
                )
            task.cancel()
            timeout_message = f"Booking timed out after {timeout_seconds} seconds"
            timeouts[job.reservation_id] = timeout_message

        if pending:
            await asyncio.gather(*pending, return_exceptions=True)

    results: Dict[str, Dict[str, Any]] = {}

    for task in done:
        job = task_map[task]
        try:
            results[job.reservation_id] = task.result()
        except asyncio.CancelledError:
            timeout_message = timeouts.get(job.reservation_id, "Task was cancelled")
            if logger:
                logger.warning(
                    "Task was cancelled for reservation %s...",
                    job.reservation_id[:8],
                )
            results[job.reservation_id] = {
                "success": False,
                "error": timeout_message,
            }
            timeouts.setdefault(job.reservation_id, timeout_message)
        except Exception as exc:  # pragma: no cover - defensive guard
            if logger:
                logger.error(
                    "❌ Booking task raised for %s: %s",
                    job.reservation_id,
                    exc,
                )
            results[job.reservation_id] = {
                "success": False,
                "error": str(exc),
            }

    return results, timeouts
