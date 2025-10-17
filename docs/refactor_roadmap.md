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
- Immediate-booking flow now delegates to helpers for user/profile lookup, request construction, flow orchestration, persistence, and notifications (`botapp/booking/immediate_handler.py`, `botapp/notifications.py`).
- Telegram UI split into dedicated modules (`botapp/ui/menus.py`, `booking.py`, `profile.py`, `admin.py`), with a thin compatibility facade for existing imports.
- Async browser pool refactored into modular helpers (`automation/browser/pool/{init,maintenance,health,tasks}.py`) and tracked via updated instrumentation tables.
- Reservation scheduler pipeline helpers extracted to `reservations/queue/scheduler/{pipeline,dispatch,outcome,metrics,browser_lifecycle}.py` and covered by targeted unit tests ensuring reservation grouping, dispatch behaviour, and stats reporting.
- Reservation queue now delegates persistence, duplicate-slot validation, and status transitions to focused helpers (`reservations/queue/reservation_{repository,validation,transitions}.py`) with matching unit coverage.
- Browser recovery now uses dedicated strategy executors under `automation/browser/recovery/strategies/` with shared types, reducing the recovery service to orchestration and telemetry.
- Acuity booking form logic split into stateless helpers (`automation/forms/{fields,actions}.py`) with `automation/forms/acuity_booking_form.py` acting as a thin orchestration facade for legacy callers.
- Availability helpers reorganised into modular components (`automation/availability/{dom_extraction,day_detection,time_grouping,time_utils,api}.py`) with `fetch_available_slots()` as the new entrypoint.
- Guardrails: baseline lint configuration added via `.flake8` (max line length, ignore rules) ready for CI integration once the new structure settles.
## Key Targets
- ~~`botapp/booking/immediate_handler.py` — replace the monolithic `_execute_booking` with helper methods ...~~ (completed).
- ~~`automation/executors/booking.py` fast/natural flow split with shared helpers~~ (completed by flows package).
- ~~`automation/executors/tennis.py` — builds `BookingRequest` via factory and delegates to `BookingFlowExecutor`~~ (completed).
- ~~`botapp/ui/telegram_ui.py` — split keyboard factories and message builders into context modules~~ (completed).
- ~~`automation/browser/async_browser_pool.py` — divide responsibilities into `automation/browser/pool_init.py`, `pool_maintenance.py`, `pool_health.py`, and `browser_tasks.py`~~ (completed via `automation/browser/pool/*`).
- `reservations/queue/reservation_scheduler.py` — reorganise into pipeline (`pull_ready_reservations`, `hydrate_booking_requests`, `dispatch_to_executors`, `record_outcome`), extracting dedicated modules (e.g., `scheduler/pipeline.py`, `scheduler/metrics.py`, `scheduler/browser_lifecycle.py`). Pipeline, dispatch, metrics, and browser lifecycle helpers now live under `reservations/queue/scheduler/` with unit coverage; metrics instrumentation and browser manager integration still need refinement alongside new monitoring hooks.
- `reservations/queue/reservation_queue.py` — move persistence to `reservation_repository.py`, validation to `reservation_validation.py`, and status transitions to `reservation_transitions.py`; ensure scheduler callers use the new abstractions. *In progress:* queue now uses the new helpers internally with accompanying unit tests; follow-up wiring for external callers and dataclass-based orchestration still required.
- `automation/browser/browser_pool_recovery.py` — convert strategy enums into strategy classes under `browser/recovery/strategies/`, provide service that composes strategies and surfaces structured telemetry. *Completed:* strategies extracted with shared types; outstanding work includes improving emergency fallback configuration and adding integration tests once browser harness is available.
- `automation/browser/browser_health_checker.py` — split signal collection and evaluation into `browser/health/collectors.py` and `browser/health/evaluators.py`, exposing `verify_browser(browser_id)` and `summarise_pool_status()` APIs.
- ~~`automation/forms/acuity_booking_form.py` — convert to stateless helper functions grouped under `automation/forms/fields.py` and `automation/forms/actions.py` for reuse across flows.~~ *(completed via helper modules; Playwright stubs still desirable for deeper coverage.)*
- ~~`automation/availability/support.py` — rework availability support into modular components and expose a single `fetch_available_slots(request, browser_context)` entrypoint consumed by flows.~~ *(completed with `automation/availability/{dom_extraction,day_detection,time_grouping,time_utils,api}.py`; integration tests pending once harness is ready.)*
- Update roadmap/docs/tests once the above modules are in place.

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
