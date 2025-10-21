#!/usr/bin/env python3
"""
Async telegram bot - entrypoint wrappers around the runtime application.
"""
from tracking import t

import logging
import signal
import sys
from pathlib import Path

if __name__ == "__main__" and __package__ is None:
    sys.path.append(str(Path(__file__).resolve().parents[1]))
    __package__ = "botapp"

# Import logging configuration to initialize proper logging
from infrastructure import logging_config  # noqa: F401

from automation.browser.lifecycle import shutdown_all_browser_processes
from botapp.config import load_bot_config
from botapp.runtime import BotApplication


class CleanBot(BotApplication):
    """Backwards-compatible façade exposing the runtime bot application."""

    def __init__(self, config=None):
        super().__init__(config=config)


def cleanup_browser_processes(force: bool | None = None) -> None:
    """Shut down browser resources gracefully, with optional force kill."""

    t('botapp.app.cleanup_browser_processes')

    logger = logging.getLogger('Main')
    shutdown_all_browser_processes(logger=logger, force=force)


def signal_handler(signum, frame):
    """Handle SIGINT/SIGTERM signals for graceful shutdown."""
    t('botapp.app.signal_handler')
    logger = logging.getLogger('Main')
    logger.info(f"🚨 Received signal {signum}, initiating graceful shutdown...")
    cleanup_browser_processes(force=True)
    exit(0)


def main() -> None:
    """Entry point used by both CLI script and module execution."""
    t('botapp.app.main')

    import atexit

    logger = logging.getLogger('Main')
    logger.info("=" * 50)
    logger.info("Async Telegram Bot - Full AsyncIO Architecture")
    logger.info("=" * 50)

    signal.signal(signal.SIGINT, signal_handler)
    signal.signal(signal.SIGTERM, signal_handler)

    atexit.register(lambda: cleanup_browser_processes(force=True))

    logger.info("🔄 Checking for orphaned browser processes before startup...")
    cleanup_browser_processes(force=True)

    config = load_bot_config()
    bot = CleanBot(config)

    try:
        logger.info("🚀 Starting bot...")
        bot.run()
    except KeyboardInterrupt:
        logger.info("✅ Stopped by user (Ctrl+C)")
    except Exception as exc:
        logger.error("❌ Error: %s", exc, exc_info=True)
    finally:
        logger.info("🔄 Final cleanup...")
        cleanup_browser_processes(force=True)


if __name__ == '__main__':
    main()
