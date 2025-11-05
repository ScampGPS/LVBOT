"""
Reservation Queue Management Module

This module provides the ReservationQueue class for managing queued reservation requests.
It handles storage, retrieval, and status updates of reservation requests with JSON persistence.
"""
from tracking import t

import uuid
import logging
from datetime import datetime, timedelta
from typing import Any, Dict, List, Mapping, Optional, Union
from enum import Enum

from reservations.models import ReservationRequest
from reservations.queue.reservation_repository import ReservationRepository
from reservations.queue.reservation_validation import ensure_unique_slot
from reservations.queue.reservation_transitions import (
    add_to_waitlist as mark_waitlisted,
    apply_status_update,
)
from reservations.queue.request_builder import (
    ReservationRequestBuilder,
    DEFAULT_BUILDER,
)
from infrastructure.settings import get_test_mode
import pytz


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


class QueueRecordSerializer:
    """Serialize and hydrate queue reservation records."""

    def __init__(
        self,
        builder: ReservationRequestBuilder = DEFAULT_BUILDER,
    ) -> None:
        self._builder = builder

    def to_storage(self, reservation: ReservationRequest) -> Dict[str, Any]:
        return dict(self._builder.to_payload(reservation))

    def from_storage(self, payload: Mapping[str, Any]) -> ReservationRequest:
        return self._builder.record_from_payload(payload)

    def normalise_payload(self, payload: Mapping[str, Any]) -> Dict[str, Any]:
        record = self.from_storage(payload)
        return self.to_storage(record)


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
    
    def __init__(
        self,
        file_path: str = 'data/queue.json',
        *,
        builder: ReservationRequestBuilder | None = None,
    ):
        """
        Initialize the ReservationQueue.

        Args:
            file_path (str): Path to the JSON file for persistence. Defaults to 'data/queue.json'.
        """
        t('reservations.queue.reservation_queue.ReservationQueue.__init__')
        self.logger = logging.getLogger('ReservationQueue')
        self._builder = builder or ReservationRequestBuilder()
        self._serializer = QueueRecordSerializer(self._builder)
        self.repository = ReservationRepository(file_path, logger=self.logger)
        self.file_path = file_path
        self.queue = self.repository.load()
        repaired = self._normalise_loaded_entries()
        if repaired:
            self.logger.warning(
                "Normalised %s queued reservations missing identifiers or metadata",
                repaired,
            )
            self._save_queue()
        self.logger.info(f"""RESERVATION QUEUE INITIALIZED
        File: {self.file_path}
        Existing reservations: {len(self.queue)}
        Status breakdown: {self._get_status_counts()}
        """)
    
    def add_reservation(self, reservation_data: Union[ReservationRequest, Dict[str, Any]]) -> str:
        """
        Add a new reservation to the queue.

        Args:
            reservation_data: Reservation details (dataclass or legacy dict).

        Returns:
            str: Unique reservation ID assigned to the new reservation
        """
        t('reservations.queue.reservation_queue.ReservationQueue.add_reservation')

        if isinstance(reservation_data, ReservationRequest):
            payload = self._serializer.to_storage(reservation_data)
        else:
            payload = self._serializer.normalise_payload(dict(reservation_data))

        # Ensure freshly generated identifiers and statuses are not overridden by
        # legacy payloads that may contain null values.
        payload.pop('id', None)
        payload.pop('status', None)

        # Log detailed reservation request
        self.logger.info(f"""NEW RESERVATION REQUEST
        User ID: {payload.get('user_id')}
        User Name: {payload.get('first_name', 'Unknown')}
        Date: {payload.get('target_date')}
        Time: {payload.get('target_time')}
        Court: {payload.get('court_number', 'Any')}
        Players: {payload.get('players', [])}
        """)

        # Check for duplicate reservations
        user_id = payload.get('user_id')
        target_date_raw = payload.get('target_date')
        target_time_raw = payload.get('target_time')
        requested_courts = payload.get('court_preferences')
        if (not requested_courts) and payload.get('court_number') is not None:
            requested_courts = [payload.get('court_number')]

        ensure_unique_slot(
            self.queue,
            user_id=user_id,
            target_date=target_date_raw,
            target_time=target_time_raw,
            courts=requested_courts,
            logger=self.logger,
        )

        reservation_id = uuid.uuid4().hex
        reservation = {
            'id': reservation_id,
            'status': ReservationStatus.PENDING.value,
            **payload,
        }

        tz = pytz.timezone('America/Guatemala')
        scheduled_time = self._compute_scheduled_execution(reservation, tz)
        reservation['status'] = ReservationStatus.SCHEDULED.value
        reservation['scheduled_execution'] = scheduled_time.isoformat()

        self.queue.append(reservation)
        self._save_queue()

        # Log successful addition
        self.logger.info(f"""RESERVATION ADDED SUCCESSFULLY
        Reservation ID: {reservation_id}
        User ID: {reservation.get('user_id')}
        Status: {reservation['status']}
        Scheduled execution: {scheduled_time}
        Total queue size: {len(self.queue)}
        """)
        return reservation_id

    def add_reservation_request(self, request: ReservationRequest) -> str:
        """Add a dataclass reservation request to the queue."""
        t('reservations.queue.reservation_queue.ReservationQueue.add_reservation_request')

        return self.add_reservation(request)

    def list_reservations(self) -> List[ReservationRequest]:
        """Return reservations as dataclasses."""
        t('reservations.queue.reservation_queue.ReservationQueue.list_reservations')

        return [self._serializer.from_storage(item) for item in self.queue]

    def _normalise_loaded_entries(self) -> int:
        """Repair queue entries loaded from disk that may lack required metadata."""

        repaired = 0
        tz = pytz.timezone('America/Guatemala')
        now = datetime.now(tz)
        valid_statuses = {status.value for status in ReservationStatus}

        for reservation in self.queue:
            modified = False

            if not reservation.get('id'):
                reservation['id'] = uuid.uuid4().hex
                modified = True

            target_time = reservation.get('target_time')
            if isinstance(target_time, str) and '_' in target_time:
                candidate = target_time.split('_')[-1]
                if len(candidate) == 5 and candidate[2] == ':' and candidate.replace(':', '').isdigit():
                    reservation['target_time'] = candidate
                    modified = True

            status = reservation.get('status')
            if status not in valid_statuses:
                reservation['status'] = ReservationStatus.PENDING.value
                modified = True

            target_dt = self._parse_target_datetime(reservation, tz)
            if target_dt and target_dt < now:
                if reservation.get('status') not in {
                    ReservationStatus.SUCCESS.value,
                    ReservationStatus.CANCELLED.value,
                    ReservationStatus.EXPIRED.value,
                }:
                    reservation['status'] = ReservationStatus.EXPIRED.value
                    reservation['expired_at'] = now.isoformat()
                    modified = True

            scheduled_execution = reservation.get('scheduled_execution')
            needs_reschedule = False
            if not scheduled_execution:
                needs_reschedule = True
            else:
                try:
                    datetime.fromisoformat(scheduled_execution)
                except (TypeError, ValueError):
                    needs_reschedule = True

            if needs_reschedule and reservation.get('target_date') and reservation.get('target_time'):
                try:
                    scheduled_dt = self._compute_scheduled_execution(reservation, tz)
                    reservation['scheduled_execution'] = scheduled_dt.isoformat()
                    reservation['status'] = ReservationStatus.SCHEDULED.value
                    modified = True
                except Exception:
                    # Leave entry as-is if we cannot compute; scheduler will skip it.
                    self.logger.error(
                        "Failed to recompute scheduled_execution for reservation %s",
                        reservation.get('id') or '<unknown>',
                    )

            if modified:
                repaired += 1

        return repaired

    @staticmethod
    def _compute_scheduled_execution(reservation: Mapping[str, Any], tz) -> datetime:
        """Compute when a reservation should execute based on configuration."""

        config = get_test_mode()
        if config.enabled:
            delay = max(config.trigger_delay_minutes, 0)
            return datetime.now(tz) + timedelta(minutes=delay)

        target_datetime = ReservationQueue._parse_target_datetime(reservation, tz)
        if target_datetime is None:
            raise ValueError("Reservation missing target date/time")

        scheduled_time = target_datetime - timedelta(hours=48) - timedelta(seconds=30)
        if scheduled_time <= datetime.now(tz):
            scheduled_time = datetime.now(tz) + timedelta(minutes=1)
        return scheduled_time

    @staticmethod
    def _parse_target_datetime(reservation: Mapping[str, Any], tz) -> Optional[datetime]:
        target_date = reservation.get('target_date')
        target_time = reservation.get('target_time')
        if not target_date or not target_time:
            return None

        try:
            date_obj = datetime.strptime(str(target_date), '%Y-%m-%d').date()
            time_obj = datetime.strptime(str(target_time), '%H:%M').time()
        except (TypeError, ValueError):
            return None

        return tz.localize(datetime.combine(date_obj, time_obj))
    
    def get_reservation(self, reservation_id: str) -> Optional[Dict[str, Any]]:
        """
        Retrieve a single reservation by its unique ID.
        
        Args:
            reservation_id (str): Unique reservation identifier
            
        Returns:
            Optional[Dict[str, Any]]: Reservation dictionary if found, None otherwise
        """
        t('reservations.queue.reservation_queue.ReservationQueue.get_reservation')
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
        t('reservations.queue.reservation_queue.ReservationQueue.get_user_reservations')
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
        t('reservations.queue.reservation_queue.ReservationQueue.get_pending_reservations')
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
        t('reservations.queue.reservation_queue.ReservationQueue.get_reservations_by_time_slot')
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
        t('reservations.queue.reservation_queue.ReservationQueue.add_to_waitlist')
        for reservation in self.queue:
            if reservation.get('id') == reservation_id:
                old_status = reservation.get('status')
                mark_waitlisted(reservation, position)
                self._save_queue()

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
        t('reservations.queue.reservation_queue.ReservationQueue.get_waitlist_for_slot')
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
        t('reservations.queue.reservation_queue.ReservationQueue.update_reservation_status')
        for reservation in self.queue:
            if reservation.get('id') == reservation_id:
                old_status = reservation.get('status')
                apply_status_update(reservation, new_status, **kwargs)
                self._save_queue()

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
        t('reservations.queue.reservation_queue.ReservationQueue.remove_reservation')
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
        t('reservations.queue.reservation_queue.ReservationQueue.update_reservation')
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
        t('reservations.queue.reservation_queue.ReservationQueue._save_queue')
        self.repository.save(self.queue)
    
    def _load_queue(self) -> List[Dict[str, Any]]:
        """
        Internal helper method to load the queue from JSON file.
        
        Returns:
            List[Dict[str, Any]]: List of reservation dictionaries, empty list if file doesn't exist
        """
        t('reservations.queue.reservation_queue.ReservationQueue._load_queue')
        return self.repository.load()
    
    def _get_status_counts(self) -> Dict[str, int]:
        """
        Get counts of reservations by status
        
        Returns:
            Dictionary mapping status to count
        """
        t('reservations.queue.reservation_queue.ReservationQueue._get_status_counts')
        from collections import Counter
        status_counts = Counter(r.get('status', 'unknown') for r in self.queue)
        return dict(status_counts)
