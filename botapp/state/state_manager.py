"""
State management for conversation handling
Manages user states and temporary data during conversations
"""
from tracking import t

from typing import Optional, Dict, Any, List
from datetime import datetime, timedelta
import logging


class UserStateManager:
    """Manage user conversation states and temporary data"""
    
    def __init__(self, timeout_minutes: int = 30):
        t('botapp.state.state_manager.UserStateManager.__init__')
        self.user_states: Dict[int, str] = {}
        self.temp_data: Dict[int, Dict[str, Any]] = {}
        self.last_activity: Dict[int, datetime] = {}
        self.timeout_minutes = timeout_minutes
        self.state_callbacks: Dict[str, List[callable]] = {}
    
    def set_state(self, user_id: int, state: str) -> None:
        """Set user's conversation state"""
        t('botapp.state.state_manager.UserStateManager.set_state')
        old_state = self.user_states.get(user_id)
        self.user_states[user_id] = state
        self.last_activity[user_id] = datetime.now()
        
        # Trigger state change callbacks
        if old_state != state:
            self._trigger_state_change(user_id, old_state, state)
        
        logging.debug(f"User {user_id} state: {old_state} -> {state}")
    
    def get_state(self, user_id: int) -> Optional[str]:
        """Get user's current state"""
        t('botapp.state.state_manager.UserStateManager.get_state')
        self._check_timeout(user_id)
        return self.user_states.get(user_id)
    
    def clear_state(self, user_id: int) -> None:
        """Clear user's state and temporary data"""
        t('botapp.state.state_manager.UserStateManager.clear_state')
        self.user_states.pop(user_id, None)
        self.temp_data.pop(user_id, None)
        self.last_activity.pop(user_id, None)
        logging.debug(f"Cleared state for user {user_id}")
    
    def set_temp_data(self, user_id: int, key: str, value: Any) -> None:
        """Store temporary data for user"""
        t('botapp.state.state_manager.UserStateManager.set_temp_data')
        if user_id not in self.temp_data:
            self.temp_data[user_id] = {}
        
        self.temp_data[user_id][key] = value
        self.last_activity[user_id] = datetime.now()
    
    def get_temp_data(self, user_id: int, key: Optional[str] = None) -> Any:
        """Get temporary data for user"""
        t('botapp.state.state_manager.UserStateManager.get_temp_data')
        self._check_timeout(user_id)
        
        if key:
            return self.temp_data.get(user_id, {}).get(key)
        return self.temp_data.get(user_id, {})
    
    def append_temp_data(self, user_id: int, key: str, value: Any) -> None:
        """Append to a list in temporary data"""
        t('botapp.state.state_manager.UserStateManager.append_temp_data')
        if user_id not in self.temp_data:
            self.temp_data[user_id] = {}
        
        if key not in self.temp_data[user_id]:
            self.temp_data[user_id][key] = []
        
        if isinstance(self.temp_data[user_id][key], list):
            self.temp_data[user_id][key].append(value)
        else:
            # Convert to list if it wasn't already
            self.temp_data[user_id][key] = [self.temp_data[user_id][key], value]
        
        self.last_activity[user_id] = datetime.now()
    
    def update_temp_data(self, user_id: int, data: Dict[str, Any]) -> None:
        """Update multiple temporary data fields at once"""
        t('botapp.state.state_manager.UserStateManager.update_temp_data')
        if user_id not in self.temp_data:
            self.temp_data[user_id] = {}
        
        self.temp_data[user_id].update(data)
        self.last_activity[user_id] = datetime.now()
    
    def has_state(self, user_id: int, state: str) -> bool:
        """Check if user is in specific state"""
        t('botapp.state.state_manager.UserStateManager.has_state')
        return self.get_state(user_id) == state
    
    def is_in_conversation(self, user_id: int) -> bool:
        """Check if user is in any conversation state"""
        t('botapp.state.state_manager.UserStateManager.is_in_conversation')
        return self.get_state(user_id) is not None
    
    def on_state_change(self, from_state: str, to_state: str, callback: callable) -> None:
        """Register callback for state transitions"""
        t('botapp.state.state_manager.UserStateManager.on_state_change')
        key = f"{from_state}->{to_state}"
        if key not in self.state_callbacks:
            self.state_callbacks[key] = []
        self.state_callbacks[key].append(callback)
    
    def get_active_users(self) -> List[int]:
        """Get list of users with active states"""
        t('botapp.state.state_manager.UserStateManager.get_active_users')
        self._cleanup_expired()
        return list(self.user_states.keys())
    
    def get_users_in_state(self, state: str) -> List[int]:
        """Get all users in a specific state"""
        t('botapp.state.state_manager.UserStateManager.get_users_in_state')
        self._cleanup_expired()
        return [uid for uid, s in self.user_states.items() if s == state]
    
    def _check_timeout(self, user_id: int) -> None:
        """Check if user's session has timed out"""
        t('botapp.state.state_manager.UserStateManager._check_timeout')
        if user_id in self.last_activity:
            time_passed = datetime.now() - self.last_activity[user_id]
            if time_passed > timedelta(minutes=self.timeout_minutes):
                self.clear_state(user_id)
                logging.debug(f"User {user_id} session timed out")
    
    def _cleanup_expired(self) -> None:
        """Clean up all expired sessions"""
        t('botapp.state.state_manager.UserStateManager._cleanup_expired')
        expired_users = []
        cutoff_time = datetime.now() - timedelta(minutes=self.timeout_minutes)
        
        for user_id, last_active in self.last_activity.items():
            if last_active < cutoff_time:
                expired_users.append(user_id)
        
        for user_id in expired_users:
            self.clear_state(user_id)
    
    def _trigger_state_change(self, user_id: int, from_state: Optional[str], 
                            to_state: str) -> None:
        """Trigger callbacks for state change"""
        t('botapp.state.state_manager.UserStateManager._trigger_state_change')
        # Specific transition
        key = f"{from_state}->{to_state}"
        if key in self.state_callbacks:
            for callback in self.state_callbacks[key]:
                try:
                    callback(user_id, from_state, to_state)
                except Exception as e:
                    logging.error(f"State callback error: {e}")
        
        # Any transition to specific state
        key = f"*->{to_state}"
        if key in self.state_callbacks:
            for callback in self.state_callbacks[key]:
                try:
                    callback(user_id, from_state, to_state)
                except Exception as e:
                    logging.error(f"State callback error: {e}")


class ConversationStates:
    """Enumeration of conversation states"""
    
    # Main states
    IDLE = None
    MAIN_MENU = "main_menu"
    
    # Reservation flow
    RESERVE_DATE = "reserve_date"
    RESERVE_TIME = "reserve_time"
    RESERVE_COURT = "reserve_court"
    RESERVE_CONFIRM = "reserve_confirm"
    
    # Profile flow
    PROFILE_FIRST_NAME = "profile_first_name"
    PROFILE_LAST_NAME = "profile_last_name"
    PROFILE_PHONE = "profile_phone"
    PROFILE_EMAIL = "profile_email"
    PROFILE_COURT_PREF = "profile_court_pref"
    
    # Admin flows
    ADMIN_MENU = "admin_menu"
    ADMIN_SEARCH_USER = "admin_search_user"
    ADMIN_BROADCAST = "admin_broadcast"
    ADMIN_EDIT_USER = "admin_edit_user"
    
    # Special states
    AWAITING_CONFIRMATION = "awaiting_confirmation"
    PROCESSING = "processing"
    ERROR = "error"

    @classmethod
    def _state_matches(cls, state: str, prefix: str, tracking_id: str) -> bool:
        t(tracking_id)
        return bool(state) and state.startswith(prefix)

    @classmethod
    def is_reservation_flow(cls, state: str) -> bool:
        """Check if state is part of reservation flow"""
        return cls._state_matches(
            state,
            "reserve_",
            'botapp.state.state_manager.ConversationStates.is_reservation_flow',
        )

    @classmethod
    def is_profile_flow(cls, state: str) -> bool:
        """Check if state is part of profile flow"""
        return cls._state_matches(
            state,
            "profile_",
            'botapp.state.state_manager.ConversationStates.is_profile_flow',
        )

    @classmethod
    def is_admin_flow(cls, state: str) -> bool:
        """Check if state is part of admin flow"""
        return cls._state_matches(
            state,
            "admin_",
            'botapp.state.state_manager.ConversationStates.is_admin_flow',
        )
