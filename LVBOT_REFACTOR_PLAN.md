# LVBot Refactor & Modularization Plan

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

## 4. Architecture Alignment
- **Module naming**: rename references to removed modules (`playwright_bot.py`, `browser_pool.py`, etc.) in README and docs; align them with `utils/async_browser_pool.py`, `utils/availability_checker_v3.py`, etc.
- **Package structure**: introduce top-level packages to separate concerns:
  - `bot/` (Telegram entrypoint, handlers, UI helpers)
  - `automation/` (browser pools, executors, availability parsing)
  - `domain/` (reservation queue, scheduler, priority logic)
  - `infrastructure/` (logging config, persistence helpers)
- Add `__init__.py` files and update imports to absolute package paths once the folders exist.

## 5. Browser & Automation Layer
- Extract configuration flags (headless/headful, warm-up delay, timeout profiles) from `utils/async_browser_pool.py` into a dedicated settings object so environments can override them without code edits.
- Collapse legacy variants (`async_booking_executor_backup.py`, `working_booking_executor.py`, `optimized_booking_executor.py`) into a single `automation/executors/async_executor.py` module retaining feature flags (`experienced_mode`, `natural_flow`). Mark experimental logic behind feature toggles instead of duplicate files.
- Ensure helper utilities (`async_browser_helpers`) expose a consistent async API; remove dead sync variants and wrap any remaining sync calls.
- Integrate browser health, recovery, and lifecycle helpers through a cohesive `BrowserManager` facade to avoid ad-hoc initialization in multiple modules.

## 6. Scheduler & Reservation Pipeline
- Move queue persistence, scheduler, orchestrator, and priority management under `domain/` with clear interfaces (`QueueRepository`, `SchedulerService`, `BookingOrchestrator`).
- Replace ad-hoc dictionaries passed between modules with lightweight dataclasses (e.g., `ReservationRequest`, `BookingAttempt`) defined in a shared `domain/models.py` without changing field semantics.
- Decouple scheduler start/stop from the Telegram application life cycle by introducing an application service layer; handlers call service methods instead of touching queue internals.
- Normalize retry/backoff logic across `ReservationScheduler`, `ReservationHelpers`, and executors so the same constants are reused.

## 7. Data & Configuration Hygiene
- Relocate JSON data files to `infra/data/` and wrap access behind repository classes to ease swapping storage later.
- Remove personally identifiable information from committed JSON fixtures; replace with sanitized seed data and document required fields.
- Centralize environment variable loading (e.g., via `python-dotenv` guard) in a single `settings.py` to avoid scattered `os.getenv` lookups.

## 8. Testing & Validation Improvements
- Introduce a `tests/unit` suite covering
  - `ReservationQueue` persistence semantics
  - Availability parsing (`AvailabilityCheckerV3`, `TimeSlotExtractor`)
  - Scheduler prioritization logic with mocked time.
- Add `tests/integration` scripts to exercise Telegram command handlers via `Application.run_polling` test harness or mocked dispatcher.
- Provide a minimal Playwright smoke test that runs headless in CI to verify browser pool bootstrap.
- Set up pytest configuration, type checking (mypy or pyright), and linting (ruff/flake8) with pre-commit hooks.

## 9. Documentation & Developer Experience
- Rewrite README’s architecture section to mirror the new package layout and remove outdated references.
- Generate module reference docs (Sphinx or mkdocs) once namespaces settle.
- Document standard workflows: adding a new handler, extending scheduler logic, running tests locally.
- Publish a changelog that tracks refactor milestones and highlights untouched business logic.

## 10. Phased Execution Timeline
1. **Phase 0 – Audit (1-2 days)**: complete Section 3 tasks, capture baseline outputs.
2. **Phase 1 – Documentation & Naming (2-3 days)**: update README/manifest, create package scaffolding without moving code yet.
3. **Phase 2 – Module Moves (4-6 days)**: reorganize files into new packages, adjust imports, ensure tests/smoke scripts pass after each move.
4. **Phase 3 – Automation Facade (4 days)**: consolidate browser pools and executors, introduce configuration objects, keep behaviours identical.
5. **Phase 4 – Domain Services (4-5 days)**: wrap queue/scheduler/orchestrator in service layer, add dataclasses, update handlers to use new interfaces.
6. **Phase 5 – Testing Tooling (3 days)**: stand up pytest, create core unit tests, wire CI jobs.
7. **Phase 6 – Polish (2 days)**: finalize docs, verify CI, remove deprecated modules/backups, confirm regression outputs match baseline.

## 11. Acceptance Criteria
- All existing commands, booking flows, and diagnostic scripts work exactly as before (validated against Phase 0 artifacts).
- Codebase has no orphaned `.backup` files or duplicate executors.
- Imports follow the new package structure with clear ownership boundaries.
- Automated test suite and linting pass locally and in CI.
- Documentation accurately reflects the reorganized architecture and onboarding steps.
