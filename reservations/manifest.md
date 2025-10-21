# reservations Manifest

## Purpose
Domain layer for reservation data models, queue orchestration, and scheduling services. Interfaces between user requests and the automation executors.

## Subpackages
- `models/`: Dataclasses representing reservations and individual time slots.
- `queue/`: Queue persistence, repository helpers, scheduler pipeline, and validation logic. Includes `scheduler/` with dispatch, metrics, and lifecycle controls.
- `services/`: High-level reservation service that coordinates queue operations and automation hand-off.

## Notable Files
- `queue/reservation_queue.py`: Core queue that enqueues booking requests and exposes scheduling hooks.
- `queue/reservation_scheduler.py`: Drives the scheduling pipeline and interacts with browser pools.
- `queue/reservation_transitions.py`: State machine transitions for reservation lifecycle.
- `services/reservation_service.py`: Facade used by the bot to submit, cancel, and track reservations.

## Operational Notes
- Queue modules depend on Playwright resources supplied by `automation.browser`; ensure those pools are initialized before scheduling.
- The queue/scheduler respects the runtime test-mode config (fast execution and within-48h allowances) exposed via `infrastructure.settings.get_test_mode`.
- Changes to model schemas should be mirrored in `data/*.json` and documented in migration notes.
