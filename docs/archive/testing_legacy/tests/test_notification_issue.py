#!/usr/bin/env python3
"""Test script to reproduce the notification issue"""

import asyncio
import logging
from datetime import datetime
from lvbot.utils.reservation_queue import ReservationQueue
from lvbot.utils.user_manager import UserManager
from lvbot.utils.priority_manager import PriorityManager
from lvbot.utils.booking_orchestrator import DynamicBookingOrchestrator
from lvbot.utils.reservation_scheduler import ReservationScheduler

# Set up logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    datefmt='%H:%M:%S'
)

logger = logging.getLogger(__name__)

class MockBot:
    """Mock bot for testing notifications"""
    def __init__(self, queue, user_db):
        self.notifications_sent = []
        self.config = {'ADMIN_CHAT_ID': 125763357}
        self.queue = queue
        self.user_db = user_db
        
    async def send_notification(self, user_id: int, message: str):
        logger.info(f"MockBot.send_notification called: user_id={user_id}")
        logger.info(f"Message: {message}")
        self.notifications_sent.append({
            'user_id': user_id,
            'message': message,
            'timestamp': datetime.now()
        })
        return True
        
    def send_notification_sync(self, user_id: int, message: str):
        logger.info(f"MockBot.send_notification_sync called: user_id={user_id}")
        return True

async def test_notification_flow():
    """Test the notification flow after a successful booking"""
    
    # Initialize components
    queue = ReservationQueue()
    user_db = UserManager()
    priority_manager = PriorityManager()
    orchestrator = DynamicBookingOrchestrator()
    
    # Create mock bot
    mock_bot = MockBot(queue, user_db)
    
    # Initialize scheduler with mock bot
    scheduler = ReservationScheduler(
        config=None,
        queue=queue,
        notification_callback=None,
        bot_handler=mock_bot,
        browser_pool=None
    )
    
    # Create a test reservation
    test_reservation_id = "test123456789"
    test_reservation = {
        'id': test_reservation_id,
        'user_id': 125763357,  # Your user ID
        'target_date': '2025-08-06',
        'target_time': '09:00',
        'court_preferences': [1, 2, 3],
        'status': 'pending'
    }
    
    # Add to queue
    queue.add_reservation(test_reservation)
    logger.info(f"Added test reservation: {test_reservation_id}")
    
    # Simulate successful booking result
    results = {
        test_reservation_id: {
            'success': True,
            'court': 1,
            'time': '09:00',
            'confirmation_code': 'TEST123'
        }
    }
    
    # Mark as completed (simulating what happens in real flow)
    queue.update_reservation_status(test_reservation_id, 'completed')
    logger.info(f"Updated reservation status to completed")
    
    # Test the notification method
    logger.info("Calling _notify_booking_results...")
    await scheduler._notify_booking_results(results)
    
    # Also test getting user directly
    logger.info(f"\nTesting user lookup...")
    user = user_db.get_user(125763357)
    logger.info(f"User found: {user is not None}")
    if user:
        logger.info(f"User details: {user}")
    
    # Check if scheduler has proper user_db reference
    logger.info(f"\nScheduler user_db: {scheduler.user_db}")
    logger.info(f"Scheduler user_db type: {type(scheduler.user_db)}")
    
    # Check if notification was sent
    logger.info(f"\nNotifications sent: {len(mock_bot.notifications_sent)}")
    for notif in mock_bot.notifications_sent:
        logger.info(f"User: {notif['user_id']}")
        logger.info(f"Message: {notif['message'][:100]}...")

if __name__ == "__main__":
    asyncio.run(test_notification_flow())