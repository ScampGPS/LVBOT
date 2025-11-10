"""Reusable polling helper for court availability."""

from __future__ import annotations
from tracking import t

import copy
from dataclasses import dataclass, field
from datetime import datetime
import logging
from typing import Any, Awaitable, Callable, Dict, List, Mapping, Optional


AvailabilityData = Dict[int, Any]


@dataclass
class AvailabilityChange:
    """Represents differences between two availability snapshots."""

    added: Dict[str, List[str]] = field(default_factory=dict)
    removed: Dict[str, List[str]] = field(default_factory=dict)
    error: Optional[str] = None

    def has_changes(self) -> bool:
        t('monitoring.availability_poller.AvailabilityChange.has_changes')
        return bool(self.added or self.removed or self.error)


@dataclass
class PollSnapshot:
    """Container for poll results and detected changes."""

    timestamp: datetime
    results: AvailabilityData
    previous: AvailabilityData
    changes: Dict[int, AvailabilityChange]


class AvailabilityPoller:
    """Polls availability using a supplied coroutine and detects changes."""

    def __init__(
        self,
        fetcher: Callable[[], Awaitable[AvailabilityData]],
        *,
        logger,
    ) -> None:
        t('monitoring.availability_poller.AvailabilityPoller.__init__')
        self._fetcher = fetcher
        self._logger = logger or logging.getLogger('AvailabilityPoller')
        self._previous: AvailabilityData = {}

    @property
    def previous(self) -> AvailabilityData:
        t('monitoring.availability_poller.AvailabilityPoller.previous')
        return copy.deepcopy(self._previous)

    async def poll(self) -> PollSnapshot:
        t('monitoring.availability_poller.AvailabilityPoller.poll')
        raw_results = await self._fetcher()
        is_initial = not self._previous
        normalised_results = self._normalise_snapshot(raw_results)
        previous_normalised = self._normalise_snapshot(self._previous)

        changes: Dict[int, AvailabilityChange] = {}
        if is_initial:
            for court_number, data in normalised_results.items():
                if isinstance(data, dict) and "error" in data:
                    changes[court_number] = AvailabilityChange(error=str(data['error']))
        else:
            for court_number in set(previous_normalised.keys()) | set(normalised_results.keys()):
                change = self._detect_change(
                    previous_normalised.get(court_number),
                    normalised_results.get(court_number),
                )
                if change is not None:
                    changes[court_number] = change

        snapshot = PollSnapshot(
            timestamp=datetime.now(),
            results=copy.deepcopy(normalised_results),
            previous=copy.deepcopy(previous_normalised),
            changes=changes,
        )

        self._previous = normalised_results
        return snapshot

    # ------------------------------------------------------------------
    # Internal helpers
    # ------------------------------------------------------------------
    def _normalise_snapshot(self, snapshot: AvailabilityData) -> AvailabilityData:
        t('monitoring.availability_poller.AvailabilityPoller._normalise_snapshot')
        if not snapshot:
            return {}

        normalised: AvailabilityData = {}
        for court_number, data in snapshot.items():
            normalised[court_number] = self._normalise_court_data(data)
        return normalised

    def _normalise_court_data(self, data: Any) -> Any:
        t('monitoring.availability_poller.AvailabilityPoller._normalise_court_data')
        if not isinstance(data, dict) or "error" in data:
            return data

        normalised = {}
        for date_str, times in data.items():
            normalised[date_str] = sorted(set(times))
        return normalised

    def _detect_change(self, old: Any, new: Any) -> Optional[AvailabilityChange]:
        t('monitoring.availability_poller.AvailabilityPoller._detect_change')
        change = AvailabilityChange()

        if new is None:
            if old is None:
                return None
            if isinstance(old, dict) and "error" in old:
                change.error = "Availability fetch failed previously"
            elif isinstance(old, dict):
                for date_str, times in old.items():
                    change.removed[date_str] = list(times)
            return change if change.has_changes() else None

        if isinstance(new, dict) and "error" in new:
            change.error = str(new.get("error"))
            return change

        if old is None:
            if isinstance(new, dict):
                for date_str, times in new.items():
                    change.added[date_str] = list(times)
            return change if change.has_changes() else None

        if isinstance(old, dict) and "error" in old and isinstance(new, dict) and "error" not in new:
            change.error = "Recovered from error"

        if isinstance(old, dict) and isinstance(new, dict):
            dates = set(old.keys()) | set(new.keys())
            for date_str in dates:
                old_times = set(old.get(date_str, []))
                new_times = set(new.get(date_str, []))
                added = sorted(new_times - old_times)
                removed = sorted(old_times - new_times)
                if added:
                    change.added[date_str] = added
                if removed:
                    change.removed[date_str] = removed

        return change if change.has_changes() else None
