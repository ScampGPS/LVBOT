# Refactor Roadmap: Readable Orchestration & Size Limits

## Objectives
- Make orchestrators read like English: e.g. `book_time_slot(time, type)` with clear helper calls.
- Keep files (~<=500 lines) and functions (~<=50 lines) within intentional limits.
- Preserve behaviour while preparing for stricter linting/testing later.

## Key Targets
- `botapp/booking/immediate_handler.py` — shrink `_execute_booking` into helper-driven flow.
- `automation/executors/booking.py` — split working/experienced/smart flows and break up monolithic methods (e.g. `_execute_booking_internal`).
- Secondary large files (`botapp/app.py`, browser pool, scheduler) once booking flow is clean.

## Approach
1. **Define helper granularity**
   - Create value objects (`BookingRequest`, `BookingResult`).
   - Helpers: `fetch_user_profile`, `build_booking_request`, `attempt_natural_flow`, `attempt_fallback_flow`, `persist_success`, `send_success_message`, `send_failure_message`.
   - Executor helpers: `locate_time_button`, `humanize_before_click`, `fill_booking_form_with_user`, `submit_booking_form`, `wait_for_confirmation`.
2. **Refactor orchestrators**
   - Immediate handler: orchestrate helper calls; reduce to ~30 lines.
   - Executors: expose `book_time_slot(request)` as English-like entry point.
3. **Module split**
   - Break `automation/executors/booking.py` into focused modules (`working_flow.py`, `experienced_flow.py`, `smart_flow.py`, shared helpers).
   - Extract bot wiring from `botapp/app.py` once booking flow is done.
4. **Logging & error handling**
   - Keep granular logging inside helpers; top-level functions log state transitions only.
5. **Add guardrails**
   - After refactor, add lint/CI checks for max file/function size.
6. **Testing plan**
   - Maintain existing archive tests; add unit tests for new helper functions.
   - Run targeted Playwright smoke tests after major slices.

## Execution Order
1. Finish current “make it work” tasks.
2. Refactor immediate booking handler.
3. Reshape working executor and related helpers.
4. Split executor module and adjust imports.
5. Apply limits/linting and update remaining large files.

## Notes
- Refactor incrementally to avoid breaking automation.
- Document helper responsibilities during implementation for easier onboarding.
