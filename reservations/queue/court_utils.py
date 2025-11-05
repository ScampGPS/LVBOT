"""Court preference helpers shared across queue components."""

from __future__ import annotations
from tracking import t

from typing import Any, Iterable, List, Optional


def normalize_court_sequence(
    courts: Iterable[Any],
    *,
    allowed: Optional[Iterable[int]] = None,
) -> List[int]:
    """Return courts in original order without duplicates."""

    t('reservations.queue.court_utils.normalize_court_sequence')
    allowed_set = {int(c) for c in allowed} if allowed is not None else None
    seen: set[int] = set()
    ordered: List[int] = []

    for value in courts:
        if value is None:
            continue
        try:
            court = int(value)
        except (TypeError, ValueError):
            continue
        if allowed_set is not None and court not in allowed_set:
            continue
        if court in seen:
            continue
        seen.add(court)
        ordered.append(court)
    return ordered
