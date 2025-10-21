# Tracking Utilities

This package centralises the tooling that records which functions execute in production.

## Runtime logging
- Import the runtime helper with `from tracking import t` and call `t('qualified.name')` inside a function.
- Each invocation increments a counter stored in `tracking/function_call_counts.json`, with updates written immediately under a lock to keep the file consistent.

## AST instrumentation
- `tracking/instrument.py` rewrites Python files to insert `from tracking import t` and a `t('module.qualname')` call as the first executable line of every function.
- Run it from the project root via `python3 -m tracking.instrument`. Re-running is idempotent; files that are already instrumented are skipped.
- The script ignores the `tracking/` package itself and any file that fails to parse.

## Output data
- `function_call_counts.json` records how often instrumented functions run. The file contains a JSON object with fully qualified function names mapped to integer invocation counts.

## Function inventory
- `tracking/inventory.py` collects every function definition (matching the instrumentation qualifiers) and writes them to `tracking/all_functions.txt`, overwriting that file on each run.
- Run it with `python3 -m tracking.inventory`. Use the output to compare against `function_call_counts.json` for coverage analysis.
