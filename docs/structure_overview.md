# Repository Layout Overview (August 2025 Cleanup)

- `docs/`
  - `plans/`: Roadmaps and refactor plans (`LVBOT_REFACTOR_PLAN.md`, `REFACTORING_PLAN.md`, `MANIFEST.md`).
  - `reports/`: Historical performance analyses, fix summaries, and investigation write-ups.
  - `guides/`: How-to documents and operational guides.
  - `archive/`: Legacy notes that are kept for record but not part of the active workflow.
- `lvbot/`
  - `bot/`: Telegram entrypoint and related orchestration code (`telegram_tennis_bot.py`).
  - `handlers/`: Callback and command handlers imported by the bot layer.
  - `utils/`: Browser automation, scheduling, and support utilities (reachable via `lvbot.utils.*`).
  - `automation/`, `monitoring/`, `agents/`, `models/`, `experiments/`: Task-specific modules relocated from the root for clearer ownership.
- `scripts/`
  - `analysis/`: Playwright analysis helpers and DOM inspection scripts.
  - `diagnostics/`: Debugging utilities, log viewers, and sanity checks.
  - `maintenance/`: One-off fix/cleanup scripts and exploratory workflows.
  - `monitoring/`: Slot monitoring and availability probes.
  - `playwright/`: Capture/check scripts tightly coupled to the browser stack.
- `testing/`
  - `tests/`: All runnable test scripts, including the prior root-level `test_*.py` and `test_investigations/` utilities.
  - `logs/`: Collected log artifacts; `archive/` holds the previous `logs/` tree; new runs write to `testing/logs`.
  - `screencaps/`: All screenshot folders and single images captured during test/debug sessions.
  - `artifacts/`: JSON/HTML outputs and other structured test evidence.
  - `reports/`: Markdown reports generated from test runs.
  - `tools/`: Helper scripts used by tests for selector or page analysis.
- `data/`, `queue.json`, `users.json`: Runtime data files kept at project root for compatibility.
- `requirements.txt`: Python dependencies (unchanged).

All previous stray log/test artifacts are now under `testing/`, documentation is centralized in `docs/`, and the application code lives under `lvbot/` so the project root stays focused on configuration and top-level workflows.
