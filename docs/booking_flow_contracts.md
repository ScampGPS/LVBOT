# Booking Flow Contracts

## Overview

The shared contracts defined in `automation/shared/booking_contracts.py` govern data exchange across:

1. **Bot immediate bookings** – Telegram callbacks trigger request creation and executor dispatch.
2. **Queued reservations** – Scheduler promotes queued jobs into live bookings using the same request shape.
3. **Automation executors** – Working/experienced/smart flows consume requests and emit results with consistent metadata.
4. **Persistence and notifications** – Success/failure handlers operate on `BookingResult` instances regardless of origin.
5. **Browser health and recovery** – Diagnostics attach request/result metadata for observability.

## Lifecycle

1. **Trigger**
   - Source (bot callback, scheduler tick, tennis automation) passes contextual payloads to the appropriate request builder.
   - Builders assemble `BookingUser`, `CourtPreference`, and `BookingRequest` objects, applying validation (non-empty courts, valid email/phone, time format `HH:MM`).

2. **Execution**
   - Executors receive `BookingRequest`, select the appropriate flow module, and perform booking steps.
   - Execution metadata (browser id, attempt count, timing) is merged into the request metadata before results are returned.

3. **Result Creation**
   - Flow modules produce `BookingResult` via `BookingResult.success_result` or `BookingResult.failure_result`.
   - Confirmation details, screenshots, or error codes populate metadata for downstream consumers.

4. **Post-processing**
   - Persistence helpers store outcomes: immediate bookings update trackers, queued bookings modify reservation records.
   - Notification helpers format messages using `BookingResult` properties.
   - Browser health/recovery modules evaluate metadata to determine next actions.

5. **Telemetry**
   - Monitoring systems ingest serialized `BookingResult` objects (converted to dicts in persistence/notification layers).
   - Metadata keys align with the mapping doc: `target_date`, `target_time`, `executor`, `browser_id`, etc.

## Contract Guarantees

- `BookingRequest.target_date` is a `datetime.date` (UTC context) and `target_time` uses 24h `HH:MM` format.
- `BookingRequest.court_preference.as_list()` always returns at least one court number.
- `BookingResult.user` echoes the `BookingUser` from the originating request.
- `BookingResult.status` determines notification tone and persistence path; failure results must include at least one entry in `errors` or a `message`.
- Metadata dictionaries must be JSON-serializable to enable storage in existing JSON-based repositories.

## Integration Tasks

- Update unit tests to construct `BookingRequest` via builders rather than ad-hoc dicts.
- Provide adapters that convert legacy executor `ExecutionResult` objects into `BookingResult` until flows are refactored.
- Ensure scheduler and immediate handler share persistence helpers to avoid divergence between immediate vs. queued success recording.
- Document any additional metadata keys in this file to keep analytics dashboards accurate.
