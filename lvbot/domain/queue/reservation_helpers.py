"""
Reservation helper functions
Handles reservation-specific operations and calculations
"""

from typing import List, Dict, Any, Tuple, Optional
from datetime import datetime, timedelta
import pytz
import logging


class ReservationHelpers:
    """Collection of reservation helper functions"""
    
    @staticmethod
    def create_tennis_config(user_info: Dict[str, Any], courts: List[int], 
                           time: str, speed_multiplier: float = 1.0) -> Any:
        """Create TennisConfig object from reservation data"""
        # Import here to avoid circular imports
        from playwright_bot import TennisConfig
        
        return TennisConfig(
            email=user_info['email'],
            first_name=user_info['first_name'],
            last_name=user_info['last_name'],
            phone=user_info['phone'],
            court_preference=[c-1 for c in courts],  # Convert to 0-indexed
            preferred_times=[time],
            headless=True,
            human_behavior_enabled=True,
            speed_multiplier=speed_multiplier
        )
    
    @staticmethod
    def calculate_retry_delay(retry_count: int, minutes_since_window: float, 
                            config: Any) -> Tuple[bool, float, str]:
        """
        Calculate if should retry and delay based on timing
        Returns: (should_retry, delay_seconds, status_message)
        """
        max_retries = getattr(config, 'max_retries', 3)
        
        if retry_count >= max_retries:
            return False, 0, f"Maximum retries ({max_retries}) reached"
        
        # Aggressive retry in first 5 minutes
        if minutes_since_window < 5:
            if retry_count == 0:
                delay = 30  # 30 seconds
            elif retry_count == 1:
                delay = 60  # 1 minute
            else:
                delay = 120  # 2 minutes
            return True, delay, f"Quick retry #{retry_count + 1} in {delay}s"
        
        # Normal retry for 5-30 minutes
        elif minutes_since_window < 30:
            delay = 300  # 5 minutes
            return True, delay, f"Normal retry #{retry_count + 1} in 5 minutes"
        
        # Slow retry after 30 minutes
        else:
            delay = 900  # 15 minutes
            return True, delay, f"Slow retry #{retry_count + 1} in 15 minutes"
    
    @staticmethod
    def format_court_assignments(reservations: List[Any]) -> Dict[int, List[int]]:
        """
        Format court assignments to avoid conflicts
        Returns: {user_id: [assigned_courts]}
        """
        assignments = {}
        used_courts = set()
        
        # First pass: assign unique courts
        for res in reservations:
            available_courts = [c for c in res.courts if c not in used_courts]
            
            if available_courts:
                # Assign first available court
                assigned = available_courts[0]
                assignments[res.user_id] = [assigned]
                used_courts.add(assigned)
            else:
                # No unique courts available
                assignments[res.user_id] = []
        
        # Second pass: handle users with no assignments
        remaining_users = [r for r in reservations if not assignments.get(r.user_id)]
        if remaining_users and len(used_courts) < 4:  # Still courts available
            # Distribute remaining courts
            for res in remaining_users:
                # Find least used court from their preferences
                court_usage = {c: 0 for c in res.courts}
                for assigned_courts in assignments.values():
                    for court in assigned_courts:
                        if court in court_usage:
                            court_usage[court] += 1
                
                # Assign least used court
                if court_usage:
                    least_used = min(court_usage.items(), key=lambda x: x[1])[0]
                    assignments[res.user_id] = [least_used]
        
        return assignments
    
    @staticmethod
    def calculate_booking_priority(user_profile: Any, reservation: Any, 
                                 config: Any) -> int:
        """Calculate booking priority score (lower is higher priority)"""
        priority = 0
        
        # Admin gets highest priority
        if getattr(user_profile, 'is_admin', False):
            return 0
        
        # Base priority from reservation
        priority = reservation.priority * 1000
        
        # Bonus for earlier time slots
        try:
            hour = int(reservation.time.split(':')[0])
            if hour < 10:  # Morning slots
                priority -= 100
            elif hour > 18:  # Evening slots
                priority -= 50
        except:
            pass
        
        # Bonus for single court request
        if len(reservation.courts) == 1:
            priority -= 200
        
        # Penalty for all courts request
        if len(reservation.courts) >= 4:
            priority += 300
        
        # User history bonus (fewer reservations = higher priority)
        total_reservations = getattr(user_profile, 'total_reservations', 0)
        if total_reservations < 5:
            priority -= 150
        elif total_reservations > 20:
            priority += 100
        
        return max(0, priority)  # Ensure non-negative
    
    @staticmethod
    def group_reservations_by_time(reservations: List[Any]) -> Dict[str, List[Any]]:
        """Group reservations by date and time"""
        groups = {}
        
        for res in reservations:
            key = f"{res.date}_{res.time}"
            if key not in groups:
                groups[key] = []
            groups[key].append(res)
        
        return groups
    
    @staticmethod
    def get_next_retry_time(reservation: Any, config: Any) -> Optional[datetime]:
        """Calculate next retry time for a reservation"""
        if reservation.status != 'pending' or reservation.attempts >= config.max_retries:
            return None
        
        # Get minutes since window opened
        tz = pytz.timezone(config.timezone)
        now = datetime.now(tz)
        window_open = reservation.target_datetime - timedelta(hours=config.booking_window_hours)
        minutes_since = (now - window_open).total_seconds() / 60
        
        should_retry, delay_seconds, _ = ReservationHelpers.calculate_retry_delay(
            reservation.attempts, minutes_since, config
        )
        
        if should_retry:
            return now + timedelta(seconds=delay_seconds)
        
        return None
    
    @staticmethod
    def format_reservation_summary(reservation: Any, include_user: bool = True) -> str:
        """Format a reservation into a summary string"""
        courts = ', '.join([f"Court {c}" for c in reservation.courts])
        
        summary = f"📅 {reservation.date} at {reservation.time}\n"
        summary += f"🎾 {courts}\n"
        
        if include_user and hasattr(reservation, 'user_info'):
            summary += f"👤 {reservation.user_info.get('first_name', '')} {reservation.user_info.get('last_name', '')}\n"
        
        summary += f"📊 Status: {reservation.status}"
        
        if reservation.attempts > 0:
            summary += f" (Attempts: {reservation.attempts})"
        
        return summary
    
    @staticmethod
    def check_reservation_conflicts(new_reservation: Any, 
                                  existing_reservations: List[Any]) -> List[str]:
        """Check for conflicts with existing reservations"""
        conflicts = []
        
        for existing in existing_reservations:
            # Skip if different date/time
            if (existing.date != new_reservation.date or 
                existing.time != new_reservation.time):
                continue
            
            # Check court overlap
            court_overlap = set(existing.courts) & set(new_reservation.courts)
            if court_overlap:
                conflicts.append(
                    f"Court conflict: {court_overlap} already requested by user {existing.user_id}"
                )
            
            # Check same user
            if existing.user_id == new_reservation.user_id:
                conflicts.append(
                    f"Duplicate reservation: You already have a reservation at this time"
                )
        
        return conflicts
    
    @staticmethod
    def estimate_execution_time(num_reservations: int, parallel_browsers: int = 3) -> str:
        """Estimate how long reservations will take to execute"""
        # Base time per reservation
        time_per_reservation = 15  # seconds
        
        # Calculate based on parallelization
        batches = (num_reservations + parallel_browsers - 1) // parallel_browsers
        total_seconds = batches * time_per_reservation
        
        if total_seconds < 60:
            return f"{total_seconds} seconds"
        else:
            minutes = total_seconds // 60
            seconds = total_seconds % 60
            return f"{minutes}m {seconds}s"
    
    @staticmethod
    def should_use_extreme_mode(reservation: Any, config: Any) -> bool:
        """Determine if extreme speed mode should be used"""
        # Check if within critical window (e.g., first 2 minutes)
        tz = pytz.timezone(config.timezone)
        now = datetime.now(tz)
        window_open = reservation.target_datetime - timedelta(hours=config.booking_window_hours)
        minutes_since = (now - window_open).total_seconds() / 60
        
        # Use extreme mode for:
        # 1. First 2 minutes of window
        # 2. High priority reservations
        # 3. Failed attempts in first 5 minutes
        return (
            minutes_since < 2 or
            (reservation.priority == 0 and minutes_since < 5) or
            (reservation.attempts > 0 and minutes_since < 5)
        )