# LVBot Manifest

## Purpose
This document explains the repository's top-level files and points to detailed manifests for each source directory, helping contributors navigate the codebase quickly.

## Top-Level Files
- `README.md`: Project overview, refactor context, and setup instructions for the tennis reservation bot.
- `run_bot.py`: Minimal entry point that launches the async Telegram bot defined in `botapp/app.py`.
- `requirements.txt`: Locked Python dependencies covering Telegram, Playwright automation, time handling, and test tooling.
- `pytest.ini`: Pytest defaults that scope unit tests to `tests/unit` and relax deprecation warnings during runs.
- `.flake8`: Linting preferences used when running Flake8 locally or in CI.
- `.gitignore`: Git ignore rules for caches, logs, virtual environments, and environment files.
- `manifest.md`: Root inventory of files plus links to per-directory manifests (this document).

## Directory Manifests
- `automation/manifest.md`: Playwright automation stack including browser pools, availability parsing, and booking flows.
- `botapp/manifest.md`: Telegram bot application modules for handlers, UI, state, and bootstrap wiring.
- `config/manifest.md`: Environment configuration templates and notes about secrets management.
- `data/manifest.md`: JSON persistence stores for users, queue state, and reservation snapshots.
- `docs/manifest.md`: Living documentation, guides, and architectural plans.
- `infrastructure/manifest.md`: Shared infrastructure helpers for logging, settings, and database access.
- `logs/manifest.md`: Runtime log directory usage and retention expectations.
- `monitoring/manifest.md`: Monitoring jobs that track availability and court performance.
- `reservations/manifest.md`: Domain models, queue coordination, and scheduler orchestration.
- `scripts/manifest.md`: Maintenance and operational scripts for developers and operators.
- `tests/manifest.md`: Unit test layout covering automation, queue logic, and schedulers.
- `tracking/manifest.md`: Instrumentation helpers and the function inventory used for observability.
- `users/manifest.md`: User management helpers and authorization logic.
- `utils/manifest.md`: Shared utilities bridging legacy and new architecture components.

## Operational Notes
- Runtime artifacts live in `logs/` and `automation/logs/`; both directories stay in Git via explicit allowlists so documentation remains versioned.
- Python cache directories (`__pycache__/`) and pytest caches are generated during execution; they remain untracked and do not carry manifests because contents are ephemeral.
- Tooling directories such as `.claude/`, `.venv/`, and `.pytest_cache/` are local-only and intentionally excluded from per-directory manifests.
