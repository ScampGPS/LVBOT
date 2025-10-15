"""
Reservation Queue Management Module

This module provides the ReservationQueue class for managing queued reservation requests.
It handles storage, retrieval, and status updates of reservation requests with JSON persistence.
"""

import json
import uuid
import logging
from datetime import datetime
from typing import List, Dict, Any, Optional, Iterable
from pathlib import Path
from enum import Enum

from lvbot.domain.models import ReservationRequest, UserProfile


class ReservationStatus(Enum):
    """Reservation status states for enhanced queue management"""
    PENDING = "pending"                    # Waiting for booking window
    SCHEDULED = "scheduled"                # Ready to be executed
    CONFIRMED = "confirmed"                # In top 3, will be booked
    WAITLISTED = "waitlisted"             # In waitlist queue
    BOOKING_IN_PROGRESS = "booking"       # Currently being booked
    SUCCESS = "success"                   # Successfully booked
    FAILED = "failed"                     # Booking failed
    BUMPED = "bumped"                     # Bumped by VIP
    CANCELLED = "cancelled"               # User cancelled
    EXPIRED = "expired"                   # Waitlist expired


class ReservationQueue:
    """
    Manages the storage, retrieval, and status updates of reservation requests.
    
    This class provides a persistent queue for managing tennis court reservation requests,
    storing them in a JSON file and providing methods for queue operations.
    
    Attributes:
        file_path (str): Path to the JSON file for persistence
        queue (List[Dict[str, Any]]): In-memory list of reservation dictionaries
        logger (logging.Logger): Logger instance for this class
    """
    
    def __init__(self, file_path: str = 'queue.json'):
        """
        Initialize the ReservationQueue.
        
        Args:
            file_path (str): Path to the JSON file for persistence. Defaults to 'queue.json'.
        """
        self.file_path = file_path
        self.logger = logging.getLogger('ReservationQueue')
        self.queue = self._load_queue()
        self.logger.info(f"""RESERVATION QUEUE INITIALIZED
        File: {self.file_path}
        Existing reservations: {len(self.queue)}
        Status breakdown: {self._get_status_counts()}
        """)
    
    def add_reservation(self, reservation_data: Dict[str, Any]) -> str:
        """
        Add a new reservation to the queue.
        
        Args:
            reservation_data (Dict[str, Any]): Reservation data dictionary
            
        Returns:
            str: Unique reservation ID assigned to the new reservation
        """
        from datetime import datetime, timedelta
        import pytz
        from lvbot.utils.constants import TEST_MODE_ENABLED, TEST_MODE_TRIGGER_DELAY_MINUTES
        
        # Log detailed reservation request
        self.logger.info(f"""NEW RESERVATION REQUEST
        User ID: {reservation_data.get('user_id')}
        User Name: {reservation_data.get('first_name', 'Unknown')}
        Date: {reservation_data.get('target_date')}
        Time: {reservation_data.get('target_time')}
        Court: {reservation_data.get('court_number', 'Any')}
        Players: {reservation_data.get('players', [])}
        """)
        
        # Check for duplicate reservations
        user_id = reservation_data.get('user_id')
        target_date = reservation_data.get('target_date')
        target_time = reservation_data.get('target_time')
        
        # Check if user already has a reservation for this date/time
        existing_reservations = self.get_reservations_by_time_slot(target_date, target_time)
        for existing in existing_reservations:
            if (existing.get('user_id') == user_id and 
                existing.get('status') in ['pending', 'scheduled', 'attempting']):
                self.logger.warning(f"""DUPLICATE RESERVATION REJECTED
                User {user_id} already has a reservation for {target_date} at {target_time}
                Existing reservation ID: {existing.get('id')}
                """)
                raise ValueError(f"You already have a reservation for {target_date} at {target_time}")
        
        reservation_id = uuid.uuid4().hex
        reservation = {
            'id': reservation_id,
            'status': 'pending',
            **reservation_data
        }
        
        # Calculate scheduled execution time
        tz = pytz.timezone('America/Guatemala')
        
        if TEST_MODE_ENABLED:
            # In test mode, schedule execution X minutes from now
            scheduled_time = datetime.now(tz) + timedelta(minutes=TEST_MODE_TRIGGER_DELAY_MINUTES)
            reservation['status'] = 'scheduled'
            self.logger.info(f"TEST MODE: Scheduling execution in {TEST_MODE_TRIGGER_DELAY_MINUTES} minutes")
        else:
            # Normal mode: schedule 48 hours before the target time
            target_date = datetime.strptime(reservation_data['target_date'], '%Y-%m-%d').date()
            target_time = datetime.strptime(reservation_data['target_time'], '%H:%M').time()
            target_datetime = datetime.combine(target_date, target_time)
            target_datetime = tz.localize(target_datetime)
            
            # Schedule execution 30 seconds before 48-hour window opens
            scheduled_time = target_datetime - timedelta(hours=48) - timedelta(seconds=30)
            
            # If scheduled time is in the past, schedule immediately
            if scheduled_time <= datetime.now(tz):
                scheduled_time = datetime.now(tz) + timedelta(minutes=1)
                reservation['status'] = 'scheduled'
            else:
                reservation['status'] = 'scheduled'
        
        reservation['scheduled_execution'] = scheduled_time.isoformat()
        
        self.queue.append(reservation)
        self._save_queue()
        
        # Log successful addition
        self.logger.info(f"""RESERVATION ADDED SUCCESSFULLY
        Reservation ID: {reservation_id}
        User ID: {reservation_data.get('user_id')}
        Status: {reservation['status']}
        Scheduled execution: {scheduled_time}
        Total queue size: {len(self.queue)}
        """)
        return reservation_id

    def add_reservation_request(self, request: ReservationRequest) -> str:
        """Add a dataclass reservation request to the queue."""

        payload = {
            'user_id': request.user.user_id,
            'first_name': request.user.first_name,
            'last_name': request.user.last_name,
            'email': request.user.email,
            'phone': request.user.phone,
            'tier': request.user.tier,
            'target_date': request.target_date.isoformat(),
            'target_time': request.target_time,
            'court_preferences': request.court_preferences,
            'created_at': request.created_at.isoformat(),
            'status': request.status,
        }

        reservation_id = self.add_reservation(payload)
        return reservation_id

    def list_reservations(self) -> List[ReservationRequest]:
        """Return reservations as dataclasses."""

        results: List[ReservationRequest] = []
        for item in self.queue:
            user = UserProfile(
                user_id=item.get('user_id'),
                first_name=item.get('first_name', ''),
                last_name=item.get('last_name', ''),
                email=item.get('email', ''),
                phone=item.get('phone', ''),
                tier=item.get('tier'),
            )
            request = ReservationRequest(
                request_id=item.get('id'),
                user=user,
                target_date=datetime.fromisoformat(item['target_date']).date()
                if isinstance(item.get('target_date'), str)
                else item.get('target_date'),
                target_time=item.get('target_time'),
                court_preferences=item.get('court_preferences', []),
                created_at=datetime.fromisoformat(item['created_at'])
                if isinstance(item.get('created_at'), str)
                else item.get('created_at'),
                status=item.get('status', 'pending'),
            )
            results.append(request)
        return results
    
    def get_reservation(self, reservation_id: str) -> Optional[Dict[str, Any]]:
        """
        Retrieve a single reservation by its unique ID.
        
        Args:
            reservation_id (str): Unique reservation identifier
            
        Returns:
            Optional[Dict[str, Any]]: Reservation dictionary if found, None otherwise
        """
        for reservation in self.queue:
            if reservation.get('id') == reservation_id:
                return reservation
        return None
    
    def get_user_reservations(self, user_id: int) -> List[Dict[str, Any]]:
        """
        Retrieve all reservations associated with a given user_id.
        
        Args:
            user_id (int): Telegram user ID
            
        Returns:
            List[Dict[str, Any]]: List of reservation dictionaries for the user
        """
        user_reservations = [
            reservation for reservation in self.queue 
            if reservation.get('user_id') == user_id
        ]
        
        self.logger.debug(f"Found {len(user_reservations)} reservations for user {user_id}")
        return user_reservations
    
    def get_pending_reservations(self) -> List[Dict[str, Any]]:
        """
        Return all reservations with status 'pending' or 'scheduled'.
        
        Returns:
            List[Dict[str, Any]]: List of pending/scheduled reservation dictionaries
        """
        pending_reservations = [
            reservation for reservation in self.queue 
            if reservation.get('status') in ['pending', 'scheduled', ReservationStatus.CONFIRMED.value]
        ]
        
        self.logger.debug(f"Found {len(pending_reservations)} pending/scheduled reservations")
        return pending_reservations
    
    def get_reservations_by_time_slot(self, target_date: str, target_time: str) -> List[Dict[str, Any]]:
        """
        Get all reservations for a specific time slot
        
        Args:
            target_date: Date in YYYY-MM-DD format
            target_time: Time in HH:MM format
            
        Returns:
            List of reservations for the specified time slot
        """
        matching_reservations = []
        for reservation in self.queue:
            # Check both 'time' and 'target_time' fields for compatibility
            res_date = reservation.get('target_date')
            res_time = reservation.get('time') or reservation.get('target_time')
            
            if res_date == target_date and res_time == target_time:
                matching_reservations.append(reservation)
        
        # Log time slot query
        self.logger.debug(f"""TIME SLOT QUERY
        Date: {target_date}
        Time: {target_time}
        Found: {len(matching_reservations)} reservations
        Users: {[r.get('user_id') for r in matching_reservations]}
        """)
        
        return matching_reservations
    
    def add_to_waitlist(self, reservation_id: str, position: int) -> bool:
        """
        Add a reservation to waitlist with position
        
        Args:
            reservation_id: Unique reservation identifier
            position: Position in waitlist
            
        Returns:
            True if successful, False if reservation not found
        """
        for reservation in self.queue:
            if reservation.get('id') == reservation_id:
                old_status = reservation.get('status')
                reservation['status'] = ReservationStatus.WAITLISTED.value
                reservation['waitlist_position'] = position
                reservation['original_position'] = position
                self._save_queue()
                
                # Log waitlist addition
                self.logger.info(f"""ADDED TO WAITLIST
                Reservation ID: {reservation_id}
                User ID: {reservation.get('user_id')}
                User Name: {reservation.get('first_name', 'Unknown')}
                Time Slot: {reservation.get('target_date')} {reservation.get('target_time')}
                Waitlist Position: {position}
                Previous Status: {old_status}
                """)
                return True
        
        self.logger.warning(f"Failed to add reservation {reservation_id} to waitlist - not found")
        return False
    
    def get_waitlist_for_slot(self, target_date: str, target_time: str) -> List[Dict[str, Any]]:
        """
        Get all waitlisted reservations for a time slot, sorted by position
        
        Args:
            target_date: Date in YYYY-MM-DD format
            target_time: Time in HH:MM format
            
        Returns:
            List of waitlisted reservations sorted by position
        """
        waitlisted = []
        for reservation in self.queue:
            res_date = reservation.get('target_date')
            res_time = reservation.get('time') or reservation.get('target_time')
            
            if (res_date == target_date and res_time == target_time and 
                reservation.get('status') == ReservationStatus.WAITLISTED.value):
                waitlisted.append(reservation)
        
        # Sort by waitlist position
        waitlisted.sort(key=lambda x: x.get('waitlist_position', float('inf')))
        return waitlisted
    
    def update_reservation_status(self, reservation_id: str, new_status: str, **kwargs) -> bool:
        """
        Update the status of a reservation and optionally other fields.
        
        Args:
            reservation_id (str): Unique reservation identifier
            new_status (str): New status value
            **kwargs: Additional fields to update (e.g., attempts, confirmation_code)
            
        Returns:
            bool: True if update was successful, False if reservation not found
        """
        for reservation in self.queue:
            if reservation.get('id') == reservation_id:
                old_status = reservation.get('status')
                reservation['status'] = new_status
                
                # Update additional fields from kwargs
                for key, value in kwargs.items():
                    reservation[key] = value
                
                self._save_queue()
                
                # Log detailed status change
                self.logger.info(f"""RESERVATION STATUS UPDATED
                Reservation ID: {reservation_id}
                User ID: {reservation.get('user_id')}
                User Name: {reservation.get('first_name', 'Unknown')}
                Time Slot: {reservation.get('target_date')} {reservation.get('target_time')}
                Status Change: {old_status} → {new_status}
                Additional Updates: {kwargs}
                """)
                return True
        
        self.logger.warning(f"Reservation {reservation_id} not found for status update")
        return False
    
    def remove_reservation(self, reservation_id: str) -> bool:
        """
        Remove a reservation from the queue by its ID.
        
        Args:
            reservation_id (str): Unique reservation identifier
            
        Returns:
            bool: True if removed successfully, False if reservation not found
        """
        for i, reservation in enumerate(self.queue):
            if reservation.get('id') == reservation_id:
                removed_reservation = self.queue.pop(i)
                self._save_queue()
                
                self.logger.info(
                    f"Removed reservation {reservation_id} for user {removed_reservation.get('user_id')}"
                )
                return True
        
        self.logger.warning(f"Reservation {reservation_id} not found for removal")
        return False
    
    def update_reservation(self, reservation_id: str, updated_data: Dict[str, Any]) -> bool:
        """
        Update an existing reservation with new data
        
        Args:
            reservation_id: The ID of the reservation to update
            updated_data: Dictionary with updated reservation data
            
        Returns:
            bool: True if update was successful, False if reservation not found
        """
        for i, reservation in enumerate(self.queue):
            if reservation.get('id') == reservation_id:
                # Update the reservation while preserving the ID
                updated_data['id'] = reservation_id
                self.queue[i] = updated_data
                self._save_queue()
                
                self.logger.info(f"Updated reservation {reservation_id}")
                return True
        
        self.logger.warning(f"Reservation {reservation_id} not found for update")
        return False
    
    def _save_queue(self) -> None:
        """
        Internal helper method to save the current queue state to JSON file.
        
        Handles file operation errors gracefully and logs any issues.
        """
        try:
            # Ensure directory exists
            Path(self.file_path).parent.mkdir(parents=True, exist_ok=True)
            
            with open(self.file_path, 'w', encoding='utf-8') as f:
                json.dump(self.queue, f, indent=2, ensure_ascii=False)
            
            self.logger.debug(f"Queue saved to {self.file_path} with {len(self.queue)} reservations")
            
        except Exception as e:
            self.logger.error(f"Failed to save queue to {self.file_path}: {e}")
    
    def _load_queue(self) -> List[Dict[str, Any]]:
        """
        Internal helper method to load the queue from JSON file.
        
        Returns:
            List[Dict[str, Any]]: List of reservation dictionaries, empty list if file doesn't exist
        """
        try:
            if Path(self.file_path).exists():
                with open(self.file_path, 'r', encoding='utf-8') as f:
                    queue_data = json.load(f)
                
                # Ensure we have a list
                if isinstance(queue_data, list):
                    self.logger.debug(f"Loaded {len(queue_data)} reservations from {self.file_path}")
                    return queue_data
                else:
                    self.logger.warning(f"Invalid queue format in {self.file_path}, starting with empty queue")
                    return []
            else:
                self.logger.debug(f"Queue file {self.file_path} does not exist, starting with empty queue")
                return []
                
        except Exception as e:
            self.logger.error(f"Failed to load queue from {self.file_path}: {e}")
            return []
    
    def _get_status_counts(self) -> Dict[str, int]:
        """
        Get counts of reservations by status
        
        Returns:
            Dictionary mapping status to count
        """
        from collections import Counter
        status_counts = Counter(r.get('status', 'unknown') for r in self.queue)
        return dict(status_counts)
