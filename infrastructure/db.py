"""
Database operation helpers
Handles common database operations and queries
"""
from utils.tracking import t

from typing import Optional, List, Dict, Any
from datetime import datetime, timedelta
import pytz
import json


class DatabaseHelpers:
    """Collection of database helper functions"""
    
    @staticmethod
    def get_or_create_user_profile(user_db, user_id: int, telegram_user) -> Any:
        """Get existing or create new user profile"""
        t('infrastructure.db.DatabaseHelpers.get_or_create_user_profile')
        profile = user_db.get_user(user_id)
        
        if not profile:
            # Import here to avoid circular imports
            from reservations.models.reservation import UserProfile

            profile = UserProfile(
                user_id=user_id,
                first_name=telegram_user.first_name or "New",
                last_name=telegram_user.last_name or "User",
                phone="",
                email="",
                court_preference=[3, 1, 2],  # Default preference
                telegram_username=telegram_user.username or "",
                is_active=False,  # Inactive until approved
                created_at=datetime.now(pytz.UTC),
                total_reservations=0
            )
            user_db.save_user(profile)
        
        return profile
    
    @staticmethod
    def update_user_field(user_db, user_id: int, field: str, value: Any) -> bool:
        """Update a single user field"""
        t('infrastructure.db.DatabaseHelpers.update_user_field')
        user = user_db.get_user(user_id)
        if user:
            setattr(user, field, value)
            user_db.save_user(user)
            return True
        return False
    
    @staticmethod
    def update_user_fields(user_db, user_id: int, fields: Dict[str, Any]) -> bool:
        """Update multiple user fields at once"""
        t('infrastructure.db.DatabaseHelpers.update_user_fields')
        user = user_db.get_user(user_id)
        if user:
            for field, value in fields.items():
                if hasattr(user, field):
                    setattr(user, field, value)
            user_db.save_user(user)
            return True
        return False
    
    @staticmethod
    def get_user_reservations_summary(queue, user_id: int, timezone_str: str = 'America/Guatemala') -> str:
        """Get formatted summary of user's reservations"""
        t('infrastructure.db.DatabaseHelpers.get_user_reservations_summary')
        tz = pytz.timezone(timezone_str)
        reservations = queue.get_user_reservations_48h(user_id, tz)
        
        if not reservations:
            return "No active reservations in the next 48 hours."
        
        summary = f"**Active Reservations ({len(reservations)})**\n\n"
        
        for idx, res in enumerate(reservations, 1):
            courts = ', '.join([f"Court {c}" for c in res.courts])
            
            # Calculate time until reservation
            hours_until = (res.target_datetime - datetime.now(tz)).total_seconds() / 3600
            
            summary += f"{idx}. {res.date} at {res.time}\n"
            summary += f"   Courts: {courts}\n"
            summary += f"   Status: {res.status}\n"
            
            if hours_until > 0:
                summary += f"   Time until: {hours_until:.1f} hours\n"
            else:
                summary += "   Ready for booking!\n"
            
            if res.attempts > 0:
                summary += f"   Attempts: {res.attempts}\n"
            
            summary += "\n"
        
        return summary
    
    @staticmethod
    def get_active_users_count(user_db) -> int:
        """Get count of active users"""
        t('infrastructure.db.DatabaseHelpers.get_active_users_count')
        all_users = user_db.get_all_users()
        return sum(1 for user in all_users.values() if user.is_active)
    
    @staticmethod
    def get_pending_users(user_db) -> List[Any]:
        """Get list of users pending approval"""
        t('infrastructure.db.DatabaseHelpers.get_pending_users')
        all_users = user_db.get_all_users()
        pending = []
        
        for user in all_users.values():
            if not user.is_active and user.phone and user.email:
                pending.append(user)
        
        # Sort by creation date (newest first)
        pending.sort(key=lambda u: getattr(u, 'created_at', datetime.min), reverse=True)
        return pending
    
    @staticmethod
    def search_users(user_db, query: str) -> List[Any]:
        """Search users by name, phone, email, or username"""
        t('infrastructure.db.DatabaseHelpers.search_users')
        query = query.lower().strip()
        all_users = user_db.get_all_users()
        results = []
        
        for user in all_users.values():
            # Search in various fields
            searchable = [
                str(user.user_id),
                user.first_name.lower(),
                user.last_name.lower(),
                user.phone,
                user.email.lower(),
                user.telegram_username.lower() if user.telegram_username else ""
            ]
            
            if any(query in field for field in searchable):
                results.append(user)
        
        return results
    
    @staticmethod
    def get_reservation_stats(queue, timezone_str: str = 'America/Guatemala') -> Dict[str, Any]:
        """Get reservation statistics"""
        t('infrastructure.db.DatabaseHelpers.get_reservation_stats')
        tz = pytz.timezone(timezone_str)
        all_reservations = queue.get_all_active_reservations(tz)
        
        stats = {
            'total_active': len(all_reservations),
            'total_pending': sum(1 for r in all_reservations if r.status == 'pending'),
            'total_processing': sum(1 for r in all_reservations if r.status == 'processing'),
            'total_confirmed': sum(1 for r in all_reservations if r.status == 'confirmed'),
            'total_failed': sum(1 for r in all_reservations if r.status == 'failed'),
            'by_court': {},
            'by_user': {},
            'by_hour': {}
        }
        
        for res in all_reservations:
            # By court
            for court in res.courts:
                stats['by_court'][court] = stats['by_court'].get(court, 0) + 1
            
            # By user
            stats['by_user'][res.user_id] = stats['by_user'].get(res.user_id, 0) + 1
            
            # By hour
            hour = res.time.split(':')[0]
            stats['by_hour'][hour] = stats['by_hour'].get(hour, 0) + 1
        
        return stats
    
    @staticmethod
    def cleanup_old_reservations(queue, days_to_keep: int = 7) -> int:
        """Remove reservations older than specified days"""
        t('infrastructure.db.DatabaseHelpers.cleanup_old_reservations')
        cutoff_date = datetime.now(pytz.UTC) - timedelta(days=days_to_keep)
        removed_count = 0
        
        # This would need to be implemented in the queue class
        # For now, return 0
        return removed_count
    
    @staticmethod
    def export_user_data(user_db, user_id: int) -> Dict[str, Any]:
        """Export all user data for GDPR compliance"""
        t('infrastructure.db.DatabaseHelpers.export_user_data')
        user = user_db.get_user(user_id)
        if not user:
            return {}
        
        return {
            'profile': {
                'user_id': user.user_id,
                'first_name': user.first_name,
                'last_name': user.last_name,
                'phone': user.phone,
                'email': user.email,
                'court_preference': user.court_preference,
                'telegram_username': user.telegram_username,
                'is_active': user.is_active,
                'is_admin': getattr(user, 'is_admin', False),
                'created_at': user.created_at.isoformat() if hasattr(user, 'created_at') else None,
                'total_reservations': user.total_reservations
            }
        }
    
    @staticmethod
    def get_user_activity_summary(queue, user_id: int, days: int = 30) -> Dict[str, Any]:
        """Get user activity summary for specified period"""
        t('infrastructure.db.DatabaseHelpers.get_user_activity_summary')
        # This would analyze reservation history
        # For now, return basic structure
        return {
            'total_reservations': 0,
            'successful_bookings': 0,
            'failed_attempts': 0,
            'favorite_courts': [],
            'favorite_times': [],
            'average_attempts_per_booking': 0
        }
    
    @staticmethod
    def batch_update_users(user_db, user_ids: List[int], field: str, value: Any) -> int:
        """Update multiple users with the same field value"""
        t('infrastructure.db.DatabaseHelpers.batch_update_users')
        updated_count = 0
        
        for user_id in user_ids:
            if DatabaseHelpers.update_user_field(user_db, user_id, field, value):
                updated_count += 1
        
        return updated_count
