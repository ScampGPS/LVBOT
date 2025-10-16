#!/usr/bin/env python3
"""
Session isolation manager for multi-browser environments.
"""
from tracking import t

import os
import json
import time
import random
import hashlib
from datetime import datetime, timedelta
from typing import Dict, Optional


class SessionManager:
    """Manages booking sessions to prevent conflicts between multiple browsers."""
    
    def __init__(self, session_file="booking_sessions.json"):
        t('archive.experiments.working_booking_solution.session_manager.SessionManager.__init__')
        self.session_file = session_file
        self.session_id = self._generate_session_id()
        self.load_sessions()
    
    def _generate_session_id(self) -> str:
        """Generate unique session ID."""
        t('archive.experiments.working_booking_solution.session_manager.SessionManager._generate_session_id')
        timestamp = int(time.time())
        random_part = random.randint(1000, 9999)
        pid = os.getpid()
        return f"session_{timestamp}_{random_part}_{pid}"
    
    def load_sessions(self) -> Dict:
        """Load existing sessions from file."""
        t('archive.experiments.working_booking_solution.session_manager.SessionManager.load_sessions')
        try:
            if os.path.exists(self.session_file):
                with open(self.session_file, 'r') as f:
                    self.sessions = json.load(f)
            else:
                self.sessions = {}
        except Exception:
            self.sessions = {}
        
        # Clean expired sessions (older than 1 hour)
        self._clean_expired_sessions()
        return self.sessions
    
    def _clean_expired_sessions(self):
        """Remove expired sessions."""
        t('archive.experiments.working_booking_solution.session_manager.SessionManager._clean_expired_sessions')
        current_time = time.time()
        expired_sessions = []
        
        for session_id, session_data in self.sessions.items():
            if current_time - session_data.get('start_time', 0) > 3600:  # 1 hour
                expired_sessions.append(session_id)
        
        for session_id in expired_sessions:
            del self.sessions[session_id]
        
        if expired_sessions:
            self.save_sessions()
    
    def save_sessions(self):
        """Save sessions to file."""
        t('archive.experiments.working_booking_solution.session_manager.SessionManager.save_sessions')
        try:
            with open(self.session_file, 'w') as f:
                json.dump(self.sessions, f, indent=2)
        except Exception as e:
            print(f"Warning: Could not save sessions: {e}")
    
    def register_session(self, target_time: str = "09:00") -> bool:
        """Register a new booking session."""
        t('archive.experiments.working_booking_solution.session_manager.SessionManager.register_session')
        current_time = time.time()
        
        # Check if another session is targeting the same time slot recently
        for session_id, session_data in self.sessions.items():
            if (session_data.get('target_time') == target_time and 
                current_time - session_data.get('start_time', 0) < 300):  # 5 minutes
                print(f"⚠️ Another session is targeting {target_time}, waiting...")
                return False
        
        # Register this session
        self.sessions[self.session_id] = {
            'start_time': current_time,
            'target_time': target_time,
            'status': 'active',
            'pid': os.getpid()
        }
        
        self.save_sessions()
        print(f"✅ Session {self.session_id} registered for {target_time}")
        return True
    
    def update_session_status(self, status: str):
        """Update session status."""
        t('archive.experiments.working_booking_solution.session_manager.SessionManager.update_session_status')
        if self.session_id in self.sessions:
            self.sessions[self.session_id]['status'] = status
            self.sessions[self.session_id]['last_update'] = time.time()
            self.save_sessions()
    
    def get_recommended_delay(self) -> int:
        """Get recommended delay based on active sessions."""
        t('archive.experiments.working_booking_solution.session_manager.SessionManager.get_recommended_delay')
        active_sessions = sum(1 for s in self.sessions.values() 
                            if s.get('status') == 'active')
        
        # More active sessions = longer delays
        base_delay = 5
        additional_delay = (active_sessions - 1) * 10
        return base_delay + additional_delay
    
    def cleanup_session(self):
        """Clean up current session."""
        t('archive.experiments.working_booking_solution.session_manager.SessionManager.cleanup_session')
        if self.session_id in self.sessions:
            del self.sessions[self.session_id]
            self.save_sessions()
            print(f"🧹 Session {self.session_id} cleaned up")


class BrowserInstanceManager:
    """Manages browser instance isolation."""
    
    @staticmethod
    def get_unique_user_data_dir() -> str:
        """Create unique user data directory for browser isolation."""
        t('archive.experiments.working_booking_solution.session_manager.BrowserInstanceManager.get_unique_user_data_dir')
        timestamp = int(time.time())
        pid = os.getpid()
        random_id = random.randint(1000, 9999)
        
        data_dir = f"browser_data_{timestamp}_{pid}_{random_id}"
        os.makedirs(data_dir, exist_ok=True)
        return data_dir
    
    @staticmethod
    def get_staggered_viewport() -> Dict[str, int]:
        """Get viewport size that's different from other likely instances."""
        t('archive.experiments.working_booking_solution.session_manager.BrowserInstanceManager.get_staggered_viewport')
        # Base dimensions with per-instance variation
        base_width = 1200
        base_height = 800
        
        # Use PID for consistent but different sizing per process
        pid_offset = (os.getpid() % 7) * 50
        
        return {
            'width': base_width + pid_offset + random.randint(-100, 100),
            'height': base_height + pid_offset + random.randint(-50, 50)
        }
    
    @staticmethod
    def get_unique_user_agent() -> str:
        """Generate slightly different user agent per instance."""
        t('archive.experiments.working_booking_solution.session_manager.BrowserInstanceManager.get_unique_user_agent')
        base_ua = "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36"
        
        # Add small variations
        chrome_versions = ["120.0.0.0", "119.0.0.0", "121.0.0.0"]
        webkit_versions = ["537.36", "537.35", "537.37"]
        
        chosen_chrome = random.choice(chrome_versions)
        chosen_webkit = random.choice(webkit_versions)
        
        return base_ua.replace("120.0.0.0", chosen_chrome).replace("537.36", chosen_webkit)


if __name__ == "__main__":
    # Test session management
    print("🧪 Testing Session Management")
    
    session_mgr = SessionManager()
    
    # Test session registration
    if session_mgr.register_session("09:00"):
        print("✅ Session registered successfully")
        
        # Test delay recommendation
        delay = session_mgr.get_recommended_delay()
        print(f"📊 Recommended delay: {delay} seconds")
        
        # Test browser instance management
        browser_mgr = BrowserInstanceManager()
        
        viewport = browser_mgr.get_staggered_viewport()
        print(f"📐 Unique viewport: {viewport}")
        
        user_agent = browser_mgr.get_unique_user_agent()
        print(f"🌐 Unique user agent: {user_agent[:50]}...")
        
        # Cleanup
        session_mgr.cleanup_session()
    else:
        print("⚠️ Session registration blocked")