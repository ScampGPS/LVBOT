# Callback Handler Refactor Summary

The callback dispatcher has been modularised and now routes through dedicated handlers.

- Introduced a `CallbackRouter` to declaratively map callback data to async handlers, with support for exact, prefix, and predicate routes.
- Extracted domain-specific handlers:
  - `botapp/handlers/booking/handler.py` for booking menus, availability, and date navigation.
  - `botapp/handlers/queue/handler.py` for queue flows and reservation management.
  - `botapp/handlers/profile/handler.py` for profile editing and keypad interactions.
  - `botapp/handlers/admin/handler.py` for admin panels and test-mode toggles.
- Added `CallbackDependencies` and `CallbackSessionState` helpers so handlers receive explicit dependencies and typed session state.
- Simplified `CallbackHandler` to orchestrate dependency wiring, instantiate domain handlers, and delegate via the router.
- Retired the legacy `build_routes` helpers and legacy monolithic logic.
- All unit tests (`py -m pytest`) pass, validating the refactor.

Future follow-ups can further expand the typed state usage inside domain handlers and grow targeted test coverage.
