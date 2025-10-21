# botapp Manifest

## Purpose
Telegram application layer. Wires the async bot, registers command/handler routers, and adapts reservation automation outputs into chat-friendly messages and menus.

## Subpackages
- `booking/`: Build immediate booking requests, persist user choices, and interface with the reservation queue.
- `bootstrap/`: Factories that create browser pools and reservation components used by `CleanBot`.
- `callbacks/`: Parse Telegram callback data into typed actions for menu navigation.
- `commands/`: Command registration and wiring for `/start`, `/stop`, and other bot commands.
- `handlers/`: Conversation handlers split by domain (`admin/`, `booking/`, `profile/`, `queue/`) plus shared callback routing.
- `messages/`: Template and dispatch helpers for outbound Telegram messages.
- `state/`: Simple state manager abstractions for chat sessions.
- `ui/`: Menu builders and inline keyboards rendered in Telegram, including admin/booking flows.

## Notable Files
- `app.py`: Async entry point (`CleanBot`) that composes browser resources, reservation services, and handler registration.
- `error_handler.py`: Centralised error capture hooked into the Telegram dispatcher.
- `notifications.py`: Sends out-of-band confirmations with the latest menu attached.
- `validation.py`: User input validation helpers shared across handlers.

## Operational Notes
- Modules rely on `users.manager.UserManager` for authorization decisions.
- Update handler registration lives in `commands/register_core_handlers`; when adding features, extend routers rather than modifying `app.py` directly.
- The admin panel now includes a "Test Mode" toggle that flips the runtime configuration exposed via `infrastructure.settings.update_test_mode`.
