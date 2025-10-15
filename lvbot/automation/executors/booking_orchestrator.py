"""
Dynamic Booking Orchestrator
Coordinates multiple browsers with refresh strategies and dynamic fallbacks
"""

import asyncio
import threading
from typing import List, Dict, Set, Optional, Any, Tuple
from datetime import datetime, timedelta
import logging
from dataclasses import dataclass
from enum import Enum
from lvbot.reservations.queue.priority_manager import PriorityManager, PriorityUser
from lvbot.users.manager import UserTier


class BookingStatus(Enum):
    PENDING = "pending"
    ATTEMPTING = "attempting"
    SUCCESS = "success"
    FAILED = "failed"
    FALLBACK = "fallback"


@dataclass
class BookingAttempt:
    """Track a booking attempt"""
    user_id: int
    reservation_id: str
    target_court: int
    fallback_courts: List[int]
    status: BookingStatus
    browser_id: Optional[str] = None
    attempt_time: Optional[datetime] = None
    result: Optional[Dict] = None


class DynamicBookingOrchestrator:
    """
    Orchestrates booking attempts across multiple browsers with dynamic fallbacks
    
    Strategy:
    1. Use 3 browsers with staggered refresh (0s, 2s, 4s delays)
    2. Assign primary targets to browsers
    3. If booking fails, dynamically reassign to available courts
    4. Track successes/failures in real-time to avoid conflicts
    """
    
    def __init__(self):
        self.logger = logging.getLogger('BookingOrchestrator')
        self.lock = threading.Lock()
        
        # Priority manager for user sorting
        self.priority_manager = PriorityManager()
        
        # Log initialization
        self.logger.info("""BOOKING ORCHESTRATOR INITIALIZED
        Priority system: Two-tier FCFS (Admin > VIP > Regular)
        Browser strategies: 3 browsers with staggered refresh
        Fallback support: Dynamic court reassignment enabled
        """)
        
        # Track booking status
        self.active_attempts: Dict[str, BookingAttempt] = {}  # reservation_id -> attempt
        self.court_status: Dict[int, str] = {}  # court -> 'available'/'attempting'/'booked'
        self.successful_bookings: Set[str] = set()  # reservation_ids that succeeded
        self.bumped_users: Dict[str, str] = {}  # user_id -> vip_id who bumped them
        
        # Browser refresh strategies (like our monitoring that worked best)
        # Support both 2 and 3 browser configurations
        self.browser_strategies = [
            {"id": "Browser1-Refresh0", "delay": 0, "refresh_interval": 5},
            {"id": "Browser2-Refresh2", "delay": 2, "refresh_interval": 5},
            {"id": "Browser3-Refresh4", "delay": 4, "refresh_interval": 5}
        ]
        
        # For GCE with limited resources - optimized based on monitoring data
        # Slots appear 1-2 seconds BEFORE the hour
        self.browser_strategies_limited = [
            {"id": "Browser1-EarlyBird", "delay": 0, "start_offset": -3},  # Starts 3s before hour
            {"id": "Browser2-OnTime", "delay": 1, "start_offset": -1}      # Starts 1s before hour
        ]
        
        # Precision refresh timing based on monitoring data
        # Slots appear 1.4s before the hour, refresh takes ~1s
        self.precision_refresh_config = {
            'slot_appears_at': -1.4,     # Slots appear 1.4s before hour
            'refresh_duration': 1.0,     # Refresh takes ~1 second
            'refresh_at': -2.0,          # Start refresh at -2.0s (safer timing)
            'safety_margin': 0.0,        # Already built into -2.0s timing
            'start_early': 15,           # Still start 15s early for navigation
            'position_by': 10,           # Be on calendar by -10s
        }
        
        # Legacy smart refresh config (kept for compatibility)
        self.smart_refresh_config = {
            'navigation_time': 11,       # Worst-case navigation time
            'pre_window_start': -15,     # Start monitoring 15s before (to account for navigation)
            'rapid_check_start': -3,     # Rapid checks from 3s before
            'critical_start': -2,        # Ultra-rapid from 2s before
            'critical_end': 2,           # Ultra-rapid until 2s after
            'post_window_end': 5,        # Stop rapid checks 5s after
            'intervals': {
                'normal': 2.0,           # 2 seconds
                'pre_rapid': 0.5,        # 500ms
                'rapid': 0.2,            # 200ms
                'critical': 0.1,         # 100ms (during -2s to +2s window)
            }
        }
    
    def create_booking_plan(self, reservations: List[Any], time_slot: str, user_manager=None) -> Dict[str, Any]:
        """
        Create dynamic booking plan for a time slot using priority system
        
        Args:
            reservations: List of reservations for the same time slot
            time_slot: Target time (e.g., "09:00")
            user_manager: Optional UserManager for tier lookup
            
        Returns:
            Booking plan with browser assignments and fallback strategies
        """
        with self.lock:
            self.logger.info(f"""CREATING BOOKING PLAN
            Time slot: {time_slot}
            Total reservations: {len(reservations)}
            User manager provided: {user_manager is not None}
            """)
            
            # Reset court status
            self.court_status = {1: 'available', 2: 'available', 3: 'available'}
            
            # Convert reservations to PriorityUser objects
            priority_users = []
            for res in reservations:
                # Get user tier
                user_id = getattr(res, 'user_id')
                if hasattr(res, 'priority'):
                    # Use existing priority if set (0=admin, 1=vip, 2=regular)
                    tier_value = getattr(res, 'priority', 2)
                    tier = UserTier(tier_value)
                elif user_manager:
                    # Look up user tier from user manager
                    tier = user_manager.get_user_tier(user_id)
                else:
                    # Default to regular
                    tier = UserTier.REGULAR
                
                priority_user = PriorityUser(
                    user_id=user_id,
                    tier=tier,
                    created_at=getattr(res, 'created_at'),
                    reservation_id=getattr(res, 'id'),
                    court_preferences=getattr(res, 'courts', [])
                )
                priority_users.append(priority_user)
            
            # Log priority users before allocation
            tier_counts = {}
            for user in priority_users:
                tier_name = user.tier.name
                tier_counts[tier_name] = tier_counts.get(tier_name, 0) + 1
            
            self.logger.info(f"Priority user breakdown: {tier_counts}")
            
            # Use priority manager to allocate users
            confirmed_users, waitlisted_users = self.priority_manager.allocate_to_browsers(
                priority_users, num_browsers=3
            )
            
            # Log allocation results
            self.logger.info(f"""ALLOCATION RESULTS
            Confirmed users: {len(confirmed_users)}
            Waitlisted users: {len(waitlisted_users)}
            """)
            
            for idx, user in enumerate(confirmed_users):
                self.logger.info(f"  Confirmed #{idx+1}: User {user.user_id} ({user.tier.name})")
            
            for idx, user in enumerate(waitlisted_users[:5]):  # Show first 5 waitlisted
                self.logger.info(f"  Waitlisted #{idx+1}: User {user.user_id} ({user.tier.name})")
            
            # Create booking attempts for confirmed users
            attempts = []
            assigned_courts = set()
            
            for user in confirmed_users:
                # Assign primary court
                primary_court = None
                for court in user.court_preferences:
                    if court not in assigned_courts:
                        primary_court = court
                        assigned_courts.add(court)
                        break
                
                if not primary_court and len(assigned_courts) < 3:
                    # Assign any available court
                    for court in [1, 2, 3]:
                        if court not in assigned_courts:
                            primary_court = court
                            assigned_courts.add(court)
                            break
                
                if primary_court:
                    # Create fallback list (other courts in preference order)
                    fallback_courts = [c for c in user.court_preferences if c != primary_court]
                    # Add any remaining courts
                    for court in [1, 2, 3]:
                        if court not in fallback_courts and court != primary_court:
                            fallback_courts.append(court)
                    
                    attempt = BookingAttempt(
                        user_id=user.user_id,
                        reservation_id=user.reservation_id,
                        target_court=primary_court,
                        fallback_courts=fallback_courts,
                        status=BookingStatus.PENDING
                    )
                    attempts.append(attempt)
                    self.active_attempts[user.reservation_id] = attempt
                    self.court_status[primary_court] = 'attempting'
                    
                    self.logger.debug(f"""Court assignment for user {user.user_id}:
                    Primary: Court {primary_court}
                    Fallbacks: {fallback_courts}
                    """)
            
            # Distribute attempts across browsers
            browser_assignments = []
            for i, attempt in enumerate(attempts):
                browser = self.browser_strategies[i % len(self.browser_strategies)]
                browser_assignments.append({
                    'browser': browser,
                    'attempt': attempt,
                    'strategy': 'refresh_staggered'
                })
            
            plan = {
                'time_slot': time_slot,
                'total_attempts': len(priority_users),
                'initial_attempts': len(attempts),
                'browser_assignments': browser_assignments,
                'confirmed_users': confirmed_users,
                'waitlisted_users': waitlisted_users,
                'overflow_count': len(waitlisted_users)
            }
            
            self._log_plan(plan)
            return plan
    
    def handle_booking_result(self, reservation_id: str, success: bool, 
                            court_booked: Optional[int] = None) -> Optional[Dict]:
        """
        Handle booking result and determine if fallback is needed
        
        Returns:
            Fallback plan if needed, None otherwise
        """
        with self.lock:
            attempt = self.active_attempts.get(reservation_id)
            if not attempt:
                return None
            
            if success:
                # Mark as successful
                attempt.status = BookingStatus.SUCCESS
                self.successful_bookings.add(reservation_id)
                if court_booked:
                    self.court_status[court_booked] = 'booked'
                    
                self.logger.info(f"""BOOKING SUCCESS
                Reservation ID: {reservation_id}
                User ID: {attempt.user_id}
                Court booked: {court_booked}
                Total successful bookings: {len(self.successful_bookings)}
                """)
                return None
            
            else:
                # Booking failed - check for fallback options
                self.logger.warning(f"""BOOKING FAILED
                Reservation ID: {reservation_id}
                User ID: {attempt.user_id}
                Failed court: {attempt.target_court}
                Checking fallback options...
                """)
                
                # Mark current court as still available (failed to book)
                if attempt.target_court in self.court_status:
                    self.court_status[attempt.target_court] = 'available'
                
                # Find next available court from fallbacks
                fallback_court = None
                for court in attempt.fallback_courts:
                    if self.court_status.get(court) == 'available':
                        fallback_court = court
                        break
                
                if fallback_court:
                    # Create fallback plan
                    attempt.status = BookingStatus.FALLBACK
                    attempt.target_court = fallback_court
                    self.court_status[fallback_court] = 'attempting'
                    
                    remaining = [c for c in attempt.fallback_courts 
                               if c != fallback_court and 
                               self.court_status.get(c) == 'available']
                    
                    self.logger.info(f"""FALLBACK PLAN CREATED
                    Reservation ID: {reservation_id}
                    New target court: {fallback_court}
                    Remaining fallbacks: {remaining}
                    """)
                    
                    return {
                        'reservation_id': reservation_id,
                        'fallback_court': fallback_court,
                        'remaining_fallbacks': remaining
                    }
                else:
                    # No fallbacks available
                    attempt.status = BookingStatus.FAILED
                    self.logger.error(f"""NO FALLBACK COURTS AVAILABLE
                    Reservation ID: {reservation_id}
                    User ID: {attempt.user_id}
                    All courts exhausted
                    """)
                    return None
    
    def get_dynamic_court_assignment(self, reservation_id: str) -> Optional[int]:
        """Get current court assignment for a reservation"""
        with self.lock:
            attempt = self.active_attempts.get(reservation_id)
            return attempt.target_court if attempt else None
    
    def is_court_available(self, court: int) -> bool:
        """Check if a court is available for booking"""
        with self.lock:
            return self.court_status.get(court, 'available') == 'available'
    
    def handle_vip_late_entry(self, vip_user: PriorityUser, current_confirmed: List[PriorityUser],
                             current_waitlist: List[PriorityUser]) -> Dict[str, Any]:
        """
        Handle VIP joining after initial allocation
        
        Args:
            vip_user: New VIP user joining
            current_confirmed: Currently confirmed users
            current_waitlist: Current waitlist
            
        Returns:
            Dict with reallocation results
        """
        with self.lock:
            self.logger.info(f"""VIP LATE ENTRY PROCESSING
            VIP User ID: {vip_user.user_id}
            VIP Tier: {vip_user.tier.name}
            Current confirmed: {len(current_confirmed)}
            Current waitlist: {len(current_waitlist)}
            """)
            
            # Use priority manager to handle VIP bump
            all_users = current_confirmed + current_waitlist + [vip_user]
            bump_result = self.priority_manager.handle_vip_bump(
                vip_user, all_users, num_browsers=3
            )
            
            # Track who got bumped
            if bump_result['bumped_user']:
                bumped = bump_result['bumped_user']
                self.bumped_users[bumped.reservation_id] = vip_user.user_id
                self.logger.info(f"""VIP BUMP OCCURRED
                VIP {vip_user.user_id} bumped User {bumped.user_id} ({bumped.tier.name})
                Bumped user moved to waitlist position {len(current_waitlist) + 1}
                """)
            else:
                self.logger.info("VIP added without bumping anyone")
            
            return bump_result
    
    def get_booking_summary(self) -> Dict[str, Any]:
        """Get summary of booking attempts"""
        with self.lock:
            summary = {
                'total_attempts': len(self.active_attempts),
                'successful': len(self.successful_bookings),
                'failed': sum(1 for a in self.active_attempts.values() 
                            if a.status == BookingStatus.FAILED),
                'court_status': self.court_status.copy(),
                'bumped_users': len(self.bumped_users),
                'attempts': []
            }
            
            for attempt in self.active_attempts.values():
                summary['attempts'].append({
                    'user_id': attempt.user_id,
                    'target_court': attempt.target_court,
                    'status': attempt.status.value,
                    'fallbacks_remaining': len([c for c in attempt.fallback_courts 
                                              if self.court_status.get(c) == 'available'])
                })
            
            return summary
    
    def get_precision_refresh_moment(self, target_time: datetime) -> datetime:
        """
        Calculate the exact moment to execute a single refresh
        Based on monitoring: slots appear 1.4s before the hour
        
        Returns:
            datetime: The precise moment to refresh
        """
        config = self.precision_refresh_config
        
        # Calculate when slot will appear
        slot_appears = target_time + timedelta(seconds=config['slot_appears_at'])
        
        # Calculate when to start refresh (slot_appears - refresh_duration - margin)
        refresh_moment = slot_appears - timedelta(
            seconds=config['refresh_duration'] + config['safety_margin']
        )
        
        self.logger.info(f"Precision timing for {target_time.strftime('%H:%M')}:")
        self.logger.info(f"  Slot appears: {slot_appears.strftime('%H:%M:%S.%f')[:-3]}")
        self.logger.info(f"  Refresh at: {refresh_moment.strftime('%H:%M:%S.%f')[:-3]}")
        
        return refresh_moment
    
    def should_refresh_now(self, target_time: datetime, current_time: datetime, 
                          last_refresh: Optional[datetime] = None) -> bool:
        """
        Determine if it's time for the precision refresh
        
        Returns:
            bool: True if should refresh now, False otherwise
        """
        refresh_moment = self.get_precision_refresh_moment(target_time)
        seconds_until_refresh = (refresh_moment - current_time).total_seconds()
        
        # If we haven't refreshed yet and it's time
        if last_refresh is None and seconds_until_refresh <= 0:
            return True
            
        # If we're way past the refresh moment and haven't refreshed
        if last_refresh is None and seconds_until_refresh < -5:
            self.logger.warning("Missed precision refresh window! Refreshing now.")
            return True
            
        return False
    
    def get_smart_refresh_interval(self, target_time: datetime, current_time: datetime) -> float:
        """
        Calculate optimal refresh interval based on proximity to target time
        Based on monitoring data: slots appear 1-2 seconds BEFORE the hour
        
        Returns:
            Refresh interval in seconds
        """
        seconds_until_target = (target_time - current_time).total_seconds()
        config = self.smart_refresh_config
        
        # Before the window - normal refresh
        if seconds_until_target > config['pre_window_start']:
            return config['intervals']['normal']
        
        # Pre-rapid phase (-5s to -3s)
        elif config['pre_window_start'] <= seconds_until_target < config['rapid_check_start']:
            return config['intervals']['pre_rapid']
        
        # Rapid phase (-3s to -2s)
        elif config['rapid_check_start'] <= seconds_until_target < config['critical_start']:
            return config['intervals']['rapid']
        
        # CRITICAL WINDOW (-2s to +2s) - Maximum speed!
        elif config['critical_start'] <= seconds_until_target <= config['critical_end']:
            return config['intervals']['critical']
        
        # Post-window slowdown (+2s to +5s)
        elif config['critical_end'] < seconds_until_target <= config['post_window_end']:
            return config['intervals']['rapid']
        
        # After the window - back to normal
        else:
            return config['intervals']['normal']
    
    def reset(self):
        """Reset orchestrator state"""
        with self.lock:
            self.active_attempts.clear()
            self.court_status = {1: 'available', 2: 'available', 3: 'available'}
            self.successful_bookings.clear()
    
    def _log_plan(self, plan: Dict):
        """Log the booking plan"""
        self.logger.info("=" * 60)
        self.logger.info(f"Booking Plan for {plan['time_slot']}:")
        self.logger.info(f"Total users: {plan['total_attempts']}")
        self.logger.info(f"Initial batch: {plan['initial_attempts']} users")
        
        for i, assignment in enumerate(plan['browser_assignments']):
            attempt = assignment['attempt']
            browser = assignment['browser']
            
            if i < plan['initial_attempts']:
                self.logger.info(
                    f"  {browser['id']} (delay {browser['delay']}s): "
                    f"User {attempt.user_id} → Court {attempt.target_court} "
                    f"(fallbacks: {attempt.fallback_courts})"
                )
            else:
                self.logger.info(
                    f"  [Overflow] User {attempt.user_id} → Court {attempt.target_court} "
                    f"(will attempt after initial batch)"
                )
        
        if plan['overflow_count'] > 0:
            self.logger.info(f"Overflow strategy: {plan['overflow_count']} users will be processed after initial batch completes")
        self.logger.info("=" * 60)
