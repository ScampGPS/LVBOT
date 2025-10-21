# docs Manifest

## Purpose
Central documentation hub capturing architecture decisions, migration plans, and operator guides.

## Top-Level Files
- `MANIFEST.md`: Legacy document that predates the repo-wide manifest initiative; keep until references are updated.
- `booking_contract_mapping.md`: Maps booking request inputs to downstream automation expectations.
- `booking_flow_contracts.md`: Defines invariants for each booking execution flow.
- `refactor_roadmap.md`: High-level milestones for the ongoing architecture refactor.
- `structure_overview.md`: Snapshot of repository layout (update alongside manifest changes).

## Subdirectories
- `guides/`: Operational and support guides (debugging tools, reservation walkthroughs, success documentation).
- `plans/`: In-flight planning documents including `LVBOT_REFACTOR_PLAN.md` and a manifest for migration tasks.

## Operational Notes
- When adding new documentation, update this manifest with a one-line summary so contributors can find the material quickly.
- Keep architectural docs aligned with code; stale diagrams or descriptions should be flagged during reviews.
