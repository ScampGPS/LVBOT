# Class Refactor & LOC Reduction Plan

**Overall Goal**: Cut at least 25% of the current high-priority LOC (~1,000 lines total) while replacing duplicated procedural code with cohesive, testable classes that keep behaviour stable.

## Inventory Summary

- `botapp/handlers/queue/handler.py`: 1695 lines, 5 functions, 1 classes
- `reservations/queue/reservation_scheduler.py`: 1442 lines, 21 functions, 2 classes
- `automation/forms/actions.py`: 250 lines, 2 functions, 0 classes
- `automation/forms/fields.py`: 144 lines, 0 functions, 0 classes
- `automation/browser/pools/specialized.py`: 916 lines, 6 functions, 2 classes
- `reservations/queue/request_builder.py`: 212 lines, 7 functions, 0 classes
- `reservations/queue/reservation_queue.py`: 444 lines, 16 functions, 2 classes
- `automation/executors/request_factory.py`: 162 lines, 4 functions, 0 classes
- `botapp/handlers/booking/handler.py`: 1234 lines, 1 functions, 1 classes
- `automation/browser/browser_health_checker.py`: 311 lines, 3 functions, 1 classes
- `automation/browser/emergency_browser_fallback.py`: 375 lines, 1 functions, 2 classes
- `botapp/messages/message_handlers.py`: 316 lines, 3 functions, 1 classes


## Objectives
- Reduce total Python LOC by eliminating duplicated flows and legacy entry points while maintaining behaviour.
- Introduce cohesive classes where modules currently expose many loosely-related functions; the goal is smaller, focused surfaces that enable code removal.
- Target high-traffic modules first so downstream work (queue, scheduler, browser) benefits immediately.

## Phase 1 – Queue Handler (`botapp/handlers/queue/handler.py`, 1,695 LOC, 40+ async handlers)
### Findings
- Repeated callback scaffolding: nearly every `handle_*` method performs the same sequence (answer query → load session → render message → update session). There are 40+ `_edit_callback_message` calls with inline Markdown variations.
- Duplicate formatting for confirmations, duplicates, and error prompts (e.g., `format_queue_reservation_added`, hard-coded Markdown blocks, and almost identical status lists inside `handle_queue_booking_court_selection`, `handle_queue_booking_confirm`, and modification helpers).
- Session interactions (`queue_session.set_*`, `clear_all`, etc.) scattered across handlers, leading to repetitive guard code.

### Actions
- [x] Create `QueueBookingFlow` class that owns the booking-specific callback chain (`handle_queue_booking_*`). The class should capture dependencies (UI builders, session accessor) and expose concise methods (e.g., `select_date`, `select_time`, `select_courts`, `confirm`).
- [x] Create `QueueReservationManager` (or `QueueReservationFlow`) for the reservation viewing/modification paths (`handle_my_reservations_menu`, `handle_queue_reservation_view`, `handle_queue_modify_*`). This separates management operations from booking initiation and lets us drop cross-branch conditionals.
- [x] Introduce `QueueMessageFactory` to build shared Markdown payloads. Consolidate:
   - Success templates currently hard-coded at lines ~860, 918, 974.
   - Duplicate warnings around lines ~788, 929.
   - Error prompts for missing session data (lines ~835, 993, 1220).
   Removing these inline blocks should eliminate 150–200 LOC immediately.
- [x] Consolidate session guard logic into helper methods (`ensure_summary`, `ensure_profile_fields`). Once the helpers exist, delete the redundant guard code from each handler.
- [x] Drop redundant compatibility helpers `_clear_queue_booking_state` (just forwarders) and merge legacy key handling once the class wrappers own the flow.

**Expected reduction:** 250–350 LOC once repeated message text and guard logic move into shared helpers and classes.

## Phase 2 – Reservation Scheduler (`reservations/queue/reservation_scheduler.py`, 1,442 LOC, 41 functions)
### Findings
- `_run_scheduler_loop`, `_execute_reservations`, `_process_ready_reservations` duplicate pipeline steps (pull → hydrate → dispatch → record) with local helper functions sprinkled throughout.
- Multiple failure result builders (`_failure_result_from_reservation`, inline tuples in `_record_failure`, etc.) all reconstruct the same `BookingResult` payloads.
- Legacy compatibility branches: calls to `ImmediateBookingHandler.execute_queue_booking`, `_execute_booking`, and duplicated dispatch logging keep old interfaces alive.

### Actions
1. Implement `SchedulerPipeline` with explicit stages (`pull_ready`, `hydrate_requests`, `dispatch`, `record_outcome`). Each stage maps to existing helper functions; migrating them into a class allows us to delete duplicated loops in `_execute_reservations` and `_process_ready_reservations`.
2. Add `ReservationHydrator` to encapsulate `_get_reservation_field`, `_build_executor_user_info`, and `_prepare_requests`. This consolidates the hydration logic and removes repeated dict access across the file.
3. Introduce `OutcomeRecorder` that handles persistence (`persist_queue_outcome`), notification formatting, and failure result creation. Once in place, drop `_booking_result_to_dict`, `_failure_result_from_reservation`, and the repeated metadata assembly inside `dispatch_to_executors` and `_record_failure`.
4. Remove legacy pathways after the new classes are wired:
   - Delete `execute_queue_booking` calls and rely on `ImmediateBookingHandler._run_booking_attempts` directly.
   - Remove legacy threading controls (`self.scheduler_thread`, `_legacy_start`) if no longer used.
5. After consolidation, re-run the module-level LOC report and ensure we’ve shaved at least ~300 lines (merging pipeline loops + removing redundant failure helpers accounts for most of that).

## Phase 3 – Form Actions & Specialized Browser (`automation/forms/actions.py`, 243 LOC; `automation/forms/fields.py`, 200 LOC; `automation/browser/pools/specialized.py`, 916 LOC)
### Findings
- Actions module contains stateful concerns (logger, JS vs Playwright strategy, tracing) without a shared object, leading to repeated parameter plumbing.
- Specialized browser recreates the same form mapping (`nombre/apellidos/telefono/correo`) and success handling each time it submits a booking.

### Actions
1. Create `AcuityFormService` class with constructor parameters for `logger`, `use_javascript`, and tracing options. Methods: `fill_form`, `submit`, `check_success`, `validate`. This removes repeated `logger` plumbing and consolidates trace management.
2. Refactor `fill_fields_javascript`/`fill_fields_playwright` into strategy methods (`_fill_via_js`, `_fill_via_playwright`) inside the service or an inner strategy object, eliminating duplicate loops across modules.
3. Update `automation/browser/pools/specialized.py` to consume the service. Remove inline dict creation at lines ~633–638 (already partially replaced by `map_user_info`) and consolidate post-booking logging into helper methods.
4. Delete the now-unused free functions (`check_booking_success`, etc.) once the service exposes equivalent methods, easing maintenance and saving ~80–100 lines between forms and specialized browser modules.

## Phase 4 – Reservation Builders & Queue Persistence (`reservations/queue/request_builder.py`, 200 LOC; `reservations/queue/reservation_queue.py`, 444 LOC)
### Findings
- Multiple helper functions perform similar transformations between raw dicts, `ReservationRequest`, and queue JSON.
- Queue persistence still accepts dicts and then immediately constructs dataclasses during listing.

### Actions
1. Introduce `ReservationRequestBuilder` class with methods:
   - `from_summary(summary_dict)` – current `build_reservation_request_from_summary` logic.
   - `from_dict(raw_reservation, user_profile=None)` – current `build_request_from_reservation`.
   - `to_payload(reservation_request)` – current `reservation_request_to_payload`.
   Move validation (`_parse_date`, `_normalise_courts`, `_resolve_user`) into private methods of the class, allowing us to delete standalone helpers.
2. Update queue callers to instantiate the builder once (dependency-injected) instead of calling module functions. This lets us drop import cycles and easily cache parsed values.
3. Introduce `QueueRecordSerializer` in `reservation_queue.py` to manage JSON storage (serialize/deserialize). Remove inline dict creation in `add_reservation` and the manual dataclass reconstruction in `list_reservations`.
4. After the serializer is in place, remove the legacy branch that stores dicts when a `ReservationRequest` is already available. `add_reservation` can accept only dataclasses (with an adapter for any remaining dict callers), reducing branching and line count.

## Phase 5 – Additional High-LOC Targets
1. `botapp/handlers/booking/handler.py` (1,234 LOC)
   - Shared templates for availability prompts, error messages, and confirmation flows can move into a `BookingUIFactory` class.
   - Extract `BookingFlowController` to manage the sequential state machine, letting us delete repeated session manipulation code.
2. `automation/browser/browser_health_checker.py` (311 LOC)
   - Collapse repeated polling/error-reporting loops into a `HealthCheckRunner` with per-check strategy objects.
3. `automation/browser/emergency_browser_fallback.py` (375 LOC)
   - Introduce `BrowserRecoveryManager` and strategy classes (restart, reassign, refresh) to remove duplicated `try/except` blocks.
4. `botapp/messages/message_handlers.py` (316 LOC)
   - Split into `MessageSender`, `MessageEditor`, `ChunkedResponder`; allows removal of repeated logging scaffolds and argument normalization.

Each of these modules has identifiable duplication (e.g., the same `await bot.send_message` wrappers scattered across functions). Consolidating them into classes should cut tens of lines per module while improving reuse.

## LOC Reduction Tracking
- After each phase, run `python - <<'PY' ...` LOC report to confirm reductions.
- Target: reduce combined LOC of the four major modules (queue handler, scheduler, specialized browser, booking handler) by at least 25% (~1,000 lines) through duplication removal and class extraction.

## Verification & Rollout
1. Maintain unit coverage: existing tests (`tests/unit/test_queue_handler_callbacks.py`, `test_reservation_queue.py`, `test_form_actions.py`, scheduler tests) must be updated or extended to match the new classes.
2. Run bot sanity check (`python run_bot.py --help` on Windows CMD) after each phase to detect runtime regressions.
3. Document new classes in `docs/refactor_plan.md` once implemented so future contributors know the intended architecture.


## Phase 6 – Medium LOC/Class Offenders
### 6.1 `monitoring/realtime_availability_monitor.py` (376 LOC)
- Duplicate polling loops per court/slot; introduce `AvailabilityPoller` class with strategies for API vs DOM checks.
- Consolidate notification formatting into a shared helper to eliminate repeated Markdown strings.

### 6.2 `automation/browser/emergency_browser_fallback.py` (375 LOC)
- Already earmarked for recovery strategies; implement `BrowserRecoveryManager` plus `RestartStrategy`, `ReassignStrategy`, `RefreshStrategy` to remove duplicated `try/except` blocks and logging.

### 6.3 `monitoring/court_monitor.py` (351 LOC)
- Similar structure to realtime monitor; reuse `AvailabilityPoller` and move shared alert logic to reduce LOC.

### 6.4 `botapp/messages/message_handlers.py` (316 LOC)
- Create `MessageSender`, `MessageEditor`, `ChunkedResponder` classes to centralise throttling, Markdown escaping, and retry logic, replacing duplicated `await bot.send_message` blocks.

### 6.5 `automation/browser/browser_health_checker.py` (311 LOC)
- Introduce `HealthCheckRunner` that sequences collectors/evaluators; move repeated logging and result summarisation into reusable methods.

### 6.6 `botapp/error_handler.py` (307 LOC)
- Convert to `BotErrorResponder` with pluggable handlers for booking, queue, admin errors; collapse duplicated error message construction.

### 6.7 `automation/executors/booking.py` (281 LOC)
- Split `BookingFlowExecutor` into base class plus `NaturalFlowExecutor` / `FastFlowExecutor` subclasses to reduce branching and inline logging duplication.

### 6.8 `automation/browser/lifecycle.py` (283 LOC)
- Create `BrowserLifecycleManager` that encapsulates start/stop/refresh operations; remove repeated context manager patterns.

### 6.9 `tracking/instrument.py` (283 LOC)
- Consolidate instrumentation builders into `InstrumentFactory` to eliminate repeated dict assembly for timers/counters.

### 6.10 `automation/executors/booking_orchestrator.py` (531 LOC – medium-high but already structured)
- After core phases, revisit to split `prepare`, `execute`, `finalise` into dedicated components, removing inline state tracking.


## Phase 7 – Small LOC/Class Offenders (100–250 LOC)
### 7.1 `botapp/handlers/queue/session.py` (236 LOC)
- Current state: dataclass + numerous `set_*/get_*` helpers duplicating guard/persist logic.
- Plan: introduce `QueueSessionStore` class with methods `update(date=None, time=None, courts=None, summary=None)` and `clear()`. Collapse the `set_*`/`get_*` helpers into properties and remove duplicated legacy key handling. Target reduction: ~60 LOC.

### 7.2 `automation/forms/acuity_booking_form.py` (186 LOC)
- After Phase 3’s `AcuityFormService`, convert this module into a thin façade class or drop it entirely if callers can use the service directly. Expected reduction: 70–90 LOC by removing duplicated validation/submission wrappers.

### 7.3 `botapp/notifications.py` (180 LOC)
- Factor repeated Markdown-building into a `NotificationBuilder` class (success, failure, duplicate). Use templates for bullet lists/buttons instead of inline string assembly. Estimated savings: 40–50 LOC.

### 7.4 `botapp/runtime/lifecycle.py` (187 LOC) & `botapp/runtime/bot_application.py` (175 LOC)
- Introduce `LifecycleManager` (state, start, shutdown) and `BotApplication` composition helpers—merge repeated startup/shutdown logging and environment checks. Reduces duplication between runtime modules (~50 LOC total).

### 7.5 `automation/browser/pool/{init,maintenance}.py` (230 & 191 LOC)
- Combine into `BrowserPoolManager` class with methods `initialize_pool`, `schedule_maintenance`, `check_health`. Shared logging and retry loops shrink both modules (target: 70 LOC combined).

### 7.6 `automation/availability/checker.py` (219 LOC)
- Create `AvailabilityChecker` class with pluggable sources (API, DOM). Remove repeated loop scaffolding around `datetime_helpers` and consolidate alert generation (saves ~40 LOC).

### 7.7 `automation/executors/flows/natural_flow.py` (157 LOC)
- Extract `NaturalFlowSteps` class encapsulating navigation/filling/confirmation to reuse with fast flow; restructure to share DOM selectors and reduce inline logging duplication (~30 LOC).

### 7.8 `botapp/notifications.py` & `botapp/ui/profile.py` (211 LOC)
- For profile UI, introduce `ProfileViewBuilder` and reuse with notifications to share bullet formatting, trimming repeated emoji/text generation (~30 LOC).

### 7.9 `botapp/callbacks/parser.py` (174 LOC)
- Implement `CallbackParser` class with registry for known patterns; remove repeated `split('_')` logic across handlers. Expect 25–30 LOC reduction.

### 7.10 `automation/executors/request_factory.py` (162 LOC)
- After Phase 2 rewrite, downsize by merging the retry builder into the new class and deleting `_normalise_user` duplication. Additional savings: ~20 LOC.

These smaller refactors leverage the larger architectural changes to finish trimming residual duplication and ensure future features tap the shared helper classes.
