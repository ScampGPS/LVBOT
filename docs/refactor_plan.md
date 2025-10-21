# Callback Handler Refactor Plan

## Current State
The Telegram callback layer (`botapp/handlers/callback_handlers.py`) is a 3,500+ line class that handles every inline button the bot exposes. It mixes routing, state mutation, UI composition, and domain orchestration inside a single `CallbackHandler`. Even though per-feature route builders exist in `botapp/handlers/{booking,queue,profile,admin}/router.py`, all callbacks still funnel through one massive `handle_callback` method with dozens of `if startswith(...)` blocks. Conversational state lives in raw `context.user_data` keys such as `queue_booking_date`, `name_input`, or `modifying_option`, making flows brittle and hard to test.

## Refactor Objectives
- Make callback routing declarative and easy to extend.
- Separate booking, queue, profile, and admin flows into focused handler classes with explicit dependencies.
- Encapsulate per-flow conversation state in typed structures instead of loose `user_data` keys.
- Centralize message formatting and keyboard composition so UI fragments are reusable.
- Align callback logic with the new configuration and dependency container introduced during the main bot refactor.
- Modernize the testing harness so callback modules have dedicated unit/async tests that run with the project’s pytest configuration.

## Proposed Approach
1. **Declarative Router**
   - Introduce a `CallbackRouter` that supports exact and prefix routes, replacing the large `if`/`startswith` ladder in `handle_callback`.
   - Keep route definitions inside the existing `build_routes()` helpers, but have them register `CallbackRoute` objects (token/pattern, handler, optional guard).
   - Provide a single place to handle unknown callbacks and telemetry.

2. **Flow-Specific Handler Classes**
   - Break the monolithic `CallbackHandler` into focused classes, e.g.:
     - `BookingMenuHandler` – reserve/playback menus, availability checks.
     - `QueueBookingHandler` – queue-specific date/time/court flows.
     - `ProfileHandler` – profile editing, keypad inputs, validation.
     - `AdminHandler` – admin dashboards, test-mode toggles.
   - Each class receives only the dependencies it actually needs (availability checker, reservation queue, user manager, notifications, etc.) from the `DependencyContainer`.
   - The router composes these classes and exposes a thin `CallbackDispatcher` object to Telegram.

3. **Typed Conversation State**
   - Define small dataclasses (e.g., `QueueBookingState`, `ProfileEditState`) that capture the fields currently stored in `context.user_data`.
   - Add helpers to read/write these dataclasses from `context.user_data`, wrapping serialization details and reducing key-name drift.
   - Update handlers to depend on these helpers rather than touching `user_data` directly.

4. **Reusable UI Helpers**
   - Extract repeated message/keyboard assembly (queue summaries, profile prompts, admin lists) into dedicated functions under `botapp/ui/`.
   - Handlers then call a single `render_*` helper and send the returned `(text, keyboard)` tuple, improving readability and consistency.

5. **Config-Driven Behaviour**
   - Remove module-level globals such as `PRODUCTION_MODE`. Read toggles from the injected config (`BotAppConfig`) or the test-mode helpers in `infrastructure/settings`.
   - Ensure admin handlers that mutate test mode (`_handle_admin_toggle_test_mode`) use the DI-friendly path.

6. **Testing & Non-Functional Updates**
   - Add unit/async tests per handler class (queue flow state transitions, profile edits, booking confirmation, etc.).
   - Extend the pytest harness (fixtures, async helpers, project configuration) so callback tests run in isolation with fake updates/context.
   - Document the new structure in README and `docs/refactor_roadmap.md`, highlighting how to register new callbacks or extend flows.

## Deliverables
- New router and handler classes under `botapp/handlers/` that replace the monolithic `CallbackHandler`.
- Updated dependency container wiring to provide handler instances to the router.
- State helper utilities and UI formatting functions extracted from the legacy class.
- Expanded test harness + unit tests covering the refactored flows.
- Documentation updates summarizing the new callback architecture.

Implementing these steps will turn the callback layer into modular, testable pieces that match the professionalism and maintainability of the newly refactored bot runtime.
