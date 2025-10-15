# Claude Code Guidelines for LVBOT

## Critical Threading Rules for Playwright

### IMPORTANT: Playwright Threading Constraints
1. **Playwright objects are NOT thread-safe** - Browser, Context, and Page objects must be accessed from the same thread that created them
2. **Never use ThreadPoolExecutor** with Playwright browser operations
3. **All browser pool operations must happen in the main thread**
4. **The "cannot switch to a different thread" error** means you're violating Playwright's threading model

### Fixed Threading Issues:
- Removed ThreadPoolExecutor from browser pool initialization in ReservationScheduler
- Browser pool now created directly in main thread
- All browser operations stay in the thread that created them

## Critical Async/Event Loop Rules

### IMPORTANT: Event Loop Context Rules
1. **Playwright objects are bound to their event loop** - Browser, Context, and Page objects can only be accessed from the same event loop that created them
2. **Never create new event loops** when already in an async context (use `asyncio.get_running_loop()` to check)
3. **AsyncBrowserPool must be accessed from the main event loop** - The same loop that created it during bot startup
4. **Avoid sync-to-async conversions** - Keep async code paths fully async from Telegram handlers down to browser operations

### Event Loop Best Practices:
- **For async contexts**: Use `await` directly, never `loop.run_until_complete()` 
- **For sync contexts**: Only create a new event loop if absolutely necessary (e.g., from scheduler)
- **Check context first**: Use `asyncio.get_running_loop()` to detect if you're already in async context
- **Prefer async all the way**: When a handler is async (like Telegram bot handlers), keep the entire execution path async

### Example of Correct Async Flow:
```python
# GOOD - Direct async execution
async def execute_booking(...):
    result = await browser_pool.execute_parallel_booking(...)
    return result

# BAD - Creating new event loop in async context  
async def execute_booking(...):
    loop = asyncio.new_event_loop()  # DON'T DO THIS!
    result = loop.run_until_complete(browser_pool.execute_parallel_booking(...))
```

## Direct URL Navigation for Bookings

### IMPORTANT: Use Direct URL Navigation
To avoid issues with timezone dropdowns intercepting clicks and timing problems:

1. **Navigate directly to booking form** using constructed URLs:
   ```python
   # URL pattern
   {base_url}/datetime/{date}T{time}:00-06:00?appointmentTypeIds[]={appointment_type_id}
   
   # Example:
   https://clublavilla.as.me/schedule/7d558012/appointment/16021953/calendar/4291312/datetime/2025-07-24T09:00:00-06:00?appointmentTypeIds[]=16021953
   ```

2. **Form fields use client.* prefix**:
   - `client.firstName` (not nombre)
   - `client.lastName` (not apellidos)
   - `client.phone` (not telefono)
   - `client.email` (not correo)

3. **This approach bypasses**:
   - Time button clicking issues
   - Timezone dropdown interference
   - Dynamic loading delays
   - Form not appearing after time selection

## Important Development Principles

### 1. Code Modularity
- **Keep all new code modular** - break functionality into reusable functions
- **Always try to use existing functions** before creating new ones
- Check `utils/` directory for existing helper modules:
  - `datetime_helpers.py` - Date/time operations
  - `telegram_ui.py` - UI components and formatting
  - `validation.py` - Input validation
  - `db_helpers.py` - Database operations
  - `browser_helpers.py` - Browser automation
  - `reservation_helpers.py` - Reservation logic
  - `message_handlers.py` - Message handling patterns
  - `state_manager.py` - Conversation state management

### 2. DRY Principle (Don't Repeat Yourself)
- Before writing new code, search for existing implementations
- Extract common patterns into helper functions
- Use the modular architecture in `utils/` directory

### 3. Performance Optimizations
- Always maintain the performance settings:
  - 3 parallel browsers
  - Browser pool enabled
  - Performance monitoring active
  - Smart refresh strategies

### 4. Testing Commands
When making changes, always test with:
```bash
# Run main bot
python3 telegram_tennis_bot.py

# Run monitoring script  
python3 all_day_court_monitor.py 1

# Check logs
tail -f all_day_monitor_*.log
```

### 5. Monitoring Insights
From our testing, we learned:
- **Refresh strategy** (Browser2/3) found slots fastest (~1.7s after release)
- **Smart refresh** (Browser4/5) is more efficient - only refreshes when needed
- Hour buttons appear exactly at the booking window opening time (48h before playing)

### 6. Code Organization
```
LVBOT/
├── utils/                    # Helper modules (USE THESE!)
│   ├── datetime_helpers.py   # Date/time utilities
│   ├── telegram_ui.py        # UI components
│   ├── validation.py         # Input validation
│   ├── db_helpers.py         # Database helpers
│   ├── browser_helpers.py    # Browser automation
│   ├── reservation_helpers.py # Reservation logic
│   ├── message_handlers.py   # Message patterns
│   └── state_manager.py      # State management
├── telegram_tennis_bot.py    # Main bot
├── playwright_bot.py         # Browser automation
├── all_day_court_monitor.py  # Monitoring script
└── browser_pool_specialized.py # Performance optimization
```

### 7. When Adding Features
1. First check if similar functionality exists
2. Look for helper functions in `utils/`
3. Extract common patterns into new helpers if needed
4. Keep functions focused and single-purpose
5. Add docstrings with examples

### 8. Example of Good Modular Code
```python
# BAD - Inline implementation
if hours_until_target <= 48:
    # booking window open
else:
    # queue for future

# GOOD - Using existing helper
from utils.datetime_helpers import DateTimeHelpers

if DateTimeHelpers.is_within_booking_window(target_date, 48):
    # booking window open
else:
    # queue for future
```

## Remember
- **Reuse before recreating**
- **Extract common patterns**
- **Keep functions small and focused**
- **Use the utils/ directory**
- **Document your code**

### 9. MANIFEST.md Maintenance
**IMPORTANT**: Always update MANIFEST.md when:
- Adding new functions to any file
- Modifying function signatures (parameters/returns)
- Creating new files
- Removing functions or files
- Changing the purpose of a function

The MANIFEST.md file serves as the primary reference for understanding the codebase structure and finding functions to reuse.

**Update format**:
```markdown
### `filename.py`
**Purpose**: Brief description of file's role

#### Key Functions:
- `function_name(param1, param2)` → Returns: type
  Brief description of what function does
```

This ensures the AI assistant can efficiently navigate and understand the codebase without opening multiple files.

### 10. Code Modification Principle
**IMPORTANT**: When making changes:
- **Always prefer editing existing modular code** over creating new code
- Look for existing functions that can be modified
- Extend existing classes rather than creating new ones
- If a function does 80% of what you need, modify it rather than creating a new one
- Use parameters and configuration options to make existing code more flexible

**Example**:
```python
# BAD - Creating new function
def check_availability_for_court_3():
    # New implementation

# GOOD - Modifying existing function
def check_availability(court_numbers: List[int] = None):
    # Modified to accept specific courts
```

## Booking Confirmation Detection

The booking system now automatically detects successful bookings by:

1. **Confirmation Page URL Pattern**: 
   - Detects URLs matching `/confirmation/{confirmation_id}`
   - Extracts the confirmation ID for reference

2. **User Name Extraction**:
   - Looks for patterns like "{Name}, ¡Tu cita está confirmada\!"
   - Returns personalized confirmation messages

3. **Success Message Format**:
   - With name: "✅ Saul, ¡Tu cita está confirmada\! (ID: 28ef7163777193af2bb9cd8f760971a7)"
   - Without name: "✅ ¡Cita confirmada\! (ID: 28ef7163777193af2bb9cd8f760971a7)"

4. **Direct URL Navigation**:
   - Uses direct URLs to bypass timezone dropdown issues
   - Pattern: `{base_url}/datetime/{date}T{time}:00-06:00?appointmentTypeIds[]={appointment_type_id}`

## Agent Routing Rules

### Specialized Agent Assignments

#### LVBOT Impact Assessment Coordinator (`/agents/orchestrators/lvbot-impact-coordinator.md`)
**MANDATORY CONSULTATION - Route when:**
- Modifying functions with dependencies outside their file
- Changing function signatures used by multiple modules
- Altering data structures shared across components
- Modifying browser pool, queue system, or critical infrastructure
- Making changes to widely-used utility functions
- Any modification that could affect threading or async behavior

**Key capabilities:**
- Cross-file dependency tracing and impact analysis
- Multi-agent coordination for complex changes
- Risk assessment and safe change pathway planning
- Downstream effect prediction and breaking change detection
- Test requirement specification and rollback planning

**CRITICAL RULE**: This agent MUST be consulted before any change to:
- `utils/async_browser_pool.py` or browser-related functions
- `utils/reservation_queue.py` or queue management functions  
- Any function imported by 3+ other files
- Function signatures with external dependencies
- Shared data structures or configuration

**Trigger phrases:**
- "modify function", "change signature", "update utility"
- "cross-file dependency", "impact analysis", "safe to change"
- "affects other modules", "breaking change", "downstream effects"

#### LVBOT Debugging Specialist (`/agents/specialized/lvbot-debugging-specialist.md`)
**Route when dealing with:**
- Visual debugging issues (screenshots needed)
- Bot execution problems requiring runtime analysis
- Network monitoring and timing issues
- Browser automation failures requiring step-by-step analysis
- User experience problems in Telegram interface
- Queue system debugging with visual evidence
- Performance bottlenecks requiring measurement

**Key capabilities:**
- Take screenshots of browser states and Telegram interface
- Execute bot and monitor real-time logs
- Run specific test files for issue reproduction
- Analyze network requests and timing
- Visual comparison of before/after states

**Trigger phrases:**
- "take screenshot", "visual debugging", "what user sees"
- "run the bot", "test execution", "monitor logs"
- "network analysis", "timing issues", "browser behavior"
- "debugging flow", "step-by-step analysis"

#### Performance Optimizer (`/agents/core/performance-optimizer.md`)
**Route when dealing with:**
- Browser pool optimization
- Async/threading issues
- Event loop problems
- Memory usage and performance metrics
- Playwright threading constraints

#### Backend Developer (`/agents/universal/backend-developer.md`)
**Route when dealing with:**
- Telegram bot handlers and callbacks
- Reservation queue logic
- Database operations
- API integrations
- General Python development

#### Code Archaeologist (`/agents/core/code-archaeologist.md`)
**Route when dealing with:**
- Code organization and refactoring
- Finding existing functions to reuse
- Extracting common patterns
- Modular architecture improvements
- MANIFEST.md updates

### Example Routing Scenarios

**Scenario 1: "Bot not responding to user commands"**
→ Route to: **LVBOT Debugging Specialist**
→ Actions: Take Telegram screenshots, run bot with logs, monitor handler execution

**Scenario 2: "Browser pool is slow to initialize"**
→ Route to: **Performance Optimizer**
→ Actions: Analyze async patterns, optimize browser creation, measure timing

**Scenario 3: "Add new reservation feature"**
→ Route to: **Backend Developer**
→ Actions: Implement handlers, update queue logic, add database operations

**Scenario 4: "Refactor utils directory structure"**
→ Route to: **Code Archaeologist**
→ Actions: Analyze existing modules, extract patterns, update MANIFEST.md

**Scenario 5: "Modify browser pool initialization function"**
→ Route to: **LVBOT Impact Coordinator** (MANDATORY) → **Performance Optimizer**
→ Actions: Assess threading dependencies, coordinate with debugging specialist, validate async behavior

**Scenario 6: "Change reservation queue data format"**
→ Route to: **LVBOT Impact Coordinator** (MANDATORY) → **Backend Developer**
→ Actions: Trace all queue dependencies, coordinate database changes, plan migration strategy

**Scenario 7: "Update utility function signature"**
→ Route to: **LVBOT Impact Coordinator** (MANDATORY) → appropriate specialist
→ Actions: Map all import sites, assess breaking changes, coordinate multi-file updates

### Mandatory Coordination Rules

**CRITICAL**: The Impact Assessment Coordinator MUST be consulted before:
- Any modification to functions imported by multiple files
- Changes to browser pool or async-related operations
- Queue system or reservation logic modifications
- Utility function signature changes
- Data structure alterations
- Threading or event loop modifications

**Workflow**: Impact Coordinator → Risk Assessment → Specialized Agent Assignment → Coordinated Implementation

