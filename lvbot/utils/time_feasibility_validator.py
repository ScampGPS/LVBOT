"""
Time Feasibility Validator - Validates if booking times are within club constraints
Handles tennis club specific timing rules and 48h booking window validation
"""

from datetime import datetime, timedelta, time, date
from typing import List, Optional, Tuple
import logging

logger = logging.getLogger(__name__)

# Tennis club constants
EARLIEST_BOOKING_HOUR = 7  # 7:00 AM
LATEST_BOOKING_HOUR = 21   # 9:00 PM  
BOOKING_WINDOW_HOURS = 48  # 48 hours advance booking


def is_within_booking_window(target_datetime: datetime, current_time: Optional[datetime] = None) -> bool:
    """
    Check if target time is within the booking window
    
    Args:
        target_datetime: The time to check
        current_time: Reference time (defaults to now)
        
    Returns:
        True if target is within booking window
    """
    if current_time is None:
        current_time = datetime.now()
        
    time_difference = target_datetime - current_time
    hours_difference = time_difference.total_seconds() / 3600
    
    is_within = 0 <= hours_difference <= BOOKING_WINDOW_HOURS
    
    logger.debug(f"Time check: {target_datetime} is {hours_difference:.1f}h from {current_time} - Within window: {is_within}")
    
    return is_within


def filter_future_times_for_today(times: List[str], current_time: Optional[datetime] = None) -> List[str]:
    """
    Filter out times that have already passed today
    
    Args:
        times: List of time strings (e.g., ['11:00', '12:00', '15:00'])
        current_time: Reference time (defaults to now)
        
    Returns:
        List of times that are still in the future today
    """
    if current_time is None:
        current_time = datetime.now()
        
    current_hour = current_time.hour
    current_minute = current_time.minute
    
    future_times = []
    
    for time_str in times:
        try:
            # Parse time string
            hour, minute = _parse_time_string(time_str)
            
            # Check if this time is in the future
            if hour > current_hour or (hour == current_hour and minute > current_minute):
                future_times.append(time_str)
                logger.debug(f"Time {time_str} is in future (current: {current_hour:02d}:{current_minute:02d})")
            else:
                logger.debug(f"Time {time_str} has passed (current: {current_hour:02d}:{current_minute:02d})")
                
        except ValueError as e:
            # If parsing fails, include the time (safer to show than hide)
            logger.warning(f"Could not parse time '{time_str}': {e}. Including in results.")
            future_times.append(time_str)
    
    logger.info(f"Filtered {len(times)} times → {len(future_times)} future times for today")
    return future_times


def get_earliest_booking_time_for_day(target_date: date) -> datetime:
    """
    Get the earliest possible booking time for a given day
    
    Args:
        target_date: The date to check
        
    Returns:
        Datetime of earliest booking slot for that day
    """
    return datetime.combine(target_date, time(EARLIEST_BOOKING_HOUR, 0))


def should_navigate_to_next_day(current_days_visible: List[str], current_time: Optional[datetime] = None) -> bool:
    """
    Determine if clicking '>' arrow would show times within booking window
    
    Args:
        current_days_visible: Day labels currently visible (e.g., ['HOY', 'MAÑANA'])
        current_time: Reference time (defaults to now)
        
    Returns:
        True if navigation would show bookable times
    """
    if current_time is None:
        current_time = datetime.now()
        
    today = current_time.date()
    
    # Determine what the next day would be based on what's visible
    if 'HOY' in current_days_visible and 'MAÑANA' not in current_days_visible:
        # Only today visible, next would be tomorrow
        next_day = today + timedelta(days=1)
        next_day_label = "MAÑANA"
    elif 'MAÑANA' in current_days_visible and 'ESTA SEMANA' not in current_days_visible:
        # Today and tomorrow visible, next would be day after tomorrow
        next_day = today + timedelta(days=2)
        next_day_label = "ESTA SEMANA"
    else:
        # All expected days visible or unusual state
        logger.debug("All expected days visible or unusual state - no navigation needed")
        return False
    
    # Check if the earliest slot of the next day is within booking window
    earliest_next_day = get_earliest_booking_time_for_day(next_day)
    is_feasible = is_within_booking_window(earliest_next_day, current_time)
    
    logger.info(f"Navigation check: {next_day_label} ({next_day}) earliest slot at {earliest_next_day} - Feasible: {is_feasible}")
    
    return is_feasible


def get_day_offset_from_label(day_label: str) -> int:
    """
    Get the day offset from a day label
    
    Args:
        day_label: Spanish day label ('HOY', 'MAÑANA', 'ESTA SEMANA')
        
    Returns:
        Number of days from today (0, 1, or 2)
    """
    day_offsets = {
        'HOY': 0,        # Today
        'MAÑANA': 1,     # Tomorrow  
        'ESTA SEMANA': 2 # Day after tomorrow
    }
    
    return day_offsets.get(day_label, 0)


def is_day_label_feasible(day_label: str, current_time: Optional[datetime] = None) -> bool:
    """
    Check if a day label represents a feasible booking day
    
    Args:
        day_label: Spanish day label ('HOY', 'MAÑANA', 'ESTA SEMANA')
        current_time: Reference time (defaults to now)
        
    Returns:
        True if day is within booking window
    """
    if current_time is None:
        current_time = datetime.now()
        
    day_offset = get_day_offset_from_label(day_label)
    target_date = current_time.date() + timedelta(days=day_offset)
    earliest_slot = get_earliest_booking_time_for_day(target_date)
    
    return is_within_booking_window(earliest_slot, current_time)


def _parse_time_string(time_str: str) -> Tuple[int, int]:
    """
    Parse time string into hour and minute integers
    
    Args:
        time_str: Time in format 'HH:MM' or 'H:MM'
        
    Returns:
        Tuple of (hour, minute)
        
    Raises:
        ValueError: If time string cannot be parsed
    """
    try:
        if ':' not in time_str:
            raise ValueError(f"Time string '{time_str}' missing colon separator")
            
        hour_str, minute_str = time_str.strip().split(':')
        hour = int(hour_str)
        minute = int(minute_str)
        
        # Validate ranges
        if not (0 <= hour <= 23):
            raise ValueError(f"Hour {hour} out of valid range 0-23")
        if not (0 <= minute <= 59):
            raise ValueError(f"Minute {minute} out of valid range 0-59")
            
        return hour, minute
        
    except ValueError:
        raise
    except Exception as e:
        raise ValueError(f"Could not parse time string '{time_str}': {e}")