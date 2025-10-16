"""
Smart Browser Allocation Helper
Determines which courts need browsers based on queued reservations
"""

from typing import List, Dict, Set, Tuple
from collections import defaultdict
import logging


class BrowserAllocationHelper:
    """Determine optimal browser allocation based on reservation queue"""
    
    @staticmethod
    def analyze_court_needs(reservations: List) -> Dict[str, Set[int]]:
        """
        Analyze reservations to determine which courts need browsers
        
        Args:
            reservations: List of reservation requests
            
        Returns:
            Dict mapping time slots to set of courts that need browsers
            Example: {'09:00': {1, 3}, '10:00': {2, 3}}
        """
        court_needs = defaultdict(set)
        
        # Group reservations by time
        time_groups = defaultdict(list)
        for reservation in reservations:
            time_groups[reservation.time].append(reservation)
        
        # For each time slot, determine which courts need browsers
        for time_slot, time_reservations in time_groups.items():
            courts_requested = set()
            
            # If only one reservation, only need browser for their first choice
            if len(time_reservations) == 1:
                res = time_reservations[0]
                if res.courts:  # courts is the preference list
                    court_needs[time_slot].add(res.courts[0])
            else:
                # Multiple reservations - need smart allocation
                # Sort by priority (admin first)
                time_reservations.sort(key=lambda r: (r.priority, r.created_at))
                
                # Allocate courts to avoid conflicts
                allocated_courts = set()
                for i, res in enumerate(time_reservations[:3]):  # Max 3 courts
                    # Try to allocate their preferred court
                    allocated = False
                    for court in res.courts:
                        if court not in allocated_courts:
                            allocated_courts.add(court)
                            allocated = True
                            break
                    
                    # If couldn't allocate preference, try any available
                    if not allocated and len(allocated_courts) < 3:
                        for court in [1, 2, 3]:
                            if court not in allocated_courts:
                                allocated_courts.add(court)
                                break
                
                court_needs[time_slot] = allocated_courts
        
        return dict(court_needs)
    
    @staticmethod
    def get_browser_requirements(court_needs: Dict[str, Set[int]]) -> Dict[int, List[str]]:
        """
        Convert court needs into browser requirements
        
        Args:
            court_needs: Dict mapping time slots to courts
            
        Returns:
            Dict mapping court numbers to list of time slots
            Example: {1: ['09:00', '10:00'], 3: ['09:00']}
        """
        browser_requirements = defaultdict(list)
        
        for time_slot, courts in court_needs.items():
            for court in courts:
                browser_requirements[court].append(time_slot)
        
        return dict(browser_requirements)
    
    @staticmethod
    def optimize_browser_pool_size(court_needs: Dict[str, Set[int]]) -> int:
        """
        Determine optimal number of browsers to create
        
        Returns:
            Number of browsers needed (max courts at any time slot)
        """
        if not court_needs:
            return 0
            
        max_courts_needed = max(len(courts) for courts in court_needs.values())
        return min(max_courts_needed, 3)  # Never more than 3 courts
    
    @staticmethod
    def should_use_refresh_strategy(time_slots: List[str]) -> bool:
        """
        Determine if refresh strategy is better than pre-positioning
        
        Args:
            time_slots: List of time slots to monitor
            
        Returns:
            True if refresh strategy is recommended
        """
        # If monitoring many different time slots, refresh is better
        # If focused on 1-2 slots, pre-positioning is better
        return len(set(time_slots)) > 2
    
    @staticmethod
    def log_allocation_plan(court_needs: Dict[str, Set[int]], logger: logging.Logger):
        """Log the browser allocation plan for debugging"""
        
        if not court_needs:
            logger.info("No browsers needed - no queued reservations")
            return
            
        logger.info("Browser Allocation Plan:")
        
        # Count total browsers needed
        all_courts = set()
        for courts in court_needs.values():
            all_courts.update(courts)
        
        logger.info(f"  Total browsers needed: {len(all_courts)}")
        logger.info(f"  Courts to monitor: {sorted(all_courts)}")
        
        # Log per time slot
        for time_slot in sorted(court_needs.keys()):
            courts = sorted(court_needs[time_slot])
            logger.info(f"  {time_slot}: Courts {courts}")
        
        # Log efficiency
        total_slots = sum(len(courts) for courts in court_needs.values())
        efficiency = (total_slots / (len(all_courts) * len(court_needs))) * 100 if all_courts else 0
        logger.info(f"  Browser utilization: {efficiency:.1f}%")