# Repository Structure (2025 cleanup)

- `automation/`: Browser automation stack covering availability parsing, executors, forms, and shared types.
- `botapp/`: Telegram bot runtime with handlers, commands, messaging, and bootstrap wiring.
- `reservations/`: Reservation models, queue orchestration, and scheduler services.
- `users/`: User management, tier logic, and related helpers.
- `infrastructure/`: Shared configuration, persistence utilities, and logging setup.
- `monitoring/`: Background monitors for court availability and system health.
- `tracking/`: Instrumentation layer that records runtime metrics and usage inventory.
- `utils/`: Legacy shims maintained until migration tasks in `docs/refactor_plan.md` complete.
- `config/`, `data/`, `logs/`: Environment templates, persisted JSON state, and runtime log output.
- `docs/`: Architecture notes, roadmaps, and refactor plans.
- `scripts/`: Operational scripts and local tooling.
- `tests/`: Unit and integration test suites.
- `run_bot.py`: CLI entrypoint for launching the Telegram bot.
- `manifest.md`: Top-level manifest summarising repository contents.
