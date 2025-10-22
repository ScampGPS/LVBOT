# Refactor Guide

## Principles
- Favor readable orchestration: high-level functions should read like plain English and call small verbs.
- Keep functions single-purpose and ≤50 lines whenever practical; keep modules ≤500 lines by extracting focused helpers.
- Prefer DRY, modular utilities shared across handlers (UI, formatting, validation, data access).
- Centralize domain rules so the same logic powers bot flows, schedulers, and automation.
- Preserve stability: stage refactors, keep logging parity, and back changes with unit/integration coverage.

## Completed Refactors

- **Callback Handler modularization** – introduced `CallbackRouter`, split booking/queue/profile/admin handlers, added `CallbackDependencies`, and retired the monolithic dispatcher (validated by `py -m pytest`).
- **Queue Handler restructure** – introduced typed session helpers, shared UI formatters, and trimmed queue flow handlers into single-purpose methods with updated harness coverage requirements.

## Next Major Refactor

### reservations/queue/reservation_scheduler.py
- Scope: finish extracting the scheduler pipeline into modular helpers (pipeline, dispatch, metrics, browser lifecycle) and streamline orchestration.
- Goals: make the scheduler read as `fetch → hydrate → dispatch → record`, centralise metrics reporting, and share queue execution logic with the rewritten handler.
- Constraints: keep existing scheduling behaviour, reuse telemetry hooks, and extend the harness to validate background execution.

#### Planned Steps
1. **Isolate pipeline stages** (pull ready reservations, build booking requests, dispatch executors, record outcomes) into dedicated modules and wire them through a slim orchestrator.
2. **Consolidate metrics/telemetry** into shared helpers so logging and monitoring are consistent and easier to test.
3. **Clarify browser lifecycle interactions** by moving stop/start routines into explicit helpers and ensuring idempotent cleanup.
4. **Add focused unit tests** for each extracted stage plus integration coverage that exercises the scheduler loop with faked queues/executors.
5. **Update the harness** to run scheduler scenarios alongside the main bot sanity flow to validate the refactored structure.

## Future Refactor Candidates

1. `botapp/handlers/booking/handler.py` (~1,200) – introduce small helpers for calendar management and message building.
2. `automation/browser/pools/specialized.py` (~900) – break smart assignment/retry logic into strategies.
3. `botapp/ui/booking.py` (~700) – keep UI components declarative and shared across flows.
4. `automation/executors/booking_orchestrator.py` (~530) – split into `prepare → execute → finalise` steps.
5. `reservations/queue/reservation_queue.py` (~450) – finish delegating persistence/validation/transition logic.
6. `botapp/handlers/profile/handler.py` (~445) – centralize keypad and validation helpers.
7. `botapp/handlers/admin/handler.py` (~435) – extract admin UI builders and data readers.
8. `botapp/booking/immediate_handler.py` (~400) – isolate user lookup, flow execution, and result messaging.
9. `monitoring/realtime_availability_monitor.py` (~376) – share monitoring core utilities.
10. `automation/browser/emergency_browser_fallback.py` (~374) – extract recovery strategies and telemetry helpers.
11. `monitoring/court_monitor.py` (~351) – mirror the monitoring refactor above.
12. `botapp/messages/message_handlers.py` (~316) – split reply/edit/chunked-send logic into focused helpers.
13. `automation/browser/browser_health_checker.py` (~311) – move polling/reporting into reusable utilities.
14. `automation/executors/booking.py` (~291) – cleanly separate natural vs fast vs orchestrator logic.
15. `automation/forms/actions.py` (~243) – extract raw DOM scripts/query helpers for shorter functions.
