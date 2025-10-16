# Refactor Roadmap: Readable Orchestration & Size Limits

## Objectives
- Deliver booking workflows that read as English-style sequences (`book_time_slot` → helpers) while preserving behaviour.
- Constrain files to ≤500 lines and core functions to ≤50 lines by extracting focused helpers.
- Keep orchestration surfaces consistent between bot triggers, queued execution, and automation flows.
- Maintain operational stability through staged extraction, logging parity, and targeted verification.

## Progress
- Shared booking contracts are implemented (`automation/shared/booking_contracts.py`) with builders/adapters in bot, queue, and executor layers (`botapp/booking/request_builder.py`, `reservations/queue/request_builder.py`, `automation/executors/request_factory.py`).
- Immediate booking handler and reservation scheduler now consume those contracts, persisting results via the new helpers and unified notifications (`botapp/booking/persistence.py`, `reservations/queue/persistence.py`, `botapp/notifications.py`).
- Documentation and tests cover the contract lifecycle and critical flows (`docs/booking_contract_mapping.md`, `docs/booking_flow_contracts.md`, `tests/unit/test_immediate_booking_flow.py`, `tests/unit/test_queue_scheduler_flow.py`).
- Working/experienced/smart executors collapsed into a single `BookingFlowExecutor`; async orchestration routes through it and the smart flow logic has been removed.

## Key Targets
- `botapp/booking/immediate_handler.py` — replace the monolithic `_execute_booking` with helper methods (`fetch_user_profile`, `build_booking_request`, `run_booking_attempts`, `persist_immediate_success`, `send_success_notification`, `send_failure_notification`). Relocate confirmation UI construction to `botapp/ui/confirmation_ui.py` and message formatting to `botapp/notifications.py`.
- `automation/executors/booking.py` — introduce shared value objects (`BookingRequest`, `BookingResult`), move `_execute_booking_internal` into `automation/executors/flows/working_flow.py`, and split fast/experienced logic into `flows/experienced_flow.py` with smart routines in `flows/smart_flow.py`. Provide `automation/executors/helpers.py` for cross-flow utilities (`locate_time_button`, `fill_booking_form`, `wait_for_confirmation`).
- `automation/executors/tennis.py` — update `TennisExecutor.execute` to construct a `BookingRequest` via a new `build_booking_request_from_tennis_config` helper and delegate booking to `book_time_slot(request)`.
- `botapp/app.py` — carve out browser pool wiring, reservation bootstrap, command registration, and notification delivery into modules (`botapp/bootstrap/browser_pool_factory.py`, `botapp/bootstrap/reservation_setup.py`, `botapp/commands/handlers.py`, `botapp/notifications.py`). Ensure `CleanBot` becomes a thin coordinator.
- `automation/browser/async_browser_pool.py` — divide responsibilities into `automation/browser/pool_init.py`, `pool_maintenance.py`, `pool_health.py`, and `browser_tasks.py`, leaving `async_browser_pool.py` as a concise facade.
- `botapp/handlers/callback_handlers.py` — extract feature routers into packages (`botapp/handlers/profile`, `.../admin`, `.../queue`, `.../booking`). Each router owns its callback map and uses shared UI/notification helpers.
- `botapp/ui/telegram_ui.py` — split keyboard factories and message builders into context-specific modules (`botapp/ui/menus.py`, `.../booking.py`, `.../profile.py`, `.../admin.py`) with centralised emoji/text constants.
- `reservations/queue/reservation_scheduler.py` — reorganise into a pipeline (`pull_ready_reservations`, `hydrate_booking_requests`, `dispatch_to_executors`, `record_outcome`). Delegate browser pool lifecycle to `browser_pool_manager` and metrics to a `scheduler_metrics` helper.
- `reservations/queue/reservation_queue.py` — move persistence to `reservation_repository.py`, validation to `reservation_validation.py`, and status transitions to `reservation_transitions.py`. Provide orchestration-facing methods that operate on `BookingRequest`/`BookingResult`.
- `automation/browser/pools/specialized.py` — relocate creation and maintenance routines to `pools/specialized/init.py` and `pools/specialized/maintenance.py`, leaving a facade that configures courts and surfaces async handles.
- `automation/browser/browser_pool_recovery.py` — convert strategy enums into strategy classes under `browser/recovery/strategies/` and expose a service that composes them, returning structured telemetry results.
- `automation/executors/booking_orchestrator.py` — separate priority computation and assignment logic into `booking_orchestrator/priority.py` and `booking_orchestrator/assignment.py`. Keep the orchestrator focused on sequencing and emitting `BookingResult` objects.
- `automation/browser/browser_health_checker.py` — divide signal collection and evaluation into `browser/health/collectors.py` and `browser/health/evaluators.py`, exposing `verify_browser(browser_id)` and `summarise_pool_status()` APIs.
- `automation/forms/acuity_booking_form.py` — convert to stateless helper functions grouped under `automation/forms/acuity/fields.py` and `.../submission.py`, consuming `BookingRequest` contact data and returning structured error info.
- `automation/availability/support.py` — split DOM extraction into `availability/dom_extraction.py`, parsing into `availability/slot_parsing.py`, and timezone logic into `availability/time_conversion.py`. Provide a unified `fetch_available_slots(request)` entrypoint for executors.

## Execution Strategy
1. **Establish shared contracts** *(completed)*
   - Create `automation/shared/booking_contracts.py` containing `BookingRequest` and `BookingResult` dataclasses with explicit field annotations, defaults, and helper constructors (`from_immediate_payload`, `from_reservation_record`).
   - Produce an integration matrix (`docs/booking_contract_mapping.md`) mapping every current payload source (immediate handler, callback handlers, reservation scheduler, tennis executor, tests) to the new dataclass fields, including transformation steps and ownership.
   - Add adapter helpers: `botapp/booking/request_builder.py` for bot-driven inputs, `reservations/queue/request_builder.py` for queued jobs, and `automation/executors/request_factory.py` for executor-side needs.
   - Publish API contracts for persistence and notifications: `persist_immediate_success(request, result)`, `persist_queue_outcome(reservation_id, result)`, `send_success_notification(user_id, result)`, and `send_failure_notification(user_id, result)` in their respective modules.
   - Document data flow in `docs/booking_flow_contracts.md`, describing how `BookingRequest` originates, how `BookingResult` feeds back into bot messaging, queue updates, and browser diagnostics.

2. **Restructure immediate booking handler**
   - Implement helper modules mentioned above and replace inline logic with method calls limited to orchestration.
   - Ensure `_execute_booking` delegates to `run_booking_attempts(request)` and only handles top-level control flow, error capture, and logging.
   - Move confirmation UI rendering into `botapp/ui/confirmation_ui.py` and update imports across callback handlers and tests.

3. **Recompose automation executors**
   - Create the `automation/executors/flows/` package with working, experienced, and smart flow modules, each exporting `execute(request)` returning `BookingResult`.
   - Move shared routines to `automation/executors/helpers.py` and adjust executors to call them.
   - Update `automation/executors/__init__.py` to expose a simple `book_time_slot(request)` API.
   - Update `automation/executors/tennis.py` to utilise the new flows and constructors.

4. **Decouple bot orchestration and UI**
   - Move bootstrap logic into dedicated modules and reduce `CleanBot` to configuration assembly plus dependency injection.
   - Replace the monolithic callback handler with feature-specific routers wired together in a central registry.
   - Introduce the new UI modules and update every call site to use focused keyboard builders and message formatters.

5. **Revise scheduler and queue infrastructure**
   - Implement the pipeline functions inside `reservations/queue/pipeline.py`, refactor `ReservationScheduler` to invoke them, and update metrics collection via `scheduler_metrics`.
   - Extract repository, validation, and transition helpers referenced above, ensuring they operate on dataclasses instead of raw dicts.
   - Ensure queued execution uses the same `BookingRequest`/`BookingResult` structures and persistence helpers as the immediate flow.

6. **Segment browser pool responsibilities**
   - Move pool creation, maintenance, health, and recovery routines into the new modules, updating imports across executors and scheduler components.
   - Ensure health and recovery services expose consistent methods (`collect_signals()`, `evaluate_pool_health()`, `recover_with_strategy(...)`) returning typed results consumed by orchestrators.
   - Update `automation/browser/pools/specialized.py` to rely on the extracted modules while maintaining current public behaviour.

7. **Modernise form and availability helpers**
   - Rebuild Acuity helpers around stateless functions that accept `BookingRequest` data, return structured error details, and share DOM utilities with executors.
   - Rework availability support into modular components and expose a single `fetch_available_slots(request, browser_context)` entrypoint consumed by flows.

8. **Guardrails and verification**
   - Introduce lint configuration (max line/function size) and integrate it into CI once the above structural changes compile.
   - Add unit tests for each new helper module, plus smoke tests covering immediate booking, queued booking, and tennis flows.
   - Provide logging parity checks to ensure new modules emit comparable telemetry to the legacy implementation during rollout.

## Delivery Sequence
1. ✅ Build shared booking contracts, adapters, and documentation artefacts described in Execution Strategy step 1.
2. Refactor the immediate booking handler and related UI/notification modules to use the shared contracts.
3. Split automation executors into flow modules, adjust tennis executor, and reintroduce orchestrator helpers around the new value objects.
4. Decompose bot orchestration (`botapp/app.py`, callback routers, Telegram UI modules) while keeping behavioural parity.
5. Restructure reservation scheduler and queue utilities onto the shared booking contracts.
6. Extract browser pool lifecycle, health, and recovery modules, wiring them back into executors and scheduler.
7. Modernise form handling and availability helpers, then activate lint/test guardrails.

## Notes
- Execute refactors in small, verifiable commits with feature flags or toggles where necessary.
- Preserve logging statements or provide replacements with identical keys to maintain monitoring continuity.
- Update this roadmap whenever module names or contract definitions evolve so downstream teams always have a current reference.
