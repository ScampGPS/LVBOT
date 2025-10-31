"""
User Management System for Tennis Bot
Handles persistent storage and retrieval of user profiles
"""
from tracking import t

import json
import logging
from typing import Dict, Any, Optional
from pathlib import Path
from enum import Enum
from infrastructure.constants import HARDCODED_VIP_USERS, HARDCODED_ADMIN_USERS


class UserTier(Enum):
    """User tier levels for priority system"""
    ADMIN = 0     # Highest priority
    VIP = 1       # VIP users
    REGULAR = 2   # Regular users


class UserManager:
    """
    Manages user profiles with persistent JSON storage
    
    Provides functionality to store, retrieve, and update user profiles
    with automatic persistence to a JSON file for data durability.
    """
    
    def __init__(self, file_path: str = 'users.json') -> None:
        """
        Initialize the UserManager with persistent storage
        
        Args:
            file_path: Path to the JSON file for storing user data
            
        Sets up logging and loads existing user data from file
        """
        t('users.manager.UserManager.__init__')
        self.file_path = Path(file_path)
        self.logger = logging.getLogger('UserManager')
        self.users: Dict[int, Dict[str, Any]] = self._load_users()
        
        self.logger.info(f"UserManager initialized with {len(self.users)} users from {file_path}")
    
    def get_user(self, user_id: int) -> Optional[Dict[str, Any]]:
        """
        Retrieve a single user profile by user ID

        Args:
            user_id: Telegram user ID to lookup

        Returns:
            Dict containing user profile data if found, None otherwise
        """
        t('users.manager.UserManager.get_user')
        user_profile = self.users.get(user_id)
        if user_profile:
            # Ensure language field exists with default value
            if 'language' not in user_profile:
                user_profile['language'] = 'es'  # Default to Spanish
            self.logger.debug(f"Retrieved user profile for user_id: {user_id}")
        else:
            self.logger.debug(f"No profile found for user_id: {user_id}")

        return user_profile
    
    def save_user(self, user_profile: Dict[str, Any]) -> None:
        """
        Save or update a user profile
        
        Args:
            user_profile: Dictionary containing user profile data
                         Must include 'user_id' key
                         
        Raises:
            ValueError: If user_profile lacks required 'user_id' key
        """
        t('users.manager.UserManager.save_user')
        if 'user_id' not in user_profile:
            raise ValueError("User profile must contain 'user_id' key")
        
        user_id = user_profile['user_id']
        
        # Update or create user profile
        self.users[user_id] = user_profile.copy()
        
        # Persist changes to file
        self._save_users()
        
        self.logger.info(f"Saved user profile for user_id: {user_id}")
    
    def get_all_users(self) -> Dict[int, Dict[str, Any]]:
        """
        Retrieve all stored user profiles

        Returns:
            Dictionary where keys are user_ids and values are user profile dictionaries
        """
        t('users.manager.UserManager.get_all_users')
        self.logger.debug(f"Retrieved all users: {len(self.users)} profiles")
        return self.users.copy()

    def _has_role(self, user_id: int, hardcoded: set[int], profile_flag: str) -> bool:
        if user_id in hardcoded:
            return True

        user_profile = self.get_user(user_id)
        return user_profile.get(profile_flag, False) if user_profile else False

    def is_admin(self, user_id: int) -> bool:
        """
        Check if a user has admin privileges
        
        Checks both hardcoded list and database flag
        
        Args:
            user_id: Telegram user ID to check
            
        Returns:
            True if user is an admin, False otherwise
        """
        t('users.manager.UserManager.is_admin')
        return self._has_role(user_id, HARDCODED_ADMIN_USERS, 'is_admin')
    
    def is_vip(self, user_id: int) -> bool:
        """
        Check if a user has VIP privileges
        
        VIP users get priority in court selection when multiple users
        are competing for the same time slot
        
        Checks both hardcoded list and database flag
        
        Args:
            user_id: Telegram user ID to check
            
        Returns:
            True if user is a VIP, False otherwise
        """
        t('users.manager.UserManager.is_vip')
        return self._has_role(user_id, HARDCODED_VIP_USERS, 'is_vip')
    
    def get_user_tier(self, user_id: int) -> UserTier:
        """
        Get the tier level of a user for priority system
        
        Args:
            user_id: Telegram user ID to check
            
        Returns:
            UserTier enum value (ADMIN, VIP, or REGULAR)
        """
        t('users.manager.UserManager.get_user_tier')
        if self.is_admin(user_id):
            return UserTier.ADMIN
        elif self.is_vip(user_id):
            return UserTier.VIP
        else:
            return UserTier.REGULAR
    
    def set_user_tier(self, user_id: int, tier: UserTier) -> None:
        """
        Set the tier level of a user

        Args:
            user_id: Telegram user ID
            tier: UserTier enum value to set
        """
        t('users.manager.UserManager.set_user_tier')
        user_profile = self.get_user(user_id)
        if not user_profile:
            user_profile = {
                'user_id': user_id,
                'language': 'es'  # Default new users to Spanish
            }

        # Update tier and corresponding flags
        user_profile['tier'] = tier.value
        user_profile['tier_name'] = tier.name

        # Update boolean flags for backward compatibility
        if tier == UserTier.ADMIN:
            user_profile['is_admin'] = True
            user_profile['is_vip'] = True  # Admins are also VIP
        elif tier == UserTier.VIP:
            user_profile['is_admin'] = False
            user_profile['is_vip'] = True
        else:  # REGULAR
            user_profile['is_admin'] = False
            user_profile['is_vip'] = False

        self.save_user(user_profile)
        self.logger.info(f"Set user {user_id} tier to {tier.name}")

    def get_user_language(self, user_id: int) -> str:
        """
        Get the preferred language of a user

        Args:
            user_id: Telegram user ID

        Returns:
            Language code ('es' or 'en'), defaults to 'es' if not set
        """
        t('users.manager.UserManager.get_user_language')
        user_profile = self.get_user(user_id)
        if user_profile:
            return user_profile.get('language', 'es')
        return 'es'  # Default to Spanish for users not found

    def set_user_language(self, user_id: int, language: str) -> bool:
        """
        Set the preferred language for a user

        Args:
            user_id: Telegram user ID
            language: Language code ('es' or 'en')

        Returns:
            True if successful, False if user not found
        """
        t('users.manager.UserManager.set_user_language')
        user_profile = self.get_user(user_id)
        if not user_profile:
            self.logger.warning(f"Cannot set language for non-existent user {user_id}")
            return False

        user_profile['language'] = language
        self.save_user(user_profile)
        self.logger.info(f"Set user {user_id} language to {language}")
        return True
    
    def _save_users(self) -> None:
        """
        Internal helper method to save user data to JSON file
        
        Handles file operations with proper error handling and logging
        """
        t('users.manager.UserManager._save_users')
        try:
            # Ensure parent directory exists
            self.file_path.parent.mkdir(parents=True, exist_ok=True)
            
            # Write user data to JSON file with proper formatting
            with open(self.file_path, 'w', encoding='utf-8') as f:
                json.dump(self.users, f, indent=2, ensure_ascii=False, default=str)
            
            self.logger.debug(f"Successfully saved {len(self.users)} user profiles to {self.file_path}")
            
        except Exception as e:
            self.logger.error(f"Error saving users to {self.file_path}: {e}", exc_info=True)
            raise
    
    def _load_users(self) -> Dict[int, Dict[str, Any]]:
        """
        Internal helper method to load user data from JSON file
        
        Returns:
            Dictionary of user profiles loaded from file
            Returns empty dictionary if file doesn't exist or is invalid
        """
        t('users.manager.UserManager._load_users')
        try:
            if not self.file_path.exists():
                self.logger.info(f"User file {self.file_path} does not exist, starting with empty user database")
                return {}
            
            if self.file_path.stat().st_size == 0:
                self.logger.info(f"User file {self.file_path} is empty, starting with empty user database")
                return {}
            
            with open(self.file_path, 'r', encoding='utf-8') as f:
                data = json.load(f)
            
            # Convert string keys back to integers (JSON keys are always strings)
            users = {}
            for key, value in data.items():
                try:
                    user_id = int(key)
                    users[user_id] = value
                except ValueError:
                    self.logger.warning(f"Invalid user_id key in JSON file: {key}, skipping entry")
                    continue
            
            self.logger.info(f"Successfully loaded {len(users)} user profiles from {self.file_path}")
            return users
            
        except json.JSONDecodeError as e:
            self.logger.error(f"Invalid JSON in user file {self.file_path}: {e}")
            self.logger.info("Starting with empty user database")
            return {}
            
        except Exception as e:
            self.logger.error(f"Error loading users from {self.file_path}: {e}", exc_info=True)
            self.logger.info("Starting with empty user database")
            return {}
