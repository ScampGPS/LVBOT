# monitoring Manifest

## Purpose
Background monitors that watch court availability and site health outside of active booking flows.

## Files
- `court_monitor.py`: Polls court schedules and alerts when slots open.
- `realtime_availability_monitor.py`: Streams availability updates for dashboards or proactive notifications.
- `__init__.py`: Marks the package and exposes monitor entry points.

## Operational Notes
- Monitors rely on automation availability helpers; configure them with the same settings as the main bot to ensure consistent results.
- Consider scheduling via cron or an async task runner; they are not automatically started by `run_bot.py`.
