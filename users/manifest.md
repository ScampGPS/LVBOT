# users Manifest

## Purpose
User management helpers for authorization, tiering, and persistence integration with the bot layer.

## Files
- `manager.py`: `UserManager` implementation that loads users from `data/users.json`, enforces admin privileges, and exposes tier utilities.
- `__init__.py`: Package exports for downstream imports.

## Operational Notes
- Keep `UserManager` in sync with the JSON schema stored under `data/`.
- Any additional user services should live here to keep authorization logic centralized.
