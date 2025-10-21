# automation Manifest

## Purpose
Core Playwright automation logic. Modules here drive browser orchestration, scrape availability from the booking portal, and execute booking flows on behalf of the Telegram bot.

## Subpackages
- `availability/`: Parses booking calendars (`api.py`, `checker.py`) and normalises extracted DOM content into dated time-slot maps.
- `browser/`: Builds and manages browser pools, lifecycle helpers, and health checks (`async_browser_pool.py`, `manager.py`, `health/`).
- `executors/`: High-level booking coordinators that choose flows, build requests, and sequence interactions (`booking.py`, `flows/`, `priority_manager.py`).
- `forms/`: Typed form interactions and validators used to fill Acuity pages safely (`actions.py`, `fields.py`).
- `logs/`: Automation-facing diagnostics such as screenshot captures for troubleshooting.
- `shared/`: Canonical booking contract definitions shared across automation and reservation layers.

## Notable Files
- `__init__.py`: Exposes package-level helpers for consumers.
- `availability/time_grouping.py`: Groups raw Playwright button elements into chronological orderings.
- `browser/browser_health_checker.py`: Evaluates browser readiness before a booking flow begins.
- `browser/lifecycle.py`: Shared shutdown helpers that close browser pools and tear down lingering Playwright processes.
- `executors/booking_orchestrator.py`: Entry point that wires availability, request building, and flow execution.
- `forms/acuity_booking_form.py`: Form object encapsulating field selectors and submission helpers.

## Operational Notes
- Modules expect Playwright to be installed and rely on shared telemetry via `tracking.t` calls.
- Screenshot directories can grow quickly; clean them after debugging to keep the repo lean.
