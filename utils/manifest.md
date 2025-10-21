# utils Manifest

## Purpose
Shared utility modules that bridge legacy implementations with the refactored architecture. Many helpers are gradually migrating into domain-specific packages.

## Files
- `README.md`: Context on legacy helpers and migration plans.
- `acuity_booking_form.py` / `acuity_page_validator.py`: Legacy form helpers retained for compatibility; new flows should prefer `automation/forms` equivalents.
- `callback_parser.py`: Parses Telegram callback payloads for older handler implementations.
- `constants.py`: Miscellaneous constants shared across legacy modules.
- `db_helpers.py`: Utility functions for lightweight persistence tasks.
- `error_handler.py`: Fallback error handling for modules that predate `botapp/error_handler.py`.
- `message_handlers.py`: Legacy message routing helpers (superseded by `botapp/messages`).
- `state_manager.py`: Simplified state management abstraction used by historical flows.
- `telegram_ui.py`: UI helpers now largely replaced by components in `botapp/ui`.
- `tennis_config.py`: Configuration shim used by legacy scripts.
- `user_manager.py`: Older user management that has since moved to `users/`; kept for backward compatibility.
- `validation.py`: Shared validation utilities awaiting migration into feature-specific packages.

## Operational Notes
- Prefer newer modules when duplications exist; mark any remaining usages so they can be retired during refactor follow-ups.
- When migrating functionality out, update this manifest to reflect the new source of truth.
