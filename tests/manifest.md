# tests Manifest

## Purpose
Automated test suite verifying availability parsing, reservation queue logic, and scheduler behaviour.

## Structure
- `unit/`: Pytest-based unit tests covering availability utilities (`test_time_grouping.py`, `test_time_utils.py`), reservation queue components, scheduler dispatch/metrics, and form actions.

## Operational Notes
- Tests assume Playwright-dependent modules are stubbed; keep heavy browser tests out of the unit suite to maintain speed.
- Run with `pytest` from the repository root; configuration in `pytest.ini` sticks to this directory.
