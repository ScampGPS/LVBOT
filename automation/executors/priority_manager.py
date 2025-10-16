"""
Priority Management System for Tennis Bot
Handles user priority sorting with two-tier FCFS system
"""

from typing import List, Tuple, Dict, Any
from dataclasses import dataclass
from datetime import datetime
from users.manager import UserTier
import logging


@dataclass
class PriorityUser:
    """User data for priority sorting"""
    user_id: int
    tier: UserTier
    created_at: datetime
    reservation_id: str
    court_preferences: List[int]
    
    @classmethod
    def from_reservation(cls, reservation: Dict[str, Any], user_tier: UserTier) -> 'PriorityUser':
        """Create PriorityUser from reservation data"""
        return cls(
            user_id=reservation['user_id'],
            tier=user_tier,
            created_at=datetime.fromisoformat(reservation['created_at']),
            reservation_id=reservation['id'],
            court_preferences=reservation.get('court_preferences', [])
        )


class PriorityManager:
    """Manages user priority sorting with two-tier FCFS system"""
    
    def __init__(self):
        """Initialize the priority manager"""
        self.logger = logging.getLogger('PriorityManager')
        self.logger.info("Priority Manager initialized with two-tier FCFS system")
    
    def sort_by_priority(self, users: List[PriorityUser]) -> List[PriorityUser]:
        """
        Sort users by two-tier FCFS: Admins first, then VIPs, then Regular (each tier FCFS)
        
        Args:
            users: List of users to sort
            
        Returns:
            Sorted list with highest priority first
        """
        self.logger.debug(f"Sorting {len(users)} users by priority")
        
        # Count by tier
        tier_counts = {UserTier.ADMIN: 0, UserTier.VIP: 0, UserTier.REGULAR: 0}
        for user in users:
            tier_counts[user.tier] += 1
        
        self.logger.info(f"User tier distribution: ADMIN={tier_counts[UserTier.ADMIN]}, VIP={tier_counts[UserTier.VIP]}, REGULAR={tier_counts[UserTier.REGULAR]}")
        
        # Sort by tier value (lower is higher priority) and then by creation time
        sorted_users = sorted(users, key=lambda u: (u.tier.value, u.created_at))
        
        # Log first few users
        if sorted_users:
            self.logger.debug("Top 5 users after sorting:")
            for i, user in enumerate(sorted_users[:5]):
                self.logger.debug(f"  {i+1}. User {user.user_id} ({user.tier.name}) - Created: {user.created_at}")
        
        return sorted_users
    
    def split_into_tiers(self, users: List[PriorityUser]) -> Dict[UserTier, List[PriorityUser]]:
        """
        Split users into tiers
        
        Args:
            users: List of users to split
            
        Returns:
            Dictionary mapping tier to list of users in that tier
        """
        tiers = {
            UserTier.ADMIN: [],
            UserTier.VIP: [],
            UserTier.REGULAR: []
        }
        
        for user in users:
            tiers[user.tier].append(user)
        
        # Sort each tier by FCFS
        for tier in tiers:
            tiers[tier].sort(key=lambda u: u.created_at)
        
        return tiers
    
    def get_user_position(self, target_user: PriorityUser, all_users: List[PriorityUser]) -> int:
        """
        Get user's position in the priority queue
        
        Args:
            target_user: User to find position for
            all_users: All users in the queue
            
        Returns:
            1-based position in queue (1 is first)
        """
        sorted_users = self.sort_by_priority(all_users)
        
        for i, user in enumerate(sorted_users):
            if user.reservation_id == target_user.reservation_id:
                return i + 1
        
        return -1  # User not found
    
    def allocate_to_browsers(self, users: List[PriorityUser], num_browsers: int = 3) -> Tuple[List[PriorityUser], List[PriorityUser]]:
        """
        Allocate users to available browsers based on priority
        
        Args:
            users: List of users to allocate
            num_browsers: Number of available browsers (default 3)
            
        Returns:
            Tuple of (confirmed_users, waitlisted_users)
        """
        self.logger.info(f"""BROWSER ALLOCATION START
        Total users: {len(users)}
        Available browsers: {num_browsers}
        """)
        
        sorted_users = self.sort_by_priority(users)
        
        # First num_browsers users get confirmed
        confirmed = sorted_users[:num_browsers]
        waitlisted = sorted_users[num_browsers:]
        
        self.logger.info(f"""ALLOCATION RESULTS
        Confirmed: {len(confirmed)} users
        Waitlisted: {len(waitlisted)} users
        """)
        
        # Log confirmed users
        for i, user in enumerate(confirmed):
            self.logger.info(f"  Browser {i+1}: User {user.user_id} ({user.tier.name})")
        
        # Log first few waitlisted
        if waitlisted:
            self.logger.info("Waitlisted users:")
            for i, user in enumerate(waitlisted[:3]):
                self.logger.info(f"  Position {i+1}: User {user.user_id} ({user.tier.name})")
            if len(waitlisted) > 3:
                self.logger.info(f"  ... and {len(waitlisted) - 3} more users")
        
        return confirmed, waitlisted
    
    def handle_vip_bump(self, new_vip: PriorityUser, current_users: List[PriorityUser], 
                       num_browsers: int = 3) -> Dict[str, Any]:
        """
        Handle VIP joining after regular users confirmed
        
        Args:
            new_vip: New VIP user joining
            current_users: Current users (including confirmed)
            num_browsers: Number of browsers
            
        Returns:
            Dict with bump_info including who gets bumped
        """
        self.logger.info(f"""VIP BUMP HANDLER
        VIP User: {new_vip.user_id} ({new_vip.tier.name})
        Current queue size: {len(current_users)}
        """)
        
        # Add VIP to users and re-sort
        all_users = current_users + [new_vip]
        confirmed, waitlisted = self.allocate_to_browsers(all_users, num_browsers)
        
        # Find who got bumped
        bumped_user = None
        for user in current_users[:num_browsers]:  # Check previously confirmed users
            if user not in confirmed:
                bumped_user = user
                break
        
        vip_position = confirmed.index(new_vip) + 1 if new_vip in confirmed else -1
        
        if bumped_user:
            self.logger.warning(f"""USER BUMPED BY VIP
            Bumped User: {bumped_user.user_id} ({bumped_user.tier.name})
            Bumped by: {new_vip.user_id} ({new_vip.tier.name})
            VIP took position: {vip_position}
            """)
        else:
            if vip_position > 0:
                self.logger.info(f"VIP {new_vip.user_id} secured position {vip_position} without bumping anyone")
            else:
                waitlist_pos = waitlisted.index(new_vip) + 1 if new_vip in waitlisted else -1
                self.logger.info(f"VIP {new_vip.user_id} added to waitlist at position {waitlist_pos}")
        
        return {
            'new_confirmed': confirmed,
            'new_waitlisted': waitlisted,
            'bumped_user': bumped_user,
            'vip_position': vip_position
        }
