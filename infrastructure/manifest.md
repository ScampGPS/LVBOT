# infrastructure Manifest

## Purpose
Shared infrastructure primitives used across automation and bot layers, including logging configuration, settings management, and database stubs.

## Files
- `constants.py`: Global infrastructure constants (paths, service identifiers).
- `db.py`: Lightweight database helpers and connection utilities used by reservation persistence layers.
- `logging_config.py`: Standard logging formatter and handler setup consumed on import.
- `settings.py`: Centralised runtime configuration loader that hydrates settings from environment variables.
- `__init__.py`: Exposes infrastructure helpers for straightforward imports.

## Subdirectories
- `logs/`: Mirrors the root log directory for infrastructure-specific log output; treated as runtime artifacts.

## Operational Notes
- Importing `logging_config` has side effects (handler registration); call it early in entry points.
- `settings.get_test_mode()` exposes runtime toggles for queue/testing behaviour and can be changed dynamically via `update_test_mode`.
- Keep settings definitions in sync with `config/.env.example` to avoid missing environment keys.
