"""
Tennis Configuration - Data structures for booking configuration
"""

from dataclasses import dataclass
from typing import List, Dict, Any, Union


@dataclass
class TennisConfig:
    """Configuration for tennis booking operations"""
    email: str
    first_name: str
    last_name: str
    phone: str
    user_id: Union[str, int]  # Can be string 'test_user' or int user ID
    preferred_time: str
    target_time: str
    fallback_times: List[str]
    court_preference: List[int]
    preferred_times: List[str] = None  # Alternative field name used in some calls
    
    def __post_init__(self):
        """Post-initialization to handle preferred_times field"""
        if self.preferred_times is None:
            self.preferred_times = [self.preferred_time]


def create_tennis_config_from_user_info(user_info: Dict[str, Any]) -> TennisConfig:
    """
    Create TennisConfig from user info dictionary
    
    Args:
        user_info: Dictionary containing user information with keys:
                  - email: str
                  - first_name: str  
                  - last_name: str
                  - phone: str
                  - user_id: str or int (optional, defaults to 0)
                  - preferred_time: str (optional, defaults to "09:00")
                  - target_time: str (optional, defaults to preferred_time)
                  - fallback_times: List[str] (optional, defaults to empty list)
                  - court_preference: List[int] (optional, defaults to [1, 2, 3])
                  - preferred_times: List[str] (optional, alternative to preferred_time)
                  
    Returns:
        TennisConfig object
    """
    # Handle preferred_time vs preferred_times
    preferred_time = user_info.get('preferred_time', '09:00')
    preferred_times = user_info.get('preferred_times', [preferred_time])
    
    # If preferred_times is provided but preferred_time is not, use first preferred_time
    if 'preferred_times' in user_info and 'preferred_time' not in user_info:
        preferred_time = preferred_times[0] if preferred_times else '09:00'
    
    return TennisConfig(
        email=user_info.get('email', ''),
        first_name=user_info.get('first_name', ''),
        last_name=user_info.get('last_name', ''),
        phone=user_info.get('phone', ''),
        user_id=user_info.get('user_id', 0),
        preferred_time=preferred_time,
        target_time=user_info.get('target_time', preferred_time),
        fallback_times=user_info.get('fallback_times', []),
        court_preference=user_info.get('court_preference', [1, 2, 3]),
        preferred_times=preferred_times
    )