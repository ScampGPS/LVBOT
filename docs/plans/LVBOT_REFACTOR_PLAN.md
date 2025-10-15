# LVBot Refactor & Modularization Plan

## Phased Overview
1. **Phase 0 – Baseline Audit**: capture current behaviour with smoke scripts, logs, and dependency notes.
2. **Phase 0.5 – Cleanup & Archival**: trace `lvbot/bot/telegram_tennis_bot.py`, purge unused assets/tests, archive legacy helpers, and summarize removals.
3. **Phase 1 – Architecture & Naming**: finalize the end-state module graph, rename docs/README, and ensure namespace scaffolding is in place.
4. **Phase 2 – Source Reorganization**: move live code into the new package layout, update imports, and merge duplicate implementations.
5. **Phase 3 – Automation Consolidation**: introduce the unified async executor, shared browser settings, and browser lifecycle facade.
6. **Phase 4 – Domain Services**: wrap queue/scheduler/orchestrator in service interfaces with dataclasses, decoupling scheduling from Telegram lifecycle.
7. **Phase 5 – Data & Configuration Hygiene**: relocate/sanitize data assets and centralize environment handling.
8. **Phase 6 – Testing & Tooling**: establish pytest/mypy/ruff, expand unit/integration coverage, and wire headless smoke tests into CI.
9. **Phase 7 – Documentation & Polish**: refresh README/workflows, publish cleanup notes, verify CI, and remove any lingering deprecated modules.

## 1. Objectives
- Reduce duplication and tighten module boundaries without altering existing runtime behaviour.
- Clarify ownership of orchestration vs. execution responsibilities inside the bot.
- Make the project approachable for future contributors by updating docs, naming, and directory layout.
- Provide enough scaffolding (tests, lint hooks, logging conventions) to validate future logic changes quickly.

## 2. Guardrails
- **No functional regressions**: refactor commits must produce identical observable behaviour (Telegram UX, booking outcomes, logs).
- **No new feature work** until the refactor baseline is complete.
- **Config and credentials remain externalised**; secrets stay out of source even if placeholders continue temporarily.
- Prefer incremental pull requests mapped to the phases below.

## 3. Preparation & Audit
1. Capture the current surface area (commands, handlers, scheduler entrypoints) in a short architecture note.
2. Freeze the current logs and test artifacts; create a reference branch/tag (`pre-refactor`) for diffs.
3. Run targeted smoke scripts (availability check, queue booking, immediate booking) and archive outputs to compare later.
4. Enumerate implicit dependencies (e.g., manual seeds in `data/*.json`, hardcoded paths) and document them before moving code.

## 4. Pre-Refactor Cleanup & Archival Prep
- Inventory the Telegram entrypoint (`bot/telegram_tennis_bot.py`) and follow its import graph to document active dependencies vs. legacy helpers.
- Identify modules, tests, and scripts that the bot no longer touches; move them into `docs/archive/` or remove them once verified obsolete.
- Sweep repository artifacts (logs, screenshots, large JSON fixtures) and delete anything outside the new `testing/` structure that lacks a clear retention purpose.
- Flag heavy debugging suites or experimental Playwright runs for archival so the refactor starts from a lean baseline.
- Capture decisions in a short cleanup report so future contributors understand why files were removed or archived.

## 5. Architecture Alignment
- **Module naming**: rename references to removed modules (`playwright_bot.py`, `browser_pool.py`, etc.) in README and docs; align them with `utils/async_browser_pool.py`, `utils/availability_checker_v3.py`, etc.
- **Package structure**: introduce top-level packages to separate concerns:
  - `bot/` (Telegram entrypoint, handlers, UI helpers)
  - `automation/` (browser pools, executors, availability parsing)
  - `domain/` (reservation queue, scheduler, priority logic)
  - `infrastructure/` (logging config, persistence helpers)
- Add `__init__.py` files and update imports to absolute package paths once the folders exist.
- Define the desired end-state module graph so each capability (scheduling, automation, UI, monitoring) has a single authoritative implementation.
- Inventory duplicate or near-duplicate modules (e.g., the many booking executor variants) and decide which one becomes canonical before refactoring begins.
- Document merge strategies for overlapping functionality so consolidation work in later phases has a clear target behaviour.

## 6. Browser & Automation Layer
- Extract configuration flags (headless/headful, warm-up delay, timeout profiles) from `utils/async_browser_pool.py` into a dedicated settings object so environments can override them without code edits.
- Collapse legacy variants (`async_booking_executor_backup.py`, `working_booking_executor.py`, `optimized_booking_executor.py`) into a single `automation/executors/async_executor.py` module retaining feature flags (`experienced_mode`, `natural_flow`). Mark experimental logic behind feature toggles instead of duplicate files.
- Ensure helper utilities (`async_browser_helpers`) expose a consistent async API; remove dead sync variants and wrap any remaining sync calls.
- Integrate browser health, recovery, and lifecycle helpers through a cohesive `BrowserManager` facade to avoid ad-hoc initialization in multiple modules.

## 7. Scheduler & Reservation Pipeline
- Move queue persistence, scheduler, orchestrator, and priority management under `domain/` with clear interfaces (`QueueRepository`, `SchedulerService`, `BookingOrchestrator`).
- Replace ad-hoc dictionaries passed between modules with lightweight dataclasses (e.g., `ReservationRequest`, `BookingAttempt`) defined in a shared `domain/models.py` without changing field semantics.
- Decouple scheduler start/stop from the Telegram application life cycle by introducing an application service layer; handlers call service methods instead of touching queue internals.
- Normalize retry/backoff logic across `ReservationScheduler`, `ReservationHelpers`, and executors so the same constants are reused.

## 8. Data & Configuration Hygiene
- Relocate JSON data files to `infra/data/` and wrap access behind repository classes to ease swapping storage later.
- Remove personally identifiable information from committed JSON fixtures; replace with sanitized seed data and document required fields.
- Centralize environment variable loading (e.g., via `python-dotenv` guard) in a single `settings.py` to avoid scattered `os.getenv` lookups.

## 9. Testing & Validation Improvements
- Introduce a `tests/unit` suite covering
  - `ReservationQueue` persistence semantics
  - Availability parsing (`AvailabilityCheckerV3`, `TimeSlotExtractor`)
  - Scheduler prioritization logic with mocked time.
- Add `tests/integration` scripts to exercise Telegram command handlers via `Application.run_polling` test harness or mocked dispatcher.
- Provide a minimal Playwright smoke test that runs headless in CI to verify browser pool bootstrap.
- Set up pytest configuration, type checking (mypy or pyright), and linting (ruff/flake8) with pre-commit hooks.

## 10. Documentation & Developer Experience
- Rewrite README’s architecture section to mirror the new package layout and remove outdated references.
- Generate module reference docs (Sphinx or mkdocs) once namespaces settle.
- Document standard workflows: adding a new handler, extending scheduler logic, running tests locally.
- Publish a changelog that tracks refactor milestones and highlights untouched business logic.

## 11. Phased Execution Timeline
1. **Phase 0 – Audit (1-2 days)**: complete Section 3 tasks, capture baseline outputs.
2. **Phase 0.5 – Cleanup & Archival (1-2 days)**: execute Section 4, remove/archive obsolete assets, and document dependency findings.
3. **Phase 1 – Documentation & Naming (2-3 days)**: update README/manifest, create package scaffolding without moving code yet.
4. **Phase 2 – Module Moves (4-6 days)**: reorganize files into new packages, adjust imports, ensure tests/smoke scripts pass after each move.
5. **Phase 3 – Automation Facade (4 days)**: consolidate browser pools and executors, introduce configuration objects, keep behaviours identical.
6. **Phase 4 – Domain Services (4-5 days)**: wrap queue/scheduler/orchestrator in service layer, add dataclasses, update handlers to use new interfaces.
7. **Phase 5 – Testing Tooling (3 days)**: stand up pytest, create core unit tests, wire CI jobs.
8. **Phase 6 – Polish (2 days)**: finalize docs, verify CI, remove deprecated modules/backups, confirm regression outputs match baseline.

## 12. Acceptance Criteria
- All existing commands, booking flows, and diagnostic scripts work exactly as before (validated against Phase 0 artifacts).
- Codebase has no orphaned `.backup` files or duplicate executors.
- Imports follow the new package structure with clear ownership boundaries.
- Automated test suite and linting pass locally and in CI.
- Documentation accurately reflects the reorganized architecture and onboarding steps.
