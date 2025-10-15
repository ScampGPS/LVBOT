"""Utility entrypoints for LVBot.

Provides quick CLI hooks into reservation services for manual inspection.
"""

from __future__ import annotations

import argparse
from lvbot.users.manager import UserManager
from lvbot.reservations.services import ReservationService


def _build_service() -> ReservationService:
    user_manager = UserManager()
    service = ReservationService(
        config=None,
        notification_callback=lambda user_id, message: print(f"Notify {user_id}: {message}"),
        user_manager=user_manager,
        browser_pool=None,
    )
    return service


def list_queue() -> None:
    service = _build_service()
    requests = service.list_requests()
    if not requests:
        print("Queue is empty.")
        return
    for request in requests:
        print(
            f"{request.request_id or 'pending'}: {request.user.user_id} -> "
            f"{request.target_date} {request.target_time}"
        )


def main() -> None:
    parser = argparse.ArgumentParser(description="LVBot utility helpers")
    parser.add_argument("command", choices=["list-queue"], help="Command to execute")
    args = parser.parse_args()

    if args.command == "list-queue":
        list_queue()


if __name__ == "__main__":
    main()
