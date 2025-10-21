# tracking Manifest

## Purpose
Instrumentation framework that provides lightweight tracing and function inventory for observability across the bot and automation layers.

## Files
- `instrument.py`: Decorators and helpers for tagging code paths (`tracking.t`).
- `runtime.py`: Runtime hooks that persist tracking events or toggle instrumentation behaviour.
- `inventory.py`: Maintains the catalogue of trackable functions and their metadata.
- `all_functions.txt`: Generated list of every instrumented function.
- `function_call_counts.json`: Aggregated invocation counters persisted by the runtime helper.
- `README.md`: Usage guide for enabling, updating, and auditing tracking coverage.

## Operational Notes
- Update `all_functions.txt` via the provided tooling; the runtime helper owns `function_call_counts.json`, so avoid manual edits to keep diffs meaningful.
- When adding new instrumentation, document intent in the README and reference the consuming subsystem (bot, automation, reservations, etc.).
