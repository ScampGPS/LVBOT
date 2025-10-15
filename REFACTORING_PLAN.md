# Refactoring Plan

This document outlines the plan for refactoring the `lvbot` codebase to improve modularity, reduce redundancy, and enhance maintainability, following the specified deep refactoring protocol.

## 1. Consolidate Browser Helper Modules

*   **Files to Merge:**
    *   `utils/browser_helpers.py`
    *   `utils/async_browser_helpers.py`
*   **Rationale:** These files contain significant functional overlap, with many duplicated or similar methods for browser automation. Merging them will create a single, authoritative source for all browser-related utility functions, adhering to the DRY principle.
*   **Plan:**
    1.  Create a new, unified `BrowserHelpers` class within `utils/async_browser_helpers.py`.
    2.  Migrate all unique, valuable methods from `utils/browser_helpers.py` into the new `BrowserHelpers` class.
    3.  For overlapping methods, select the most robust and efficient implementation (generally from `async_browser_helpers.py`).
    4.  Rename the class to `BrowserHelpers` to establish it as the canonical helper class.
    5.  Search the entire codebase for any imports from `utils.browser_helpers` and refactor them to import from the new consolidated module.
    6.  Delete the redundant `utils/browser_helpers.py` file.

## 2. Consolidate Court Monitoring Scripts

*   **Files to Merge:**
    *   `all_day_court_monitor.py`
    *   `court_slot_monitor.py`
    *   `refined_slot_monitor.py`
*   **Rationale:** These files share core logic for monitoring court availability but are split by specific use cases (all-day vs. single-slot) or for debugging. This leads to code duplication. A single, configurable `CourtMonitor` class can handle all scenarios.
*   **Plan:**
    1.  Create a new `court_monitor.py` file.
    2.  Implement a `CourtMonitor` class within the new file.
    3.  Merge the core monitoring logic and multi-browser strategies from `all_day_court_monitor.py` and `court_slot_monitor.py` into the `CourtMonitor` class. The class will be configurable to handle both all-day and single-slot monitoring.
    4.  Incorporate the debugging and exploration functionality from `refined_slot_monitor.py` into a distinct method within the `CourtMonitor` class, such as `explore_booking_flow()`.
    5.  Delete the three old monitoring files.

## 3. Consolidate Tennis Executor Modules

*   **Files to Merge:**
    *   `async_tennis_executor.py`
    *   `utils/smart_tennis_executor.py`
*   **Rationale:** `smart_tennis_executor.py` acts as a strategic layer on top of `async_tennis_executor.py`, deciding whether to use a browser pool or direct execution. This relationship can be simplified by merging them into a single, more intelligent executor class.
*   **Plan:**
    1.  Create a new `tennis_executor.py` file in the `utils/` directory.
    2.  Implement a new `TennisExecutor` class that combines the logic from both files.
    3.  The `TennisExecutor` class will manage its own `ThreadPoolExecutor` for direct execution and will also be able to use a provided browser pool.
    4.  The primary `execute` method will encapsulate the "smart" routing logic, preferring the browser pool if available and falling back to direct execution.
    5.  Refactor any code using the old executors to use the new `utils/tennis_executor.py` module.
    6.  Delete `async_tennis_executor.py` and `utils/smart_tennis_executor.py`.
