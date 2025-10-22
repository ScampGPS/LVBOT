# Booking Contract Mapping

## Sources → BookingRequest Fields

| Source | Request Builder | Request ID | Source Enum | Courts | Target Date | Target Time | User Data | Metadata | Notes |
| --- | --- | --- | --- | --- | --- | --- | --- | --- | --- |
| Immediate booking confirmation (`ImmediateBookingHandler.handle_booking_confirmation`) | `botapp.booking.request_builder.build_immediate_booking_request` | `None` | `BookingSource.IMMEDIATE` | Single court from callback payload (`court_number`) | Callback payload (`date`) | Callback payload (`time`) | `BookingUser` built from `user_manager.get_user` | Telegram message context, executor hints | Requires profile validation before builder is invoked |
| Callback-driven admin overrides (future) | `botapp.booking.request_builder.build_admin_booking_request` (placeholder) | Provided override ID | `BookingSource.ADMIN` | Courts specified by admin payload | Provided | Provided | `BookingUser` derived from admin target | Audit metadata | Reserve for future admin panel wiring |
| Queue scheduler (`ReservationScheduler._execute_reservations`) | `reservations.queue.request_builder.build_request_from_reservation` | Reservation ID (`reservation['id']`) | `BookingSource.QUEUED` | Reservation courts (ordered) | Reservation `target_date` | Reservation `target_time` | `BookingUser` composed from reservation + user store | Queue position, retry counters | Builder ensures at least one court; falls back to defaults from config |
| Retry flows (future) | `automation.executors.request_factory.build_retry_request` (placeholder) | Previous request ID | `BookingSource.RETRY` | Courts from prior attempt metadata | Stored | Stored | Same `BookingUser` as original request | Error codes, retry count | Enables idempotent recovery after transient failures |

## BookingResult Consumers

| Consumer | Entry Point | Required Fields | Optional Fields | Usage |
| --- | --- | --- | --- | --- |
| Immediate booking handler | `botapp.notifications.send_success_notification` / `send_failure_notification` | `status`, `user`, `message` | `confirmation_code`, `confirmation_url` | Format Telegram messages |
| Reservation scheduler | `reservations.queue.persistence.persist_queue_outcome` | `status`, `request_id`, `metadata` | `errors`, `confirmation_code` | Update queue records and metrics |
| Executor diagnostics | `automation.browser.pool_health.summarise_pool_status` | `status`, `metadata` | `started_at`, `completed_at` | Log structured telemetry |
| Browser recovery | `automation.browser.recovery.strategies` | `status`, `errors` | `confirmation_url` | Trigger fallback vs recovery |
| Monitoring dashboards | `monitoring.*` | `status`, `user`, `target_time`, `target_date` (from metadata) | `message` | Display cross-system status |

## Metadata Conventions

- `metadata['target_date']` and `metadata['target_time']` MUST be populated for downstream analytics.
- Queue flows add `metadata['queue_position']`, `metadata['attempt']`.
- Executor flows append `metadata['executor']` and `metadata['flow']` to identify the strategy used.
- Browser health modules read `metadata['browser_id']` when correlating diagnostics.

## Transition Checklist

1. All builders populate `BookingRequest` without optional gaps.
2. Persisted queue records are augmented with serialized `BookingRequest` details for audit.
3. Unit tests validate builder output against existing fixtures.
4. Logging statements reference the new dataclass attributes (`request.user.user_id`, `request.target_time`, etc.).
5. Monitoring dashboards read from `BookingResult` objects only.
