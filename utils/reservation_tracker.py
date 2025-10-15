"""
Reservation Tracker Module

Tracks all reservations including:
- Queued reservations (from ReservationQueue)
- Immediate reservations made within 48h window
- Completed reservations with confirmation IDs
"""

import json
import logging
from typing import List, Dict, Any, Optional
from datetime import datetime, timedelta
from pathlib import Path


class ReservationTracker:
    """
    Unified tracker for all types of reservations
    """
    
    def __init__(self, file_path: str = 'data/all_reservations.json'):
        """
        Initialize the reservation tracker
        
        Args:
            file_path: Path to JSON file for persistence
        """
        self.file_path = file_path
        self.logger = logging.getLogger('ReservationTracker')
        self.reservations = self._load_reservations()
        
    def add_immediate_reservation(self, user_id: int, reservation_data: Dict[str, Any]) -> str:
        """
        Add an immediate reservation (made within 48h window)
        
        Args:
            user_id: Telegram user ID
            reservation_data: Should contain court, date, time, confirmation_url, etc.
            
        Returns:
            Reservation ID
        """
        reservation_id = f"imm_{datetime.now().strftime('%Y%m%d%H%M%S')}_{user_id}"
        
        reservation = {
            'id': reservation_id,
            'user_id': user_id,
            'type': 'immediate',
            'status': 'confirmed',
            'created_at': datetime.now().isoformat(),
            **reservation_data
        }
        
        self.reservations[reservation_id] = reservation
        self._save_reservations()
        
        self.logger.info(f"Added immediate reservation {reservation_id} for user {user_id}")
        return reservation_id
    
    def add_completed_booking(self, user_id: int, booking_result: Dict[str, Any]) -> str:
        """
        Add a completed booking with confirmation details
        
        Args:
            user_id: Telegram user ID
            booking_result: Booking result including confirmation_id, court, time, etc.
            
        Returns:
            Reservation ID
        """
        reservation_id = f"conf_{booking_result.get('confirmation_id', datetime.now().strftime('%Y%m%d%H%M%S'))}"
        
        reservation = {
            'id': reservation_id,
            'user_id': user_id,
            'type': 'completed',
            'status': 'active',
            'created_at': datetime.now().isoformat(),
            'confirmation_id': booking_result.get('confirmation_id'),
            'confirmation_url': booking_result.get('confirmation_url'),
            'court': booking_result.get('court'),
            'date': booking_result.get('date'),
            'time': booking_result.get('time'),
            'can_cancel': True,  # Acuity allows cancellation
            'can_modify': True,  # Acuity allows modification
        }
        
        self.reservations[reservation_id] = reservation
        self._save_reservations()
        
        self.logger.info(f"Added completed booking {reservation_id} for user {user_id}")
        return reservation_id
    
    def get_user_active_reservations(self, user_id: int) -> List[Dict[str, Any]]:
        """
        Get all active reservations for a user (immediate, queued, and completed)
        
        Args:
            user_id: Telegram user ID
            
        Returns:
            List of active reservations
        """
        user_reservations = []
        
        # Get reservations from this tracker
        for res_id, res_data in self.reservations.items():
            if res_data.get('user_id') == user_id and res_data.get('status') in ['confirmed', 'active', 'pending']:
                # Check if reservation is still in the future
                try:
                    res_date = datetime.fromisoformat(res_data.get('date', ''))
                    res_time = datetime.strptime(res_data.get('time', '00:00'), '%H:%M').time()
                    res_datetime = datetime.combine(res_date.date(), res_time)
                    
                    if res_datetime > datetime.now():
                        user_reservations.append(res_data)
                except Exception as e:
                    self.logger.warning(f"Error parsing date/time for reservation {res_id}: {e}")
        
        return sorted(user_reservations, key=lambda x: (x.get('date', ''), x.get('time', '')))
    
    def cancel_reservation(self, reservation_id: str) -> bool:
        """
        Cancel a reservation
        
        Args:
            reservation_id: Reservation ID to cancel
            
        Returns:
            True if cancelled successfully
        """
        if reservation_id in self.reservations:
            self.reservations[reservation_id]['status'] = 'cancelled'
            self.reservations[reservation_id]['cancelled_at'] = datetime.now().isoformat()
            self._save_reservations()
            self.logger.info(f"Cancelled reservation {reservation_id}")
            return True
        return False
    
    def get_reservation(self, reservation_id: str) -> Optional[Dict[str, Any]]:
        """
        Get a specific reservation by ID
        
        Args:
            reservation_id: Reservation ID
            
        Returns:
            Reservation data or None
        """
        return self.reservations.get(reservation_id)
    
    def update_reservation(self, reservation_id: str, updates: Dict[str, Any]) -> bool:
        """
        Update reservation data
        
        Args:
            reservation_id: Reservation ID
            updates: Fields to update
            
        Returns:
            True if updated successfully
        """
        if reservation_id in self.reservations:
            self.reservations[reservation_id].update(updates)
            self.reservations[reservation_id]['updated_at'] = datetime.now().isoformat()
            self._save_reservations()
            return True
        return False
    
    def cleanup_old_reservations(self, days_to_keep: int = 30):
        """
        Remove reservations older than specified days
        
        Args:
            days_to_keep: Number of days to keep past reservations
        """
        cutoff_date = datetime.now() - timedelta(days=days_to_keep)
        removed_count = 0
        
        for res_id in list(self.reservations.keys()):
            res_data = self.reservations[res_id]
            try:
                created_at = datetime.fromisoformat(res_data.get('created_at', ''))
                if created_at < cutoff_date:
                    del self.reservations[res_id]
                    removed_count += 1
            except Exception as e:
                self.logger.warning(f"Error checking reservation age for {res_id}: {e}")
        
        if removed_count > 0:
            self._save_reservations()
            self.logger.info(f"Cleaned up {removed_count} old reservations")
    
    def _save_reservations(self):
        """Save reservations to JSON file"""
        try:
            Path(self.file_path).parent.mkdir(parents=True, exist_ok=True)
            with open(self.file_path, 'w', encoding='utf-8') as f:
                json.dump(self.reservations, f, indent=2, ensure_ascii=False)
        except Exception as e:
            self.logger.error(f"Failed to save reservations: {e}")
    
    def _load_reservations(self) -> Dict[str, Dict[str, Any]]:
        """Load reservations from JSON file"""
        try:
            if Path(self.file_path).exists():
                with open(self.file_path, 'r', encoding='utf-8') as f:
                    return json.load(f)
        except Exception as e:
            self.logger.error(f"Failed to load reservations: {e}")
        return {}