# scripts Manifest

## Purpose
Operational utilities and developer scripts that complement the main bot workflow.

## Files
- `tools.py`: Assorted CLI helpers for inspecting queue state, seeding data, and running maintenance tasks. Review docstrings within the file before use.

## Operational Notes
- Scripts assume the project root is on `PYTHONPATH`; run them via `python -m scripts.tools ...` to ensure imports resolve.
- Add new scripts thoughtfully—prefer enriching existing CLIs to avoid a proliferation of one-off files.
