# Testing Telegram Queue Flow

## Test Steps:

1. **Start the bot**:
   ```bash
   python3 telegram_tennis_bot.py
   ```

2. **In Telegram, test the queue flow**:
   - Send `/start`
   - Click "🎾 Reserve Court"
   - Click "📅 Reserve after 48h" 
   - Select year (current or next)
   - Select month
   - Select date (must be > 48h from now)
   - Select time slot
   - Select courts (can choose specific or all)
   - Confirm the reservation

3. **Check queued reservations**:
   - From main menu, click "📋 Queued Reservations"
   - Should see your pending reservation

4. **Monitor the scheduler**:
   - Check logs to see when scheduler processes reservations
   - Should attempt booking when 48h window opens

## Expected Results:

1. **Queue Entry Created**:
   - Status: "pending"
   - All details saved correctly

2. **Scheduler Processing**:
   - When target date/time is within 48h window
   - Status changes to "scheduled" → "completed" or "failed"

3. **Notification**:
   - User receives success/failure message via bot

## Current Implementation Status:

✅ **Complete**:
- Queue data structure (`ReservationQueue`)
- Telegram UI flow for queue booking
- Reservation scheduler running in background
- Direct URL navigation for bookings
- Confirmation page detection

⚠️ **To Verify**:
- Scheduler timing (48h window calculation)
- User notifications after booking
- Error handling and retries

## Debug Commands:

```python
# Check queue contents
import json
with open('queue.json', 'r') as f:
    print(json.dumps(json.load(f), indent=2))

# Check scheduler logs
tail -f logs/bot_*.log | grep -i scheduler
```