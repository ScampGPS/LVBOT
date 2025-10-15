# LVBot Module Migration Map

Working document that links existing modules (primarily under `lvbot/utils`) to
their target homes in the post-refactor package layout. Package scaffolding for
`lvbot/automation/{browser,executors,availability}` and `lvbot/domain/{queue,models}`
was added in Phase 1 so code can migrate incrementally without disrupting
imports.

## Automation Layer
- **Browser Core** → `lvbot/automation/browser/`
  - `async_browser_pool.py`
  - `async_browser_helpers.py`
  - `browser_lifecycle.py`
  - `browser_refresh_manager.py`
  - `browser_pool_recovery.py`
  - `browser_health_checker.py`
  - `browser_allocation.py`
  - `browser_refresh_manager.py`
  - `emergency_browser_fallback.py`
  - `stateful_browser_refresh.py`
- **Executors & Orchestrators** → `lvbot/automation/executors/`
  - `async_booking_executor.py`
  - `smart_async_booking_executor.py`
  - `experienced_booking_executor.py`
  - `working_booking_executor.py`
  - `optimized_navigation.py`
  - `reliable_navigation.py`
  - `tennis_executor.py`
  - `booking_orchestrator.py`
  - `reservation_helpers.py`
- **Availability Parsing** → `lvbot/automation/availability/`
  - `async_availability_checker.py`
  - `availability_checker_v3.py`
  - `availability_checker_v2.py` (legacy)
  - `time_slot_extractor.py`
  - `time_order_extraction.py`
  - `court_availability.py`
  - `day_mapper.py`
  - `day_context_parser.py`
  - `datetime_helpers.py`

## Domain Layer
- **Queue & Scheduling** → `lvbot/domain/queue/`
  - `reservation_queue.py`
  - `priority_manager.py`
  - `reservation_scheduler.py`
  - `reservation_tracker.py`
  - `reservation_helpers.py` (split shared logic with automation)
- **Domain Models** → `lvbot/domain/models.py`
  - `models/time_slot.py`
  - Introduce dataclasses for queue items, booking attempts, user tiers.
- **User & State Management** → `lvbot/domain/users.py`
  - `user_manager.py`
  - `state_manager.py`
  - `telegram_ui.py` (UI DTOs move to bot layer; domain surfaces pure data)

## Infrastructure Layer
- **Configuration & Settings** → `lvbot/infrastructure/`
  - `settings.py` (new)
  - `logging_config.py`
  - `constants.py`
  - `error_handler.py`
- **Persistence** → `lvbot/infrastructure/persistence/`
  - `db_helpers.py`
  - JSON adapters for queue/users once introduced.
- **Monitoring & Diagnostics** → `lvbot/infrastructure/monitoring/`
  - `monitoring/court_monitor.py`
  - `monitoring/realtime_availability_monitor.py`

## Bot Layer
- `bot/telegram_tennis_bot.py` consumes services via new interfaces.
- `handlers/callback_handlers.py` migrates to thin orchestration wrappers that
  call domain services.
- `telegram_ui.py` splits into presentation-only helpers under `bot/ui/`.

## De-Duplication Targets
- ~~Archive `async_booking_executor_backup.py` and `async_booking_executor_clean.py`
  after the consolidated executor is in place.~~ ✅ Archived to
  `docs/archive/legacy_modules/` during Phase 0.5 cleanup.
- Merge `working_booking_executor.py`, `experienced_booking_executor.py`, and
  `smart_async_booking_executor.py` behind feature flags so a single async
  executor exposes configuration toggles instead of module forks.
- Retire `optimized_booking_executor.py` once the Phase 3 automation facade is
  implemented or replace its unique behaviour with opts on the canonical
  executor.

## Data & Assets
- Move `queue.json`, `users.json`, and related test fixtures into
  `lvbot/infrastructure/data/` with repository wrappers.
- Sanitize any committed personal data during the migration.

This map will evolve as phased refactor work lands; update alongside new
package introductions to keep contributors oriented.
