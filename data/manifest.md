# data Manifest

## Purpose
JSON persistence layer for lightweight storage of reservations, queue state, and user records. Files are read and written by the bot and reservation services.

## Files
- `authorized_users.json`: Source of truth for Telegram IDs allowed to use administrative features.
- `users.json`: User profile data (tier, preferences) consumed by `UserManager`.
- `queue.json`: Active reservation requests queued for scheduling.
- `all_reservations.json`: Historical snapshot of reservations captured for reporting and debugging.

## Operational Notes
- These files may contain sensitive user information; keep them out of public branches and scrub before sharing logs.
- Back up before performing migrations; schema changes should be documented in `docs/plans/` and accompanied by migration scripts if needed.
