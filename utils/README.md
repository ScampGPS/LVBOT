# Tennis Bot Helper Modules

This directory contains modular helper functions to make the Tennis Bot code more maintainable and DRY.

## Modules

### 📅 `datetime_helpers.py`
Date and time utilities for the bot.
- Format dates for display
- Calculate time differences
- Check booking windows
- Parse reservation dates/times
- Get day labels (Today, Tomorrow, etc.)

### 🎨 `telegram_ui.py`
Telegram UI components and formatters.
- Create keyboards (main menu, date selection, etc.)
- Format messages (profiles, confirmations, errors)
- Pagination helpers
- Standard UI patterns

### ✅ `validation.py`
Input validation for user data.
- Phone number validation
- Email validation
- Time slot validation
- Court selection validation
- Date range validation

### 💾 `db_helpers.py`
Database operation helpers.
- Get or create user profiles
- Update user fields
- Search users
- Get reservation statistics
- Export user data (GDPR)

### 🌐 `browser_helpers.py`
Browser automation utilities.
- Wait for elements safely
- Click elements with retry
- Fill forms
- Handle iframes
- Extract page data

### 🎾 `reservation_helpers.py`
Reservation-specific logic.
- Create tennis configs
- Calculate retry delays
- Format court assignments
- Check conflicts
- Priority calculations

### 💬 `message_handlers.py`
Common message handling patterns.
- Handle unauthorized users
- Send loading messages
- Edit or reply intelligently
- Rate limiting
- Error messages

### 🔄 `state_manager.py`
Conversation state management.
- Track user states
- Store temporary data
- Handle timeouts
- State transitions
- Conversation flows

## Usage Example

```python
from utils.datetime_helpers import DateTimeHelpers
from utils.telegram_ui import TelegramUI
from utils.validation import ValidationHelpers
from utils.message_handlers import MessageHandlers

# Format a date
formatted = DateTimeHelpers.format_date_for_display(datetime.now())

# Create main menu
keyboard = TelegramUI.create_main_menu_keyboard(is_admin=True, pending_count=5)

# Validate phone number
is_valid, phone = ValidationHelpers.validate_phone_number("12345678")

# Handle unauthorized user
await MessageHandlers.handle_unauthorized_user(update)
```

## Benefits

1. **DRY Code**: No more duplicate logic
2. **Testable**: Each helper can be unit tested
3. **Maintainable**: Changes isolated to modules
4. **Readable**: Clear function names and purposes
5. **Reusable**: Can be used in other bots

## Adding New Helpers

When adding new helper functions:
1. Keep functions focused and single-purpose
2. Add docstrings with examples
3. Handle errors gracefully
4. Return consistent types
5. Consider adding unit tests