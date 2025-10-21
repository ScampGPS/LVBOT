# tests Manifest

## Purpose
Automated test suite verifying availability parsing, reservation queue logic, and scheduler behaviour.

## Structure
- `unit/`: Pytest-based unit tests covering availability utilities (`test_time_grouping.py`, `test_time_utils.py`), reservation queue components, scheduler dispatch/metrics, and form actions.
- `bot/`: Headless harness and CLI scenarios for driving Telegram flows without a live bot instance.

## Operational Notes
- Tests assume Playwright-dependent modules are stubbed; keep heavy browser tests out of the unit suite to maintain speed.
- Run with `pytest` from the repository root; configuration in `pytest.ini` sticks to this directory.
- Execute conversational scenarios via `python -m tests.bot queue-booking` to exercise flows without Telegram.
- Toggle queue test behaviour with environment variables such as `TEST_MODE_ENABLED`, `TEST_MODE_ALLOW_WITHIN_48H`, `TEST_MODE_TRIGGER_DELAY_MINUTES`, and `TEST_MODE_RETAIN_FAILED`.
