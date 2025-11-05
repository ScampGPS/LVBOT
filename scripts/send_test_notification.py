#!/usr/bin/env python3
"""Manual smoke test for Telegram notifications."""

from __future__ import annotations

import asyncio
import logging
import sys

from botapp.runtime.bot_application import BotApplication
from botapp.notifications import deliver_notification_with_menu

logging.basicConfig(level=logging.INFO)
LOGGER = logging.getLogger("NotificationTest")


async def main(user_id: int) -> None:
    app = BotApplication()
    message = (
        "✅ **Test Notification**\n\n"
        "This is a manual smoke test for Telegram delivery.\n"
        "If you received this, bot notifications are working. 🎯"
    )

    await deliver_notification_with_menu(
        application=app.application,
        user_manager=app.user_manager,
        user_id=user_id,
        message=message,
        logger=LOGGER,
        follow_up_delay_seconds=0,
    )


if __name__ == "__main__":
    if len(sys.argv) != 2:
        print("Usage: python scripts/send_test_notification.py <telegram_user_id>")
        raise SystemExit(1)

    asyncio.run(main(int(sys.argv[1])))
