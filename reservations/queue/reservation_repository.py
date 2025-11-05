"""Persistence helpers for reservation queue storage."""

from __future__ import annotations

import json
from pathlib import Path
from typing import Any, Iterable, List

from tracking import t


class ReservationRepository:
    """Read/write reservation data to a JSON backing file."""

    def __init__(self, file_path: str, *, logger: Any) -> None:
        t('reservations.queue.reservation_repository.ReservationRepository.__init__')
        self._path = Path(file_path)
        self._logger = logger

    def load(self) -> List[dict]:
        """Load reservations from disk, returning an empty list on failure."""

        t('reservations.queue.reservation_repository.ReservationRepository.load')
        try:
            if self._path.exists():
                with self._path.open('r', encoding='utf-8') as handle:
                    payload = json.load(handle)
                if isinstance(payload, list):
                    self._logger.debug(
                        "Loaded %s reservations from %s",
                        len(payload),
                        self._path,
                    )
                    return payload
                self._logger.warning(
                    "Invalid queue format in %s; expected list, received %s",
                    self._path,
                    type(payload).__name__,
                )
            else:
                self._logger.debug(
                    "Queue file %s does not exist; starting empty",
                    self._path,
                )
        except Exception as exc:  # pragma: no cover - defensive guard
            self._logger.error("Failed to load queue from %s: %s", self._path, exc)
        return []

    def save(self, reservations: Iterable[dict]) -> None:
        """Persist reservations to disk, ensuring parent directories exist."""

        t('reservations.queue.reservation_repository.ReservationRepository.save')
        try:
            self._path.parent.mkdir(parents=True, exist_ok=True)
            with self._path.open('w', encoding='utf-8') as handle:
                json.dump(list(reservations), handle, indent=2, ensure_ascii=False)
            self._logger.debug(
                "Queue saved to %s", self._path,
            )
        except Exception as exc:  # pragma: no cover - defensive guard
            self._logger.error("Failed to save queue to %s: %s", self._path, exc)
