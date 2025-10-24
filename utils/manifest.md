# utils Manifest

## Purpose
Shared utility modules that bridge legacy implementations with the refactored architecture. Many helpers are gradually migrating into domain-specific packages.

## Files
- `README.md`: Context on legacy helpers and migration plans.
- `constants.py`: Miscellaneous constants shared across legacy modules.
- `db_helpers.py`: Utility functions for lightweight persistence tasks.
- `user_manager.py`: Older user management shim kept for backward compatibility during migration.

## Operational Notes
- Prefer the refactored modules under `botapp/` and `automation/` when duplicates exist. The remaining files exist solely for external backwards compatibility.
- If no downstream consumers rely on these shims, remove them and note the change here.
