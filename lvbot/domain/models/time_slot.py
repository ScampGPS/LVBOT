"""
TimeSlot model for representing court availability time slots
"""

from dataclasses import dataclass
from typing import Optional


@dataclass
class TimeSlot:
    """
    Represents a single time slot for court availability
    
    Attributes:
        start_time: Start time of the slot (e.g., "10:00 AM" or "10:00")
        end_time: End time of the slot (e.g., "11:00 AM" or "11:00")
        court: Court number (1, 2, or 3)
        available: Whether the slot is available for booking
    """
    start_time: str
    end_time: str
    court: int
    available: bool = True
    
    def __str__(self) -> str:
        """String representation of the time slot"""
        return f"Court {self.court}: {self.start_time} - {self.end_time}"
    
    def duration_minutes(self) -> Optional[int]:
        """
        Calculate duration of the slot in minutes
        
        Returns:
            Duration in minutes if parseable, None otherwise
        """
        try:
            from datetime import datetime
            
            # Try parsing with AM/PM
            try:
                start = datetime.strptime(self.start_time, "%I:%M %p")
                end = datetime.strptime(self.end_time, "%I:%M %p")
            except:
                # Try 24-hour format
                start = datetime.strptime(self.start_time, "%H:%M")
                end = datetime.strptime(self.end_time, "%H:%M")
            
            duration = (end - start).total_seconds() / 60
            return int(duration)
        except:
            return None