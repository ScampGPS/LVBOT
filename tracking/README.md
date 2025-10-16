# Tracking Utilities

This package centralises the tooling that records which functions execute in production.

## Runtime logging
- Import the runtime helper with `from tracking import t` and call `t('qualified.name')` inside a function.
- The helper stores unique entries in `tracking/functions_in_use.txt`, using a lock to avoid duplicate writes.
- On import the helper merges any legacy entries from `logs/functions_in_use.txt` so previously captured data is preserved.

## AST instrumentation
- `tracking/instrument.py` rewrites Python files to insert `from tracking import t` and a `t('module.qualname')` call as the first executable line of every function.
- Run it from the project root via `python3 -m tracking.instrument`. Re-running is idempotent; files that are already instrumented are skipped.
- The script ignores the `tracking/` package itself and any file that fails to parse.

## Output data
- `functions_in_use.txt` grows over time as new functions execute. The file uses plain text, one fully qualified function name per line, to keep downstream processing simple.

## Function inventory
- `tracking/inventory.py` collects every function definition (matching the instrumentation qualifiers) and writes them to `tracking/all_functions.txt`, overwriting that file on each run.
- Run it with `python3 -m tracking.inventory`. Use the output to compare against `functions_in_use.txt` for coverage analysis.
