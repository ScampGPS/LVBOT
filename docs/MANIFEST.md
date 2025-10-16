# LVBOT Code Manifest

## Recent Updates

### Browser Pool Recovery Service (2025-08-06)
- Created browser_pool_recovery.py for resilient recovery from browser failures
- Implements RecoveryStrategy enum (INDIVIDUAL_COURT, PARTIAL_POOL, FULL_RESTART, EMERGENCY_FALLBACK)
- RecoveryResult and RecoveryAttempt dataclasses for tracking recovery operations
- Escalating recovery strategies from least to most disruptive
- Individual court recovery: Close and recreate specific browser
- Partial pool recovery: Recreate only affected browsers with staggered starts
- Full pool restart: Complete pool recreation with state preservation
- Emergency fallback: Activate minimal backup browser system
- Thread-safe operations with recovery lock
- Recovery statistics tracking and history
- Integrated with AsyncBrowserPool for seamless recovery

### Browser Health Check System (2025-08-06)
- Created browser_health_checker.py for proactive browser pool health monitoring
- Implements HealthStatus enum (HEALTHY, DEGRADED, CRITICAL, FAILED)
- Comprehensive health checks: page connectivity, JavaScript execution, network access, DOM queries
- Pre-booking health validation to maximize booking success rates
- Individual court health monitoring with detailed diagnostics
- Response time tracking and health status caching
- Determines if browser pool requires restart based on failure patterns

### Emergency Browser Fallback System (2025-08-06)
- Created independent emergency_browser_fallback.py for last-resort bookings
- Operates completely independently of browser pool infrastructure
- Direct Playwright browser creation without pool dependencies
- Simple single-browser implementation for maximum reliability
- Integrated into reservation_scheduler.py as fallback when pool unavailable
- Used in both _execute_single_booking and _execute_fallback methods
- Ensures bookings can complete even during total browser pool failure

### Availability Checker Refactoring (2025-07-29)
- Created modular architecture for availability checking following DRY principles
- Added centralized COURT_CONFIG in constants.py with all court IDs and URLs
- Created consolidated support.py for DOM extraction and date helpers
- Introduced checker.py as single entry point for availability checks
- Flattened booking executors into booking.py/core.py/navigation.py/tennis.py for easier maintenance
- Updated async_browser_pool.py to use centralized COURT_CONFIG
- Deprecated availability_checker_v2.py and async_availability_checker.py
- Fixed availability detection using correct selectors (button.time-selection)

### Phase-Optimized Booking Performance (2025-07-29)
- Optimized key booking phases to reduce execution time by 30% (57s → 40s)
- Reduced mouse movements from 2-4 to 1-2 movements with 0.2-0.5s delays
- Reduced button approach delays from 1-2s to 0.3-0.5s
- Reduced after-click delay from 3-5s to 2-3s
- Reduced confirmation wait from 5s minimum to 3s minimum
- Maintained 100% booking success rate with no bot detection
- Optimizations now live under WorkingBookingExecutor in automation/executors/booking.py

### Experienced User Mode Implementation (2025-07-29)
- Added experienced_mode flag to AsyncBookingExecutor for faster bookings
- Created ExperiencedBookingExecutor with minimal delays (26.5s execution)
- Uses paste-like behavior for all form fields (consistent fast filling)
- Minimal initial delay (0.8-1.2s) and reduced waits throughout
- Achieves 34% faster bookings while avoiding bot detection
- **DEFAULT MODE**: Experienced mode is now enabled by default
- Usage: AsyncBookingExecutor(browser_pool) # Uses experienced mode
- For standard mode: AsyncBookingExecutor(browser_pool, experienced_mode=False)

### Smart Booking Executor Implementation (2025-07-24)
- Created SmartAsyncBookingExecutor with progressive timeout and retry logic
- Implements smart timeout: 15s base + up to 6x10s extensions based on loading progress
- Time-aware retry strategy: Immediate retries before target time, 2s delay after
- Up to 10 retry attempts with smart timing based on target booking time
- Monitors network activity and DOM changes to intelligently extend timeout
- Fixes issue where bookings were timing out after 60s without retry
- Added URL checking to refresh page if already on target datetime URL
- Added automatic navigation back to court page after booking attempts

### Browser Pool Loading Optimization (2025-07-24)
- Changed navigation strategy from 'networkidle' to 'domcontentloaded' for faster initialization
- Added specific wait for calendar elements ([class*="time"]) which appear around 24-25s
- Reduced initial page load timeout issues by not waiting for all network activity
- Based on loading sequence analysis showing networkidle takes 30+ seconds while DOM loads in ~7s

### Reservation Queue Logging Enhancement (2025-07-23)
- Added dedicated reservation_queue.log file for all queue operations
- Enhanced logging throughout ReservationQueue with detailed operation tracking
- Added comprehensive logging to BookingOrchestrator for priority decisions
- Enhanced PriorityManager logging to track user tier distribution and bumping
- Added detailed logging to ReservationScheduler for execution tracking
- Improved logging format with multiline messages for better readability
- Added logging for:
  - New reservation requests with full details
  - Time slot queries and results
  - Waitlist additions and promotions
  - Status updates with before/after states
  - Browser allocation decisions
  - VIP bumping events
  - Booking successes and failures
  - Cancellation handling

## utils/ Directory - Modular Helper Functions

### `optimized_browser_pool.py`
**Purpose**: Optimized browser pool with faster sequential initialization following DRY principles

#### Key Functions:
- `__init__(pool_size, headless)` → None
  Initialize optimized browser pool with performance enhancements
- `start()` → bool
  Start browser pool with optimized sequential initialization
- `_initialize_browsers_optimized()` → None
  Create browsers sequentially with performance optimizations
- `get_browser()` → Optional[Tuple[str, Page]]
  Get available browser from pool (thread-safe)
- `release_browser(browser_id)` → None
  Release browser back to pool for reuse
- `refresh_browser(browser_id)` → bool
  Refresh specific browser (main thread only)
- `get_stats()` → Dict[str, Any]
  Get pool statistics including initialization time

### `simple_browser_pool.py`
**Purpose**: Simple browser pool that maintains ready browsers without pre-positioning

#### Key Functions:
- `__init__(pool_size, headless)` → None
  Initialize simple browser pool
- `start()` → bool
  Start browser pool with sequential initialization
- `get_browser()` → Optional[Tuple[str, Page]]
  Get available browser from pool
- `release_browser(browser_id)` → None
  Release browser back to pool
- `refresh_browser(browser_id)` → bool
  Refresh specific browser (main thread only)

### `constants.py`
**Purpose**: Centralized constants and configuration values

#### Key Constants:
- `COURT_CONFIG`: Centralized court configuration with IDs and URLs
- `TIME_BUTTON_SELECTOR`: Primary selector for time buttons (button.time-selection)
- `TIME_SLOT_SELECTORS`: List of CSS selectors for time slot buttons
- `COURT_HOURS`: List of actual court operating hours (includes :15 evening slots)
- `BOOKING_WINDOW_HOURS`: 48-hour advance booking window
- `HARDCODED_VIP_USERS`: List of VIP user IDs
- `HARDCODED_ADMIN_USERS`: List of admin user IDs
- `BrowserTimeouts`: Timeout configurations for browser operations
- `COURT_BUTTON_SELECTORS`: CSS selectors for court buttons
- `NO_AVAILABILITY_PATTERNS`: Patterns for detecting no availability messages

### `datetime_helpers.py`
**Purpose**: Date and time utility functions for tennis court bookings

#### Key Functions:
- `is_within_booking_window(target_date, window_hours)` → bool
  Check if date is within booking window
- `get_next_available_date(preferred_time)` → datetime
  Calculate next available booking date
- `format_date_for_display(date)` → str
  Format date for user display

### `telegram_ui.py`
**Purpose**: Telegram UI utility functions for keyboard creation and message formatting

#### Key Functions:
- `create_main_menu_keyboard(is_admin, pending_count)` → InlineKeyboardMarkup
  Creates the main menu keyboard with optional admin panel
- `create_court_selection_keyboard(available_courts)` → ReplyKeyboardMarkup
  Creates court selection keyboard for regular booking flow
- `create_queue_court_selection_keyboard(available_courts)` → InlineKeyboardMarkup
  Creates inline court selection keyboard for queue booking flow
- `create_yes_no_keyboard()` → ReplyKeyboardMarkup
  Creates simple yes/no keyboard
- `create_cancel_keyboard()` → ReplyKeyboardMarkup
  Creates keyboard with only cancel option
- `create_queue_confirmation_keyboard()` → InlineKeyboardMarkup
  Creates inline confirmation keyboard for queue booking flow
- `format_user_tier_badge(tier_name)` → str
  Format user tier into emoji badge (👑/⭐/👤)
- `format_reservations_list(reservations)` → str
  Format reservation list with waitlist support

### `user_manager.py`
**Purpose**: User management system with persistent storage and tier support for priority queuing

#### Key Classes:
- `UserTier` - Enum for user tiers (ADMIN=0, VIP=1, REGULAR=2)

#### Key Functions:
- `get_user(user_id)` → Optional[Dict[str, Any]]
  Retrieve user profile by ID
- `save_user(user_profile)` → None
  Save or update user profile
- `is_admin(user_id)` → bool
  Check if user has admin privileges
- `is_vip(user_id)` → bool
  Check if user has VIP privileges
- `get_user_tier(user_id)` → UserTier
  Get user's tier level for priority system
- `set_user_tier(user_id, tier)` → None
  Set user's tier level

### `automation/executors/priority_manager.py`
**Purpose**: Priority management system handling two-tier FCFS user sorting

#### Key Classes:
- `PriorityUser` - User data for priority sorting

#### Key Functions:
- `sort_by_priority(users)` → List[PriorityUser]
  Sort users by tier then FCFS
- `split_into_tiers(users)` → Dict[UserTier, List[PriorityUser]]
  Split users by tier
- `get_user_position(target_user, all_users)` → int
  Get user's queue position
- `allocate_to_browsers(users, num_browsers)` → Tuple[List, List]
  Allocate users to browsers based on priority
- `handle_vip_bump(new_vip, current_users, num_browsers)` → Dict
  Handle VIP late entry with bumping

### `booking_orchestrator.py`
**Purpose**: Enhanced dynamic booking orchestrator with priority support and VIP handling

#### Key Classes:
- `BookingStatus` - Enum for booking states
- `BookingAttempt` - Track individual booking attempts

#### Key Functions:
- `create_booking_plan(reservations, time_slot, user_manager)` → Dict
  Create booking plan with priority-based allocation
- `handle_booking_result(reservation_id, success, court_booked)` → Optional[Dict]
  Handle results and determine fallbacks
- `handle_vip_late_entry(vip_user, current_confirmed, current_waitlist)` → Dict
  Handle VIP joining with bumping logic
- `get_booking_summary()` → Dict
  Get summary including bumped users
- `create_back_to_menu_keyboard()` → InlineKeyboardMarkup
  Creates standard 'Back to Menu' inline keyboard
- `create_date_selection_keyboard(dates)` → InlineKeyboardMarkup
  Creates date selection keyboard from list of (date_obj, label) tuples
- `create_time_selection_keyboard(available_times, selected_date, flow_type)` → InlineKeyboardMarkup
  Creates time selection keyboard with flow-specific callbacks
- `format_reservation_confirmation(reservation_details)` → str
  Formats reservation confirmation message
- `format_reservations_list(reservations)` → str
  Formats list of reservations into user-friendly message
- `format_error_message(error_type, details)` → str
  Formats standardized error messages
- `format_availability_message(available_times, date, show_summary)` → str
  Formats court availability message
- `format_user_profile_message(user_data, is_hardcoded)` → str
  Formats user profile display
- `format_queue_status_message(queue_items, timezone_str)` → str
  Formats queue status message
- `create_pagination_keyboard(current_page, total_pages, callback_prefix)` → List[InlineKeyboardButton]
  Creates pagination buttons for multi-page displays
- `format_loading_message(action)` → str
  Formats a loading message
- `create_admin_menu_keyboard(pending_count)` → InlineKeyboardMarkup
  Creates admin menu keyboard
- `create_court_availability_keyboard(available_times, selected_date, layout_type, available_dates)` → InlineKeyboardMarkup
  Creates interactive court availability keyboard with matrix/vertical layouts and day cycling
- `format_interactive_availability_message(available_times, date, total_slots, layout_type)` → str
  Formats court availability message for interactive booking UI (supports matrix layout)
- `_create_vertical_layout_keyboard(available_times, selected_date)` → InlineKeyboardMarkup
  Creates vertical layout keyboard (current implementation)
- `_create_matrix_layout_keyboard(available_times, selected_date, available_dates)` → InlineKeyboardMarkup
  Creates matrix layout keyboard with time rows and court columns
- `_build_time_matrix(available_times)` → Dict[str, Dict[int, bool]]
  Builds time matrix mapping time slots to court availability
- `_filter_empty_time_rows(time_matrix)` → Dict[str, Dict[int, bool]]
  Filters out time rows where no courts are available
- `_create_matrix_keyboard_rows(time_matrix, selected_date, all_courts)` → List[List]
  Creates keyboard rows from filtered time matrix
- `_get_day_label_for_date(date_str)` → str
  Gets day label for date string (Today, Tomorrow, or day name)
- `_get_next_day(current_date, available_dates)` → str
  Gets next available date for intelligent day cycling with edge case handling

### `utils/callback_parser.py`
**Purpose**: Modular callback data parser following DRY principles

#### Key Functions:
- `parse_booking_callback(callback_data)` → Optional[Dict[str, Any]]
  Parse immediate booking callback data (book_now, confirm_book, cancel_book)
- `parse_queue_callback(callback_data)` → Optional[Dict[str, Any]]
  Parse queue booking callback data (queue_time, queue_court)
- `format_booking_callback(action, date, court_number, time)` → str
  Format callback data for booking actions

### `utils/immediate_booking_handler.py`
**Purpose**: Handles immediate booking flow from court availability display

#### Key Functions:
- `__init__(user_manager)` → None
  Initialize handler with user management dependency
- `handle_booking_request(update, context)` → None
  Handle initial booking request when user clicks a time slot
- `handle_booking_confirmation(update, context)` → None
  Execute booking after user confirmation
- `handle_booking_cancellation(update, context)` → None
  Handle booking cancellation and return to availability view
- `_get_validated_user(user_id)` → Optional[Dict[str, Any]]
  Get and validate user data with required fields check
- `_create_confirmation_ui(booking_data, user_data)` → Dict[str, Any]
  Create confirmation dialog UI components
- `_execute_booking(user_id, booking_data)` → Dict[str, Any]
  Execute actual booking using smart executor
- `_format_success_message(result, booking_data)` → str
  Format successful booking message
- `_format_failure_message(result, booking_data)` → str
  Format booking failure message

### `utils/acuity_page_validator.py`
**Purpose**: Validates Acuity scheduling pages for extraction readiness

#### Key Functions:
- `is_page_ready_for_extraction(page, court_num)` → bool
  Check if page is ready for time extraction (allows natural redirects)
- `has_acuity_scheduling_structure(page)` → bool
  Detect if page has Acuity scheduling elements for time extraction
- `log_page_analysis(page, court_num)` → None
  Log detailed page analysis for debugging navigation issues
- `_is_acuity_domain(page)` → bool
  Check if page is on a valid Acuity domain (accepts redirect patterns)
- `_get_extraction_frame(page)` → Optional[Frame]
  Get appropriate frame for extraction (iframe or page itself)

### `validation.py`
**Purpose**: Input validation for user data and booking parameters

#### Key Functions:
- `validate_email(email)` → bool
  Validate email format
- `validate_phone(phone)` → bool
  Validate phone number format
- `validate_time_slot(time)` → bool
  Validate time slot format (HH:MM)

### `db_helpers.py`
**Purpose**: Database operations for user and reservation management

#### Key Functions:
- `get_user_by_id(user_id)` → Optional[User]
  Retrieve user from database
- `save_reservation(reservation)` → bool
  Save reservation to database
- `get_pending_reservations()` → List[Reservation]
  Get all pending reservations

### `browser_helpers.py`
**Purpose**: Browser automation utilities for Playwright

#### Key Functions:
- `wait_for_element(page, selector, timeout)` → Optional[ElementHandle]
  Wait for element with retry logic
- `safe_click(element)` → bool
  Click element with error handling
- `extract_text_content(element)` → str
  Safely extract text from element

### `sync_browser_helpers.py`
**Purpose**: Synchronous browser operations to maintain DRY principle

#### Key Functions:
- `get_scheduling_frame(page, timeout)` → Optional[Frame]
  Get scheduling iframe - single source of truth for sync frame access
- `navigate_to_court(page, court_number)` → bool
  Navigate to specific court with proper error handling
- `extract_available_times(frame)` → List[str]
  Extract available time slots from frame

### `reservation_helpers.py`
**Status**: Archived (`archive/legacy_modules/reservations_queue/reservation_helpers.py`)

Legacy retry and conflict-detection utilities retained for reference. The
current queue system no longer imports these helpers.

### `message_handlers.py`
**Purpose**: Message handling patterns for Telegram bot

#### Key Functions:
- `handle_command(command, context)` → str
  Process bot commands
- `handle_callback_query(query, context)` → None
  Handle inline keyboard callbacks
- `send_notification(user_id, message)` → bool
  Send notification to user

### `state_manager.py`
**Purpose**: Conversation state management for multi-step interactions

#### Key Functions:
- `get_user_state(user_id)` → Optional[str]
  Get current conversation state
- `set_user_state(user_id, state)` → None
  Update user conversation state
- `clear_user_state(user_id)` → None
  Clear user state data

### `availability_checker.py`
**Purpose**: Check court availability using browser pool or standalone browser

#### Key Functions:
- `check_all_courts(get_dates)` → Dict[str, Any]
  Check availability for all courts
- `_check_court_with_pool(court_number, get_dates)` → Optional[Dict]
  Check single court using browser pool
- `_check_court_with_simple_pool(court_number, get_dates)` → Optional[Dict]
  Handle SimpleBrowserPool without court_manager

### `availability/checker.py`
**Purpose**: Primary interface for Playwright-based court availability checks

#### Key Functions:
- `check_availability(court_numbers, max_concurrent, timeout_per_court)` → Dict[int, Dict[str, List[str]]]
  Collect availability grouped by date for each court
- `check_all_courts_parallel()` → Dict[int, List[str]]
  Backwards-compatible flattened availability result
- `get_next_available_slot(court_numbers, min_time, max_time)` → Optional[Tuple[int, date, str]]
  Return the earliest slot that matches the provided filters
- `format_availability_message(availability)` → str
  Build a user-facing summary of availability data

### `availability/support.py`
**Purpose**: Consolidated helpers for DOM extraction and date utilities

#### Key Components:
- `AcuityTimeParser.extract_times_by_day(frame)` → Dict[str, List[str]]
  Group DOM-ordered time buttons into day buckets with simple heuristics
- `filter_future_times_for_today(times, current_time)` → List[str]
  Remove already-expired slots from the current day
- `DateTimeHelpers.*`
  Shared formatting/parsing helpers used by Telegram handlers and executors

### `executors/booking.py`
**Purpose**: Central home for booking executors and helper routines

#### Key Classes:
- `WorkingBookingExecutor`
  Proven baseline flow used for consistent bookings
- `ExperiencedBookingExecutor`
  Faster variant with aggressive timing and pre-window refresh support
- `AsyncBookingExecutor`
  Orchestrates multi-court attempts and chooses the appropriate strategy
- `SmartAsyncBookingExecutor`
  Adds retry logic, timeout budgeting, and detailed diagnostics
- `UnifiedAsyncBookingExecutor`
  Facade that selects an executor based on `AsyncExecutorConfig`

### `executors/core.py`
**Purpose**: Shared dataclasses and config for executors

#### Key Items:
- `ExecutionResult`
  Unified result object consumed across executors and schedulers
- `AsyncExecutorConfig` / `DEFAULT_EXECUTOR_CONFIG`
  Feature toggles for executor selection

### `executors/navigation.py`
**Purpose**: Navigation helpers used by booking flows

#### Key Classes:
- `OptimizedNavigation`
  Progressive navigation strategies with fallback selection
- `ReliableNavigation`
  Event-driven navigation for scenarios where Playwright's `goto` hangs

### `executors/tennis.py`
**Purpose**: Tennis-specific executor facade and config helpers

#### Key Components:
- `TennisConfig` / `create_tennis_config_from_user_info`
  Normalized structure for user booking preferences
- `TennisExecutor`
  Routes bookings to pooled async execution or synchronous fallback

### `acuity_booking_form.py`
**Purpose**: Handle Acuity scheduling form filling and submission

#### Key Functions:
- `fill_form(page, user_info)` → bool
  Fill booking form with user information
- `submit_form(page)` → bool  
  Submit the booking form
- `check_booking_success(page)` → Tuple[bool, str]
  Check if booking was successful and extract confirmation details

### `availability_check_adapter.py`
**Purpose**: Adapter to unify availability checking interfaces

#### Key Functions:
- `check_availability_with_pool(browser_pool, get_dates)` → Dict[str, Any]
  Check availability using browser pool
- `check_availability_standalone(config, get_dates)` → ExecutionResult
  Check availability with standalone browser

### `browser_refresh_manager.py`
**Purpose**: Automatically refresh browsers to prevent memory leaks

#### Key Functions:
- `__init__(browser_pool, refresh_interval)` → None
  Initialize refresh manager with interval
- `start()` → None
  Start automatic refresh thread
- `stop()` → None
  Stop refresh manager
- `_refresh_loop()` → None
  Main refresh loop checking browser health

### `sequential_court_checker.py`
**Purpose**: Sequential court checking to avoid threading issues

#### Key Functions:
- `check_courts_sequentially(browser_pool, courts)` → Dict[int, Dict]
  Check courts one by one in sequence
- `_check_single_court(browser_id, page, court_number)` → Dict
  Check availability for single court

### `sync_availability_wrapper.py`
**Purpose**: Synchronous wrapper to avoid threading issues with browser pool

#### Key Functions:
- `check_availability_sync(browser_pool, get_dates)` → Dict[str, Any]
  Check availability synchronously without threading
- `check_single_court_sync(browser_pool, court_number, get_dates)` → Dict[str, Any]
  Check single court synchronously

### `reservation_scheduler.py` *(Updated 2025-07-25)*
**Purpose**: Background scheduler for executing reservations at 48-hour mark. Now with non-blocking concurrent execution and timeout handling.

#### Key Functions:
- `__init__(config, queue, notification_callback, bot_handler=None, browser_pool=None)` → None
  Initialize scheduler with optional pre-initialized browser pool
- `start()` → None
  Start scheduler, uses pre-initialized browser pool if provided
- `_ensure_browser_pool()` → None
  Ensure browser pool is initialized (only if not provided)
- `_create_browser_pool_sync()` → OptimizedBrowserPool/SimpleBrowserPool
  Create browser pool (prefers OptimizedBrowserPool for faster startup)
- `add_reservation(reservation)` → str
  Add reservation to queue
- `cancel_reservation(reservation_id)` → bool
  Cancel pending reservation
- `_update_reservation_success(reservation_id, result)` → None
  Update reservation status to completed
- `_update_reservation_failed(reservation_id, error)` → None
  Update reservation status to failed and remove from queue
- `_execute_single_booking(assignment, reservation, target_date, index, total)` → Dict *(NEW)*
  Execute a single booking asynchronously with proper error handling

### `utils/acuity_booking_form.py`
**Purpose**: Handles the Acuity appointment booking form interaction

#### Key Functions:
- `fill_booking_form(page, user_data, wait_for_navigation)` → Tuple[bool, str]
  Fill out the booking form with user data (nombre, apellidos, telefono, correo)
- `_wait_for_form(page)` → None
  Wait for the form to be ready
- `_fill_field(page, selector, value, field_name)` → bool
  Fill a single form field with validation
- `_handle_recaptcha(page)` → bool
  Check for reCAPTCHA and handle if present
- `_submit_form(page, wait_for_navigation)` → bool
  Submit the booking form
- `check_booking_success(page)` → Tuple[bool, str]
  Check if the booking was successful after form submission

### `utils/async_browser_pool.py`
**Purpose**: Async browser pool using async_playwright for parallel court operations

#### Key Functions:
- `start()` → None
  Initialize browsers and pre-navigate to court URLs in parallel
  - Updated loading strategy: Uses 'domcontentloaded' instead of 'networkidle' for faster initialization
  - Waits for calendar elements ([class*="time"]) to appear (up to 30s)
  - Supports partial initialization with minimum courts required
- `get_page(court_num)` → Page
  Get page for specific court number (expects 1-based court numbers: 1, 2, 3)
- `execute_parallel_booking(target_court, user_info, target_time, user_preferences, target_date)` → Dict
  Execute booking on specified court using pre-loaded page (fixed court indexing)
- `refresh_all_pages()` → None
  Refresh all court pages for latest availability data (skips if critical operation in progress)
- `is_ready()` → bool
  Check if browser pool is ready for use
- `set_critical_operation(in_progress)` → None
  Set flag to prevent browser refresh during critical operations like bookings
- `is_critical_operation_in_progress()` → bool
  Check if a critical operation is currently in progress
- `_create_and_navigate_court_page_with_retry(court)` → bool
  Create court page with retry logic (3 attempts with exponential backoff)
- `_create_and_navigate_court_page_safe(court)` → bool
  Safe wrapper for court page creation with error handling and cleanup

### `utils/browser_health_checker.py`
**Purpose**: Monitor and validate browser pool health before critical operations

#### Key Classes:
- `HealthStatus` - Enum for health states (HEALTHY, DEGRADED, CRITICAL, FAILED)
- `HealthCheckResult` - Result of health check operation with status and details
- `CourtHealthStatus` - Health status for individual court browser

#### Key Functions:
- `perform_pre_booking_health_check()` → HealthCheckResult
  Comprehensive health validation of browser pool before bookings
- `check_pool_health()` → HealthCheckResult
  Check overall browser pool status and connectivity
- `check_court_health(court_number)` → CourtHealthStatus
  Check health of specific court browser with detailed diagnostics
- `test_browser_responsiveness(page, court_number)` → Dict[str, Any]
  Test page connectivity, JavaScript, network access, and DOM queries
- `get_court_health_summary()` → Dict[int, str]
  Get summary of all court health statuses
- `requires_pool_restart()` → bool
  Check if browser pool requires restart based on failure patterns

### `utils/browser_pool_recovery.py`
**Purpose**: Provides recovery strategies for browser pool failures to maintain bot availability

#### Key Classes:
- `RecoveryStrategy` - Enum for recovery strategies (INDIVIDUAL_COURT, PARTIAL_POOL, FULL_RESTART, EMERGENCY_FALLBACK)
- `RecoveryAttempt` - Tracks individual recovery attempt details
- `RecoveryResult` - Result of recovery operation with success status and details
- `BrowserPoolRecoveryService` - Main recovery service class

#### Key Functions:
- `recover_browser_pool(failed_courts, error_context)` → RecoveryResult
  Main recovery method that determines and executes appropriate recovery strategy
- `recover_individual_court(court_number)` → RecoveryResult
  Recover a single court browser by closing and recreating it
- `recover_partial_pool(court_numbers)` → RecoveryResult
  Recover multiple courts with parallel recreation and staggered starts
- `perform_full_pool_restart()` → RecoveryResult
  Complete browser pool restart with state preservation
- `activate_emergency_fallback()` → RecoveryResult
  Activate minimal backup browser system as last resort
- `is_recovery_needed()` → Tuple[bool, List[int]]
  Check if recovery is needed and identify failed courts
- `get_recovery_stats()` → Dict[str, Any]
  Get recovery statistics and history

### `utils/async_booking_executor.py`
**Purpose**: Direct booking execution using AsyncBrowserPool with direct URL navigation

#### Key Functions:
- `execute_booking(court_number, time_slot, user_info, target_date)` → ExecutionResult
  Execute a booking for a specific court and time using direct URL navigation to bypass time selection issues

### `utils/smart_async_booking_executor.py`
**Purpose**: Enhanced booking executor with smart timeout management and retry logic

#### Key Functions:
- `execute_booking_with_retry(court_number, time_slot, user_info, target_date)` → ExecutionResult
  Execute booking with time-aware retry (immediate before target time, 2s delay after, max 10 attempts)
- `_execute_booking_with_smart_timeout(court_number, time_slot, user_info, target_date)` → ExecutionResult
  Execute booking with progressive timeout extension based on loading progress
- `_navigate_with_smart_timeout(page, url)` → Dict
  Navigate with smart timeout that extends based on progress (15s base + up to 6x10s extensions)
- `_navigate_back_to_court_page(page, court_number)` → None
  Navigate back to base court page after booking attempt to prepare for next booking

### `utils/stateful_browser_refresh.py`
**Purpose**: Maintains page state during browser refresh operations

#### Key Functions:
- `refresh_with_state(page)` → Tuple[bool, str]
  Refresh page while maintaining current state (selected times, forms, etc.)
- `_capture_page_state(page)` → PageState
  Capture current page state including court, time selection, and form data
- `_restore_page_state(page, state)` → bool
  Restore page to previously captured state after refresh
- `_extract_court_number(page)` → Optional[int]
  Extract court number from current page
- `_extract_selected_time(page)` → Optional[str]
  Extract currently selected time slot
- `_is_form_visible(page)` → bool
  Check if booking form is visible
- `_extract_form_data(page)` → Dict[str, str]
  Extract data from visible form fields
- `_click_time_slot(page, time_text)` → bool
  Click on a specific time slot button
- `_restore_form_data(page, form_data)` → bool
  Restore previously entered form data

### `utils/emergency_browser_fallback.py`
**Purpose**: Independent emergency booking mechanism that operates without browser pool dependencies

#### Key Functions:
- `__init__()` → None
  Initialize emergency fallback with no pool dependencies
- `create_browser()` → Browser
  Create a single browser instance directly with Playwright
- `book_reservation(user_info, target_date, target_time, court_preferences)` → EmergencyBookingResult
  Execute a booking with single browser using direct URL navigation
- `cleanup()` → None
  Clean up browser resources properly
- `emergency_book(user_info, target_date, target_time, court_preferences)` → EmergencyBookingResult
  Quick convenience function for emergency bookings with automatic cleanup

## Main Files

### `botapp/app.py`
**Purpose**: Async Telegram bot entry point coordinating browser pool, scheduler, and handlers

#### Key Components:
- `CleanBot`
  Initializes the browser pool, reservation service, and callback handlers
- `main()`
  Launches the bot, registering signal handlers and cleanup hooks
- `_graceful_shutdown()` / `_post_stop()`
  Handles orderly shutdown of the scheduler and browser pool

### `run_bot.py`
**Purpose**: Convenience launcher that invokes `botapp.app.main()`

### `playwright_bot.py`
**Purpose**: Core browser automation for tennis court bookings

#### Key Functions:
- `execute_booking(config)` → ExecutionResult
  Execute tennis court booking
- `check_availability(config)` → ExecutionResult
  Check court availability

### `all_day_court_monitor.py`
**Purpose**: Monitor court availability throughout the day

#### Key Functions:
- `monitor_courts(court_numbers)` → None
  Continuously monitor specified courts
- `log_availability(court, times)` → None
  Log availability to file

### `browser/pools/specialized.py`
**Purpose**: Specialized browser pool with court pre-positioning

#### Key Functions:
- `execute_parallel_booking(target_court, user_info, target_time)` → Dict
  Execute booking using pre-positioned browsers with AcuityBookingForm integration
- `get_browser_for_court(court_number)` → Optional[Browser]
  Get browser positioned on specific court
- `_book_specific_time(browser, target_time, user_info)` → Tuple[bool, str]
  Book specific time slot using AcuityBookingForm handler for form filling

### `reservation_queue.py`
**Purpose**: Manages storage and retrieval of queued reservation requests with enhanced priority and waitlist support

#### Key Classes:
- `ReservationStatus` - Enum for all reservation states (PENDING, SCHEDULED, CONFIRMED, WAITLISTED, etc.)

#### Key Functions:
- `add_reservation(reservation_data)` → str
  Add new reservation to queue
- `get_user_reservations(user_id)` → List[Dict]
  Get all reservations for a user
- `update_reservation_status(reservation_id, status)` → bool
  Update reservation status
- `get_reservation(reservation_id)` → Optional[Dict]
  Get specific reservation by ID
- `remove_reservation(reservation_id)` → bool
  Remove/cancel a reservation
- `get_reservations_by_time_slot(target_date, target_time)` → List[Dict]
  Get all reservations for a specific time slot
- `add_to_waitlist(reservation_id, position)` → bool
  Add reservation to waitlist with position
- `get_waitlist_for_slot(target_date, target_time)` → List[Dict]
  Get waitlisted reservations for a time slot

### `logging_config.py`
**Purpose**: Comprehensive logging configuration with dedicated reservation queue logging

#### Key Functions:
- `setup_logging()` → None
  Initialize logging with multiple handlers including dedicated reservation_queue.log
- `get_logger(name)` → logging.Logger
  Get a logger instance for a module
- `log_function_call(logger)` → Callable
  Decorator to log function entry/exit with args and results
- `save_tracked_functions()` → None
  Save tracked function calls to used_functions.log

#### Key Features:
- Dedicated reservation_queue.log for queue operations  
- Separate handlers for ReservationQueue, BookingOrchestrator, and PriorityManager
- Comprehensive logging with file, line, and function information
- Rotating file handlers to manage log size
- Debug, info, and error logs separated

### `reservation_tracker.py`
**Purpose**: Unified tracker for all reservations (queued, immediate, completed)

#### Key Functions:
- `add_immediate_reservation(user_id, data)` → str
  Track immediate booking made within 48h
- `add_completed_booking(user_id, result)` → str
  Track completed booking with confirmation
- `get_user_active_reservations(user_id)` → List[Dict]
  Get all active reservations for user
- `cancel_reservation(reservation_id)` → bool
  Cancel a reservation
- `update_reservation(reservation_id, updates)` → bool
  Update reservation details

## Recent Updates (2025-07-25)

### Fixed Scheduler Hanging Issue (v2)
- **Problem**: Scheduler was blocking on `await executor.execute()` violating async principles
- **Initial Solution**: Implemented concurrent task execution with timeout handling
- **Issue**: Timeout wasn't working properly - tasks were running sequentially
- **Final Solution**: 
  - Used `asyncio.wait()` for true concurrent execution with proper timeout
  - Added 85-second timeout at executor level (SmartAsyncBookingExecutor)
  - Added 90-second timeout at scheduler level for defense in depth
  - Improved task cancellation handling with proper cleanup
  - Added task names for better debugging
- **Changes**:
  - Replaced sequential `asyncio.wait_for()` with concurrent `asyncio.wait()`
  - Added `_execute_booking_with_retry_internal()` with overall timeout wrapper
  - Improved pending task cancellation with timeout and error handling
  - Created `_execute_single_booking()` helper for modular async execution

### Fixed Slow Navigation Detection (2025-07-25)
- **Problem**: Navigation was taking 85+ seconds despite pages loading in 5-7 seconds
- **Root Cause**: 
  - Navigation timeout was set to 120 seconds
  - Form detection only checked every 2 seconds
  - Smart timeout couldn't interrupt the long navigation task
- **Solution**:
  - Reduced navigation timeout from 120s to 30s
  - Added immediate form detection for Acuity booking fields
  - Implemented early exit when form is detected (after 3s stabilization)
  - Added form visibility check after navigation
  - Better detection of unavailable slots
- **Result**: Navigation should now complete in 5-10 seconds as expected

### Implemented Phase-Based Smart Timeout (2025-07-25)
- **Problem**: Even with faster navigation, system waited too long for unavailable slots
- **Root Cause**: Form never appears when slot unavailable, but system waited full timeout
- **Solution**: Phase-based progressive timeout system
  - Base timeout: 1.5s
  - Document response: +1.5s
  - Resources loading: +1.5s  
  - DOM ready: +2.0s (critical - form should appear)
  - Form check window: +1.5s (final chance)
  - Total max: ~8s for unavailable slots
- **Benefits**:
  - Fast detection of unavailable slots (8s vs 85s)
  - Preserves existing code structure (no new classes)
  - Clear phase tracking in logs
  - Immediate exit when no form after DOM ready
