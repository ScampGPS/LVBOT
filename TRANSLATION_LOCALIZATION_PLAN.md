# Localization Centralization Plan

## Goals
- Ensure every user-facing string passes through the translation system.
- Remove hard-coded English button labels and texts across booking, queue, and admin flows.
- Provide reusable helpers so handlers only supply translation keys + params.

## Current Pain Points
- Inline `InlineKeyboardButton` constructions in handlers frequently embed English strings.
- There is no uniform helper for "Back"/"Main Menu" buttons; each handler builds its own variant.
- Date/time/court descriptions rely on English-specific formatting ("th" suffixes, "Court" prefix).

## Action Plan (Quick Pass)
1. **Navigation Helpers**
   - Add `TelegramUI.create_nav_buttons(language, back_target)` that wraps common back/main menu buttons.
   - Replace manual button creation in booking/admin/queue handlers.
2. **Message Templates**
   - Move recurring headers like "My Reservations", "Reservations for {user}" into `botapp/i18n/strings.py`.
   - Update `BookingUIFactory`, queue/admin flows to use translator keys instead of f-strings.
3. **Court/Date Formatting Helpers**
   - Create localized helper functions (e.g., `format_date_for_locale`, `format_court_list`) under `botapp/i18n/helpers` and replace the English-only logic scattered across handlers.
4. **Test Coverage**
   - Extend bot harness scenarios to assert Spanish users see translated strings.
   - Add unit tests around the new helper functions to prevent regressions.
5. **Queue & Error Messaging**
   - Consolidate queue prompts (time selection, confirmation, cancellation) into translator-driven helpers so handlers never embed English prose.
   - Update `ErrorHandler` and `format_error_message` to look up user language before emitting failures, ensuring consistency across flows.

> This document is a quick-cut blueprint; each bullet can be expanded into tasks as we proceed.
