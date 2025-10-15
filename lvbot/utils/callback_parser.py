"""
Callback data parser for Telegram bot callbacks
Handles parsing of various callback data formats
"""

from typing import Optional, Tuple, Dict, Any
from datetime import datetime, date
import logging

logger = logging.getLogger(__name__)


class CallbackParser:
    """Modular callback data parser following DRY principles"""
    
    @staticmethod
    def parse_booking_callback(callback_data: str) -> Optional[Dict[str, Any]]:
        """
        Parse immediate booking callback data
        
        Formats supported:
        - book_now_YYYY-MM-DD_court_HH:MM
        - confirm_book_YYYY-MM-DD_court_HH:MM
        - cancel_book_YYYY-MM-DD
        
        Args:
            callback_data: Raw callback data string
            
        Returns:
            Dict with parsed data or None if invalid
            Keys: action, date, court_number, time (optional)
        """
        try:
            # Determine action type
            if callback_data.startswith('book_now_'):
                action = 'book_now'
                data_part = callback_data.replace('book_now_', '')
            elif callback_data.startswith('confirm_book_'):
                action = 'confirm'
                data_part = callback_data.replace('confirm_book_', '')
            elif callback_data.startswith('cancel_book_'):
                action = 'cancel'
                data_part = callback_data.replace('cancel_book_', '')
            else:
                return None
            
            # Parse based on action
            if action in ['book_now', 'confirm']:
                # Format: YYYY-MM-DD_court_HH:MM
                parts = data_part.split('_')
                if len(parts) != 3:
                    logger.error(f"Invalid booking callback format: {callback_data}")
                    return None
                
                date_str, court_str, time_str = parts
                
                # Validate components
                try:
                    parsed_date = datetime.strptime(date_str, '%Y-%m-%d').date()
                    court_number = int(court_str)
                    # Basic time validation
                    if ':' not in time_str or len(time_str) != 5:
                        raise ValueError(f"Invalid time format: {time_str}")
                    
                    return {
                        'action': action,
                        'date': parsed_date,
                        'court_number': court_number,
                        'time': time_str
                    }
                except (ValueError, TypeError) as e:
                    logger.error(f"Error parsing booking components: {e}")
                    return None
                    
            elif action == 'cancel':
                # Format: YYYY-MM-DD
                try:
                    parsed_date = datetime.strptime(data_part, '%Y-%m-%d').date()
                    return {
                        'action': action,
                        'date': parsed_date
                    }
                except ValueError as e:
                    logger.error(f"Error parsing cancel date: {e}")
                    return None
                    
        except Exception as e:
            logger.error(f"Unexpected error parsing callback: {callback_data}, error: {e}")
            return None
    
    @staticmethod
    def parse_queue_callback(callback_data: str) -> Optional[Dict[str, Any]]:
        """
        Parse queue booking callback data
        
        Formats:
        - queue_time_YYYY-MM-DD_HH:MM
        - queue_court_N or queue_court_all
        
        Args:
            callback_data: Raw callback data string
            
        Returns:
            Dict with parsed data or None if invalid
        """
        try:
            if callback_data.startswith('queue_time_'):
                # Format: queue_time_YYYY-MM-DD_HH:MM
                parts = callback_data.replace('queue_time_', '').split('_')
                if len(parts) != 2:
                    return None
                    
                date_str, time_str = parts
                parsed_date = datetime.strptime(date_str, '%Y-%m-%d').date()
                
                return {
                    'type': 'time_selection',
                    'date': parsed_date,
                    'time': time_str
                }
                
            elif callback_data.startswith('queue_court_'):
                court_part = callback_data.replace('queue_court_', '')
                
                if court_part == 'all':
                    return {
                        'type': 'court_selection',
                        'courts': 'all'
                    }
                else:
                    try:
                        court_number = int(court_part)
                        return {
                            'type': 'court_selection',
                            'courts': [court_number]
                        }
                    except ValueError:
                        return None
                        
        except Exception as e:
            logger.error(f"Error parsing queue callback: {callback_data}, error: {e}")
            return None
    
    @staticmethod
    def format_booking_callback(action: str, date: date, court_number: Optional[int] = None, 
                              time: Optional[str] = None) -> str:
        """
        Format callback data for booking actions
        
        Args:
            action: One of 'book_now', 'confirm_book', 'cancel_book'
            date: Target date
            court_number: Court number (required for book_now/confirm_book)
            time: Time slot (required for book_now/confirm_book)
            
        Returns:
            Formatted callback string
        """
        date_str = date.strftime('%Y-%m-%d')
        
        if action in ['book_now', 'confirm_book']:
            if court_number is None or time is None:
                raise ValueError(f"Court and time required for action: {action}")
            return f"{action}_{date_str}_{court_number}_{time}"
            
        elif action == 'cancel_book':
            return f"{action}_{date_str}"
            
        else:
            raise ValueError(f"Unknown action: {action}")