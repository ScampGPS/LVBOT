# Reservation Management System Guide

## Overview

The LVBOT reservation management system now provides comprehensive functionality for:
- Viewing all reservations (queued and immediate)
- Managing individual reservations
- Cancelling reservations
- Sharing reservation details

## System Architecture

### 1. **ReservationQueue** (`reservations/queue/reservation_queue.py`)
- Manages queued reservations (booked > 48h in advance)
- Stores in `data/queue.json`
- Used by scheduler for automatic booking

### 2. **ReservationTracker** (`reservations/queue/reservation_tracker.py`)
- Tracks immediate reservations (within 48h)
- Tracks completed bookings with confirmation IDs
- Stores in `data/all_reservations.json`
- Unified interface for all reservation types

### 3. **CallbackHandler Updates**
- `_handle_reservations_menu`: Shows all user reservations
- `_handle_manage_reservation`: Shows individual reservation details
- `_handle_reservation_action`: Processes cancel/modify/share actions

## User Flow

### Viewing Reservations

1. User clicks "📅 Reservations" from main menu
2. System shows all active reservations:
   - Queued (pending scheduler)
   - Immediate (confirmed within 48h)
   - Completed (with confirmation IDs)
3. Each reservation shows:
   - Status emoji (⏳ pending, ✅ confirmed, etc.)
   - Date and time
   - Court(s)
   - Management button

### Managing Individual Reservations

1. User clicks "Manage #X" for a specific reservation
2. System shows detailed view:
   - Full date/time/court details
   - Current status
   - Confirmation ID (if available)
3. Available actions:
   - **Cancel**: Remove the reservation
   - **Modify**: (Coming soon)
   - **Share**: Send details as forwardable message

### Cancellation Flow

1. User clicks "❌ Cancel Reservation"
2. System cancels based on type:
   - Queued: Removed from queue
   - Immediate/Completed: Marked as cancelled in tracker
3. Confirmation message shown
4. User can return to reservations list

### Sharing Reservations

1. User clicks "📤 Share Details"
2. Bot sends new message with reservation info:
   ```
   🎾 Tennis Reservation
   📅 2025-07-24 at 18:00
   📍 Club La Villa - Court 2
   ```
3. User can forward this message to friends

## Data Storage

### Queue Reservations (`data/queue.json`)
```json
{
  "id": "abc123...",
  "user_id": 12345,
  "target_date": "2025-07-29",
  "target_time": "14:00",
  "court_preferences": [1, 2],
  "status": "pending",
  "created_at": "2025-07-22T..."
}
```

### Immediate/Completed Reservations (`data/all_reservations.json`)
```json
{
  "imm_20250722_12345": {
    "id": "imm_20250722_12345",
    "user_id": 12345,
    "type": "immediate",
    "status": "confirmed",
    "court": 3,
    "date": "2025-07-23",
    "time": "09:00",
    "confirmation_id": "abc123def456",
    "confirmation_url": "https://...",
    "can_cancel": true,
    "can_modify": true
  }
}
```

## Integration Points

### 1. Immediate Booking Handler
- Saves successful bookings to ReservationTracker
- Extracts confirmation ID from booking result
- Stores confirmation URL for future reference

### 2. Queue Scheduler
- When scheduler completes a booking:
  - Updates queue status
  - Should save to ReservationTracker (TODO)
  - Sends user notification

### 3. Future Enhancements
- Direct cancellation via Acuity API
- Modification/rescheduling support
- Calendar integration
- Reminder notifications

## Testing

Run the test suite:
```bash
python3 test_reservation_management.py
```

This tests:
- Adding different reservation types
- Unified viewing
- Cancellation
- Details retrieval
- Update functionality

## User Benefits

1. **Single View**: See all reservations in one place
2. **Easy Management**: Cancel without leaving Telegram
3. **Share with Friends**: Forward reservation details
4. **Track Status**: Know which are pending vs confirmed
5. **Confirmation Access**: Keep confirmation IDs handy
