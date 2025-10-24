"""Shared helpers for live availability lookups in queue/test mode flows."""

from __future__ import annotations

import logging
from datetime import date, datetime
from typing import Any, Dict, List, Optional

from telegram.ext import ContextTypes


CACHE_KEY = 'queue_live_time_cache'


async def fetch_live_time_slots(
    deps: Any,
    context: ContextTypes.DEFAULT_TYPE,
    selected_date: date,
    tz,
    now: datetime,
    logger: logging.Logger,
    *,
    cache_key: str = CACHE_KEY,
    log_prefix: str = "Queue",
) -> Optional[List[str]]:
    """Return live slots for ``selected_date`` or ``None`` when unavailable.

    The result is cached in ``context.user_data[cache_key]`` to reuse lookups
    during the same interaction. When no slots are found the cached value is an
    empty list so callers can distinguish "no availability" from "not yet
    fetched".
    """

    checker = getattr(deps, 'availability_checker', None)
    if checker is None:
        logger.warning(
            "%s live availability requested but availability checker is unavailable",
            log_prefix,
        )
        return None

    cache_value = context.user_data.setdefault(cache_key, {})
    if not isinstance(cache_value, dict):
        cache_value = {}
        context.user_data[cache_key] = cache_value

    date_key = selected_date.isoformat()
    if date_key in cache_value:
        slots = cache_value[date_key]
        logger.info(
            "%s live availability cache hit for %s: %s slots",
            log_prefix,
            date_key,
            len(slots),
        )
        return slots

    matrix = await _fetch_live_matrix(checker, selected_date, now, logger, log_prefix)
    if matrix is None:
        return None

    daily_availability = matrix.get(date_key, {})
    if not daily_availability:
        logger.info(
            "%s live availability found no slots for %s (matrix keys: %s)",
            log_prefix,
            date_key,
            list(matrix.keys()),
        )
        cache_value[date_key] = []
        return []

    unique_times: set[str] = set()
    for times in daily_availability.values():
        unique_times.update(times)

    filtered_times: List[str] = []
    for time_str in sorted(unique_times):
        try:
            hour, minute = map(int, time_str.split(':'))
        except ValueError:
            continue

        slot_dt = datetime.combine(
            selected_date,
            datetime.min.time().replace(hour=hour, minute=minute),
        )
        slot_dt = tz.localize(slot_dt)
        if slot_dt >= now:
            filtered_times.append(time_str)

    cache_value[date_key] = filtered_times
    logger.info(
        "%s live availability resolved %s slots for %s",
        log_prefix,
        len(filtered_times),
        selected_date,
    )
    return filtered_times


async def _fetch_live_matrix(
    checker: Any,
    selected_date: date,
    now: datetime,
    logger: logging.Logger,
    log_prefix: str,
) -> Optional[Dict[str, Dict[int, List[str]]]]:
    try:
        availability_results = await checker.check_availability(current_time=now)
    except Exception as exc:  # pragma: no cover - defensive guard
        logger.error(
            "%s live availability failed for %s: %s",
            log_prefix,
            selected_date,
            exc,
        )
        return None

    matrix: Dict[str, Dict[int, List[str]]] = {}
    for court_num, court_data in availability_results.items():
        if isinstance(court_data, dict) and "error" in court_data:
            logger.warning(
                "%s live availability ignored Court %s due to error: %s",
                log_prefix,
                court_num,
                court_data["error"],
            )
            continue

        for date_key, times in court_data.items():
            if not times:
                continue
            matrix.setdefault(date_key, {})[court_num] = sorted(times)

    logger.info(
        "%s live availability matrix fetched for %s: %s dates, courts=%s",
        log_prefix,
        selected_date,
        len(matrix),
        {k: list(v.keys()) for k, v in matrix.items()},
    )
    return matrix
