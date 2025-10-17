"""Reservation service bootstrap helpers."""

from __future__ import annotations
from tracking import t

from typing import Any, Callable, Tuple

from reservations.services import ReservationService


NotificationCallback = Callable[[int, str], Any]


def build_reservation_components(
    config,
    notification_callback: NotificationCallback,
    user_manager,
    browser_pool,
) -> Tuple[ReservationService, Any, Any]:
    """Create the reservation service along with queue and scheduler handles."""

    t('botapp.bootstrap.reservation_setup.build_reservation_components')

    service = ReservationService(
        config=config,
        notification_callback=notification_callback,
        user_manager=user_manager,
        browser_pool=browser_pool,
    )

    return service, service.queue, service.scheduler


__all__ = ['build_reservation_components']
