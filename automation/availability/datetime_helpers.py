"""
DateTime utility functions for Tennis Bot
Handles all date and time related operations
"""

from datetime import datetime, timedelta, date
from typing import Optional, List, Tuple
import pytz
import locale


class DateTimeHelpers:
    """Collection of date and time utility functions"""
    
    @staticmethod
    def format_date_for_display(date: datetime) -> str:
        """Format date as 'Monday, January 15'"""
        return date.strftime('%A, %B %d')
    
    @staticmethod
    def format_time_for_display(time: str, use_12h: bool = True) -> str:
        """
        Format time consistently
        Args:
            time: Time string in HH:MM format
            use_12h: If True, convert to 12h format with AM/PM
        """
        if not use_12h:
            return time
            
        try:
            hour, minute = map(int, time.split(':'))
            period = "AM" if hour < 12 else "PM"
            if hour == 0:
                hour = 12
            elif hour > 12:
                hour -= 12
            return f"{hour}:{minute:02d} {period}"
        except:
            return time
    
    @staticmethod
    def get_hours_until(target_date: datetime, from_date: Optional[datetime] = None) -> float:
        """Calculate hours between two dates"""
        if from_date is None:
            from_date = datetime.now(target_date.tzinfo)
        return (target_date - from_date).total_seconds() / 3600
    
    @staticmethod
    def is_within_booking_window(target_date: datetime, window_hours: int = 48) -> bool:
        """Check if date is within booking window"""
        hours_until = DateTimeHelpers.get_hours_until(target_date)
        return 0 <= hours_until <= window_hours
    
    @staticmethod
    def get_booking_window_open_time(target_date: datetime, window_hours: int = 48) -> datetime:
        """Calculate when booking window opens for a target date"""
        return target_date - timedelta(hours=window_hours)
    
    @staticmethod
    def parse_reservation_datetime(date_str: str, time_str: str, timezone_str: str = 'America/Guatemala') -> Optional[datetime]:
        """
        Parse date and time strings into a single datetime object
        Args:
            date_str: Date in various formats (YYYY-MM-DD, MM/DD/YYYY, etc)
            time_str: Time in HH:MM format
            timezone_str: Timezone string
        Returns:
            Datetime object or None if parsing fails
        """
        try:
            tz = pytz.timezone(timezone_str)
            
            # Parse date
            date_obj = None
            for fmt in ['%Y-%m-%d', '%m/%d/%Y', '%d/%m/%Y', '%Y/%m/%d']:
                try:
                    date_obj = datetime.strptime(date_str, fmt).date()
                    break
                except ValueError:
                    continue
            
            if not date_obj:
                return None
            
            # Parse time
            hour, minute = map(int, time_str.split(':'))
            
            # Combine into datetime
            dt = datetime.combine(date_obj, datetime.min.time().replace(hour=hour, minute=minute))
            return tz.localize(dt)
            
        except Exception:
            return None
    
    @staticmethod
    def parse_callback_date(callback_data: str) -> Optional[date]:
        """
        Parse date from callback data with format 'date_YYYY-MM-DD'
        
        Args:
            callback_data: Callback data string containing date
            
        Returns:
            date: Parsed date object, None if invalid format
        """
        try:
            if not callback_data.startswith('date_'):
                return None
            
            date_str = callback_data.replace('date_', '')
            return datetime.strptime(date_str, '%Y-%m-%d').date()
        except ValueError:
            return None
    
    @staticmethod
    def get_day_label(date: datetime, timezone_str: str = 'America/Guatemala') -> str:
        """
        Get a friendly label for the date (Today, Tomorrow, Monday, etc)
        """
        tz = pytz.timezone(timezone_str)
        now = datetime.now(tz).date()
        target_date = date.date() if isinstance(date, datetime) else date
        
        days_diff = (target_date - now).days
        
        if days_diff == 0:
            return "Today"
        elif days_diff == 1:
            return "Tomorrow"
        elif days_diff == 2:
            return "Day After Tomorrow"
        elif 0 < days_diff <= 6:
            return date.strftime('%A')  # Weekday name
        else:
            return date.strftime('%B %d')  # Month Day
    
    @staticmethod
    def get_available_slots_for_date(date: datetime, config) -> List[str]:
        """
        Get available time slots for a specific date based on weekday/weekend
        Args:
            date: The date to check
            config: Bot configuration object with available_times and weekend_times
        """
        # 0 = Monday, 6 = Sunday
        weekday = date.weekday()
        
        if weekday in [5, 6]:  # Saturday or Sunday
            return config.weekend_times if hasattr(config, 'weekend_times') else []
        else:
            return config.available_times if hasattr(config, 'available_times') else []
    
    @staticmethod
    def format_duration(seconds: float) -> str:
        """Format duration in seconds to human readable format"""
        if seconds < 60:
            return f"{seconds:.1f} seconds"
        elif seconds < 3600:
            return f"{seconds/60:.1f} minutes"
        else:
            hours = int(seconds // 3600)
            minutes = int((seconds % 3600) // 60)
            return f"{hours}h {minutes}m"
    
    @staticmethod
    def is_past_time(date: datetime, time_str: str, timezone_str: str = 'America/Guatemala') -> bool:
        """Check if a date/time combination is in the past"""
        target_dt = DateTimeHelpers.parse_reservation_datetime(
            date.strftime('%Y-%m-%d'), 
            time_str, 
            timezone_str
        )
        if not target_dt:
            return True
            
        tz = pytz.timezone(timezone_str)
        now = datetime.now(tz)
        return target_dt < now
    
    @staticmethod
    def get_next_valid_booking_date(timezone_str: str = 'America/Guatemala', booking_window: int = 48) -> datetime:
        """Get the next valid date that can be booked"""
        tz = pytz.timezone(timezone_str)
        now = datetime.now(tz)
        # Add buffer to ensure we're within window
        return now + timedelta(hours=1)
    
    @staticmethod
    def format_countdown(target_datetime: datetime, from_datetime: Optional[datetime] = None) -> str:
        """Format a countdown string to target datetime"""
        if from_datetime is None:
            from_datetime = datetime.now(target_datetime.tzinfo)
            
        diff = target_datetime - from_datetime
        
        if diff.total_seconds() < 0:
            return "Passed"
            
        days = diff.days
        hours = diff.seconds // 3600
        minutes = (diff.seconds % 3600) // 60
        
        parts = []
        if days > 0:
            parts.append(f"{days}d")
        if hours > 0:
            parts.append(f"{hours}h")
        if minutes > 0 or (days == 0 and hours == 0):
            parts.append(f"{minutes}m")
            
        return " ".join(parts)
    
    @staticmethod
    def get_week_range(date: datetime) -> Tuple[datetime, datetime]:
        """Get start and end of week for a given date (Monday-Sunday)"""
        start = date - timedelta(days=date.weekday())
        end = start + timedelta(days=6)
        return start, end