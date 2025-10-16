"""
Validation utility functions
Handles input validation for various user inputs
"""
from tracking import t

from typing import Tuple, List, Optional
import re
from datetime import datetime


class ValidationHelpers:
    """Collection of validation helper functions"""
    
    @staticmethod
    def validate_phone_number(phone: str) -> Tuple[bool, str]:
        """
        Validate phone number format
        Returns: (is_valid, cleaned_phone_or_error_message)
        """
        t('botapp.validation.ValidationHelpers.validate_phone_number')
        # Remove all non-digit characters
        digits_only = ''.join(c for c in phone if c.isdigit())
        
        if len(digits_only) == 8:
            return True, digits_only
        elif len(digits_only) < 8:
            return False, f"Phone number too short. Got {len(digits_only)} digits, need 8."
        else:
            return False, f"Phone number too long. Got {len(digits_only)} digits, need 8."
    
    @staticmethod
    def validate_email(email: str) -> Tuple[bool, str]:
        """
        Validate email format
        Returns: (is_valid, cleaned_email_or_error_message)
        """
        t('botapp.validation.ValidationHelpers.validate_email')
        email = email.strip().lower()
        
        # Basic email regex
        email_pattern = r'^[a-zA-Z0-9._%+-]+@[a-zA-Z0-9.-]+\.[a-zA-Z]{2,}$'
        
        if re.match(email_pattern, email):
            return True, email
        else:
            if '@' not in email:
                return False, "Email must contain @ symbol"
            elif '.' not in email.split('@')[1]:
                return False, "Email domain must contain a dot"
            else:
                return False, "Invalid email format"
    
    @staticmethod
    def validate_time_slot(time: str, available_times: List[str]) -> Tuple[bool, str]:
        """
        Validate if time slot is available
        Returns: (is_valid, time_or_error_message)
        """
        t('botapp.validation.ValidationHelpers.validate_time_slot')
        time = time.strip()
        
        if not available_times:
            return False, "No time slots available"
        
        if time not in available_times:
            # Try to find close matches
            close_matches = [t for t in available_times if t.startswith(time[:2])]
            if close_matches:
                return False, f"'{time}' not available. Did you mean: {', '.join(close_matches)}?"
            else:
                return False, f"'{time}' not available. Choose from: {', '.join(available_times)}"
        
        return True, time
    
    @staticmethod
    def validate_court_selection(selection: str, available_courts: List[int]) -> Tuple[bool, List[int], str]:
        """
        Validate court selection
        Returns: (is_valid, court_list, error_message)
        """
        t('botapp.validation.ValidationHelpers.validate_court_selection')
        if not available_courts:
            return False, [], "No courts available"
        
        # Handle "All courts" selection
        if selection.lower() in ['all', 'all courts', 'todos']:
            return True, available_courts, ""
        
        # Handle single court
        if selection.lower().startswith('court '):
            try:
                court_num = int(selection.split()[-1])
                if court_num in available_courts:
                    return True, [court_num], ""
                else:
                    return False, [], f"Court {court_num} not available. Choose from: {available_courts}"
            except ValueError:
                return False, [], "Invalid court number"
        
        # Handle comma-separated list
        if ',' in selection:
            try:
                courts = []
                for part in selection.split(','):
                    court_str = part.strip()
                    if court_str.lower().startswith('court'):
                        court_num = int(court_str.split()[-1])
                    else:
                        court_num = int(court_str)
                    courts.append(court_num)
                
                # Validate all courts
                invalid_courts = [c for c in courts if c not in available_courts]
                if invalid_courts:
                    return False, [], f"Invalid courts: {invalid_courts}. Available: {available_courts}"
                
                # Remove duplicates and sort
                courts = sorted(list(set(courts)))
                return True, courts, ""
                
            except ValueError:
                return False, [], "Invalid court format. Use: 'Court 1' or '1,2,3'"
        
        # Try to parse as single number
        try:
            court_num = int(selection)
            if court_num in available_courts:
                return True, [court_num], ""
            else:
                return False, [], f"Court {court_num} not available. Choose from: {available_courts}"
        except ValueError:
            return False, [], "Invalid input. Use: 'Court 1', '1,2,3', or 'All courts'"
    
    @staticmethod
    def validate_date_selection(date_str: str, min_date: datetime, max_date: datetime) -> Tuple[bool, Optional[datetime], str]:
        """
        Validate date selection
        Returns: (is_valid, date_object, error_message)
        """
        t('botapp.validation.ValidationHelpers.validate_date_selection')
        try:
            # Try multiple date formats
            date_formats = ['%Y-%m-%d', '%m/%d/%Y', '%d/%m/%Y', '%m-%d-%Y', '%d-%m-%Y']
            date_obj = None
            
            for fmt in date_formats:
                try:
                    date_obj = datetime.strptime(date_str, fmt).date()
                    break
                except ValueError:
                    continue
            
            if not date_obj:
                return False, None, "Invalid date format. Use YYYY-MM-DD or MM/DD/YYYY"
            
            # Create datetime for comparison
            date_dt = datetime.combine(date_obj, datetime.min.time())
            date_dt = date_dt.replace(tzinfo=min_date.tzinfo)
            
            # Check bounds
            if date_dt < min_date:
                return False, None, "Date is too early. Cannot book past dates."
            elif date_dt > max_date:
                days_ahead = (date_dt - min_date).days
                return False, None, f"Date is too far ahead. Maximum booking window is {(max_date - min_date).days} days."
            
            return True, date_dt, ""
            
        except Exception as e:
            return False, None, f"Error parsing date: {str(e)}"
    
    @staticmethod
    def validate_name(name: str, field_name: str = "Name") -> Tuple[bool, str]:
        """
        Validate name input
        Returns: (is_valid, cleaned_name_or_error_message)
        """
        t('botapp.validation.ValidationHelpers.validate_name')
        name = name.strip()
        
        if not name:
            return False, f"{field_name} cannot be empty"
        
        if len(name) < 2:
            return False, f"{field_name} too short (minimum 2 characters)"
        
        if len(name) > 50:
            return False, f"{field_name} too long (maximum 50 characters)"
        
        # Check for valid characters (letters, spaces, hyphens, apostrophes)
        if not re.match(r"^[a-zA-ZÀ-ÿĀ-žА-я\s\-'\.]+$", name):
            return False, f"{field_name} contains invalid characters"
        
        # Clean up multiple spaces
        name = ' '.join(name.split())
        
        return True, name
    
    @staticmethod
    def validate_yes_no_response(response: str) -> Tuple[bool, bool, str]:
        """
        Validate yes/no response
        Returns: (is_valid, is_yes, error_message)
        """
        t('botapp.validation.ValidationHelpers.validate_yes_no_response')
        response = response.strip().lower()
        
        yes_responses = ['yes', 'y', 'si', 'sí', 's', 'yeah', 'yep', 'sure', 'ok', 'okay']
        no_responses = ['no', 'n', 'nope', 'nah', 'cancel']
        
        if response in yes_responses:
            return True, True, ""
        elif response in no_responses:
            return True, False, ""
        else:
            return False, False, "Please respond with 'Yes' or 'No'"
    
    @staticmethod
    def validate_priority(priority: str) -> Tuple[bool, int, str]:
        """
        Validate priority selection
        Returns: (is_valid, priority_value, error_message)
        """
        t('botapp.validation.ValidationHelpers.validate_priority')
        priority = priority.strip().lower()
        
        priority_map = {
            'high': 0,
            'normal': 1,
            'low': 2,
            '0': 0,
            '1': 1,
            '2': 2,
            'alta': 0,
            'media': 1,
            'baja': 2
        }
        
        if priority in priority_map:
            return True, priority_map[priority], ""
        else:
            return False, 1, "Invalid priority. Use: High, Normal, or Low"
    
    @staticmethod
    def validate_court_preference_order(courts: List[int], available_courts: List[int]) -> Tuple[bool, str]:
        """
        Validate court preference order
        Returns: (is_valid, error_message)
        """
        t('botapp.validation.ValidationHelpers.validate_court_preference_order')
        if not courts:
            return False, "Court preference cannot be empty"
        
        if len(courts) != len(set(courts)):
            return False, "Court preference cannot contain duplicates"
        
        invalid_courts = [c for c in courts if c not in available_courts]
        if invalid_courts:
            return False, f"Invalid courts in preference: {invalid_courts}"
        
        return True, ""