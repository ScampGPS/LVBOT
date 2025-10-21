"""Lifecycle orchestration for the Telegram bot runtime."""

from __future__ import annotations
from tracking import t

import asyncio
import logging
from typing import Optional

from botapp.bootstrap import BotDependencies


class LifecycleManager:
    """Manage startup, shutdown, and periodic tasks for the bot runtime."""

    def __init__(
        self,
        dependencies: BotDependencies,
        *,
        logger: Optional[logging.Logger] = None,
    ) -> None:
        t('botapp.runtime.lifecycle.LifecycleManager.__init__')
        self.dependencies = dependencies
        self.logger = logger or logging.getLogger('LifecycleManager')
        self.application = None
        self.scheduler_task: Optional[asyncio.Task] = None
        self.metrics_task: Optional[asyncio.Task] = None

    async def post_init(self, application) -> None:
        """Initialize async resources once the Telegram application is ready."""

        t('botapp.runtime.lifecycle.LifecycleManager.post_init')
        self.application = application

        try:
            await self.dependencies.browser_manager.start_pool(self.logger)
        except Exception as exc:  # pragma: no cover - defensive guard
            self.logger.error(
                "CRITICAL: Browser pool failed to start - bot functionality limited: %s",
                exc,
            )

        scheduler = self.dependencies.scheduler
        self.scheduler_task = asyncio.create_task(scheduler.run_async())
        self.logger.info("Reservation scheduler task created in main event loop")

        self.metrics_task = asyncio.create_task(self._metrics_loop())
        self.logger.info("Metrics monitoring started (5-minute intervals)")

        await self.log_metrics()

        self.logger.info("Bot started successfully - awaiting messages...")
        self.logger.info("Browser pool should be initialized")

    async def post_stop(self, application) -> None:
        """Tear down background tasks and browser resources."""

        t('botapp.runtime.lifecycle.LifecycleManager.post_stop')
        self.logger.info("🔴 Starting bot shutdown sequence...")

        if self.metrics_task:
            self.metrics_task.cancel()
            try:
                await self.metrics_task
            except asyncio.CancelledError:
                pass
            self.logger.info("✅ Metrics monitoring stopped")
            self.metrics_task = None

        if self.scheduler_task:
            self.logger.info("🔄 Stopping reservation scheduler...")
            scheduler = self.dependencies.scheduler
            scheduler.running = False
            self.scheduler_task.cancel()
            try:
                await self.scheduler_task
            except asyncio.CancelledError:
                pass
            await scheduler.stop()
            self.logger.info("✅ Reservation scheduler stopped")
            self.scheduler_task = None

        self.logger.info("🔄 Stopping browser pool...")
        try:
            success = await self.dependencies.browser_manager.stop_pool(self.logger)
            if success:
                self.logger.info("✅ Browser pool cleanup completed")
            else:
                self.logger.warning("⚠️ Browser pool cleanup completed with errors")
        except Exception as exc:  # pragma: no cover - defensive guard
            self.logger.error("❌ Error during browser pool cleanup: %s", exc)

        self.logger.info("✅ Bot shutdown sequence completed")
        self.application = None

    async def graceful_shutdown(self) -> None:
        """Request a graceful shutdown of the Telegram application."""

        t('botapp.runtime.lifecycle.LifecycleManager.graceful_shutdown')
        await asyncio.sleep(1)

        if not self.application:
            self.logger.warning("No application instance available for shutdown request")
            return

        try:
            self.logger.info("Initiating graceful shutdown...")
            await self.application.stop()
            self.logger.info("Application stop requested")
        except Exception as exc:  # pragma: no cover - defensive guard
            self.logger.error("Error during graceful shutdown: %s", exc)

    async def log_metrics(self) -> None:
        """Collect and log key operational metrics."""

        t('botapp.runtime.lifecycle.LifecycleManager.log_metrics')
        try:
            user_manager = self.dependencies.user_manager
            all_users = user_manager.get_all_users()
            total_users = len(all_users)
            active_users = len([user for user in all_users.values() if user.get('is_active', False)])
            admin_users = len([user for user in all_users.values() if user.get('is_admin', False)])

            queue = self.dependencies.reservation_queue
            try:
                if hasattr(queue, 'get_all_reservations'):
                    all_reservations = queue.get_all_reservations()
                    queue_size = len(all_reservations)
                    pending_reservations = len([r for r in all_reservations if r.get('status') == 'pending'])
                else:
                    queue_size = 0
                    pending_reservations = 0
                    self.logger.debug("ReservationQueue.get_all_reservations method not available")
            except Exception as exc:
                queue_size = 0
                pending_reservations = 0
                self.logger.debug("Could not get reservation queue metrics: %s", exc)

            scheduler = self.dependencies.scheduler
            try:
                if hasattr(scheduler, 'stats'):
                    successful = scheduler.stats.get('successful_bookings', 0)
                    failed = scheduler.stats.get('failed_bookings', 0)
                    total_attempts = successful + failed
                    success_rate = (successful / total_attempts * 100) if total_attempts > 0 else 0
                else:
                    successful = failed = success_rate = 0
                    self.logger.debug("ReservationScheduler.stats not available")
            except Exception as exc:
                successful = failed = success_rate = 0
                self.logger.debug("Could not get scheduler metrics: %s", exc)

            self.logger.info(
                "=== BOT METRICS REPORT ===\n"
                f"👥 User Metrics:\n"
                f"   Total Users: {total_users}\n"
                f"   Active Users: {active_users}\n"
                f"   Admin Users: {admin_users}\n"
                f"📋 Queue Metrics:\n"
                f"   Total Reservations: {queue_size}\n"
                f"   Pending Reservations: {pending_reservations}\n"
                f"🤖 Scheduler Metrics:\n"
                f"   Successful Bookings: {successful}\n"
                f"   Failed Bookings: {failed}\n"
                f"   Success Rate: {success_rate:.1f}%\n"
                "=========================="
            )

        except Exception as exc:  # pragma: no cover - defensive guard
            self.logger.error("Error collecting bot metrics: %s", exc, exc_info=True)

    async def _metrics_loop(self) -> None:
        """Periodic metrics logging loop."""

        t('botapp.runtime.lifecycle.LifecycleManager._metrics_loop')
        try:
            while True:
                await self.log_metrics()
                await asyncio.sleep(300)
        except asyncio.CancelledError:
            self.logger.info("Metrics logging task cancelled")
            raise
        except Exception as exc:  # pragma: no cover - defensive guard
            self.logger.error("Error in metrics loop: %s", exc, exc_info=True)


__all__ = ['LifecycleManager']
