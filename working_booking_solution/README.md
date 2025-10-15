# Club Lavilla Tennis Court Booking Automation

🎾 **Automated tennis court booking system for Club Lavilla with real time slot clicking.**

## ✅ Working Solution

This system successfully books tennis court reservations using a natural user flow approach:

1. **Court Page Navigation** - Accesses the scheduling calendar page
2. **Real Time Slot Clicking** - Finds and clicks available 09:00 time slots  
3. **Form Auto-Fill** - Fills booking form with human-like typing patterns
4. **Successful Submission** - Submits reservation with anti-bot evasion

## 🏆 Final Implementation

**`court_booking_final.py`** - The complete working solution

### Key Features:
- ✅ **Working time slot detection** - Finds 09:00 button using proven selectors
- ✅ **Natural user flow** - Mimics real person selecting time slots
- ✅ **Human-like form filling** - Types with mistakes and natural delays
- ✅ **Anti-bot evasion** - Natural mouse movements and behavior patterns
- ✅ **Successful submission** - CONFIRMAR CITA button works properly

### User Information:
- **Name**: Saul Campos
- **Phone**: +502 31874277  
- **Email**: msaulcampos@gmail.com
- **Target Time**: 09:00 AM

## 🚀 Usage

```bash
python3 court_booking_final.py
# Type 'FINAL' when prompted
```

## 📋 Requirements

```bash
pip install playwright
playwright install chromium
```

## 🎯 How It Works

1. **Natural Browsing** - Visits main site to establish session
2. **Court Page Access** - Navigates to scheduling calendar
3. **Time Slot Detection** - Uses `button:has-text("09:00")` selector
4. **Time Slot Clicking** - Clicks with natural mouse movement
5. **Form Detection** - Waits for `#client\.firstName` form to appear
6. **Form Filling** - Fills all fields with 10% email error rate
7. **Submission** - Clicks CONFIRMAR CITA with human-like behavior

## 📸 Success Screenshots

- `success_filled.png` - Form filled successfully
- `success_result.png` - Booking confirmation result

## 🎉 Results

✅ **Successfully tested and working**
✅ **Time slot clicking confirmed**  
✅ **Form submission successful**
✅ **CONFIRMAR CITA button clickable**
✅ **Booking confirmation achieved**

The system successfully creates tennis court reservations using the natural court page flow instead of direct URL manipulation, making it more reliable and less detectable.