# LVBOT Debugging Tools

This directory contains specialized debugging tools to help verify and troubleshoot the LVBOT tennis reservation system's availability detection.

## Overview

The logs show discrepancies in detected time slots:
- Court 3: Found 8 time slots
- Court 2: Found 2 time slots  
- Court 1: Found 2 time slots

These tools help verify if the bot's detection matches what's actually visible on the court pages.

## Tools

### 1. `debug_court_availability.py`
**Purpose**: Comprehensive debugging tool that navigates to each court page and compares visible vs detected slots.

**Features**:
- Navigates to each court page
- Takes screenshots (initial and highlighted)
- Tests all configured selectors
- Saves page HTML for analysis
- Compares with bot's detection method
- Generates JSON and Markdown reports

**Usage**:
```bash
python3 debug_court_availability.py
```

**Output**: Creates a timestamped directory `debug_court_availability_YYYYMMDD_HHMMSS/` containing:
- Screenshots for each court
- HTML snapshots
- `debug_results.json` - Detailed analysis
- `debug_report.md` - Human-readable report

### 2. `visual_slot_comparison.py`
**Purpose**: Creates annotated screenshots showing exactly what the bot detects vs what it misses.

**Features**:
- Takes clean screenshots of each court
- Annotates detected slots in green
- Highlights missed slots in red
- Tests individual selectors with screenshots
- Creates visual comparison report

**Usage**:
```bash
python3 visual_slot_comparison.py
```

**Output**: Creates a timestamped directory `visual_comparison_YYYYMMDD_HHMMSS/` containing:
- Clean and annotated screenshots
- `comparison_report.html` - Visual HTML report
- `comparison_report.json` - Raw data

### 3. `realtime_availability_monitor.py`
**Purpose**: Monitors availability in real-time to catch changes and patterns.

**Features**:
- Uses the actual bot's browser pool
- Checks availability every N seconds
- Detects and logs changes
- Takes screenshots when changes occur
- Tracks availability history

**Usage**:
```bash
# Run indefinitely (Ctrl+C to stop)
python3 realtime_availability_monitor.py

# Run for specific duration (in minutes)
python3 realtime_availability_monitor.py --duration 10

# Custom refresh interval (in seconds)
python3 realtime_availability_monitor.py --interval 10
```

**Output**: Creates a timestamped directory `realtime_monitor_YYYYMMDD_HHMMSS/` containing:
- Screenshots of changes
- `monitor_state.json` - Current state
- `session_summary.md` - Session report

### 4. `run_availability_diagnostics.py`
**Purpose**: Runs all debugging tools and creates a consolidated report.

**Features**:
- Coordinates all three debugging tools
- Creates summary of findings
- Provides recommendations
- Identifies selector issues
- Detects mismatches

**Usage**:
```bash
python3 run_availability_diagnostics.py
```

**Output**: Creates `diagnostics_report_YYYYMMDD_HHMMSS/` with consolidated findings.

## Installation

Make sure you have installed the required dependencies:

```bash
pip install -r requirements.txt
```

Note: The visual comparison tool requires Pillow for image processing, which has been added to requirements.txt.

## Common Issues & Solutions

### Issue: Bot detects fewer slots than visible
**Possible Causes**:
1. Selectors are outdated
2. Page structure has changed
3. Dynamic content loading issues

**Solution**: Run `debug_court_availability.py` and check the selector test results.

### Issue: Detection works but is inconsistent
**Possible Causes**:
1. Timing issues
2. Page not fully loaded
3. Dynamic content changes

**Solution**: Use `realtime_availability_monitor.py` to observe patterns over time.

### Issue: Screenshots show errors or blank pages
**Possible Causes**:
1. Network issues
2. Authentication required
3. Page load timeout

**Solution**: Check browser console output and increase timeouts if needed.

## Interpreting Results

### Debug Report Fields
- **detected_slots**: What the bot's method found
- **visible_elements**: All time-like elements on page
- **selector_results**: Which selectors work and what they find
- **match**: Whether debug matches bot detection

### Visual Annotations
- **Green boxes**: Time slots detected by bot
- **Red boxes**: Time slots missed by bot
- **Blue boxes**: Elements found by specific selectors

### Monitor Changes
- **➕ Added**: New time slots appeared
- **➖ Removed**: Time slots disappeared
- **🆕**: Court data changed since last check

## Next Steps

After running diagnostics:

1. If selectors are failing, update `TIME_SLOT_SELECTORS` in `utils/constants.py`
2. If timing is an issue, adjust wait times in `availability_checker_v3.py`
3. If structure changed, update the extraction logic in `time_slot_extractor.py`
4. Share the debug reports when reporting issues

## Example Workflow

```bash
# 1. First, run the comprehensive diagnostics
python3 run_availability_diagnostics.py

# 2. If issues found, run specific tool for deeper analysis
python3 visual_slot_comparison.py

# 3. Monitor for patterns
python3 realtime_availability_monitor.py --duration 30

# 4. Review reports and screenshots in generated directories
```