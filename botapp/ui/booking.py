"""Booking and queue related UI helpers."""

from __future__ import annotations
from tracking import t

import calendar
import logging
from datetime import date, datetime, timedelta
from typing import Any, Dict, List, Optional

import pytz
from telegram import InlineKeyboardButton, InlineKeyboardMarkup, ReplyKeyboardMarkup

from botapp.ui.text_blocks import escape_telegram_markdown
from infrastructure.constants import get_court_hours
from infrastructure.settings import get_test_mode


def create_court_selection_keyboard(available_courts: List[int]) -> ReplyKeyboardMarkup:
    """Create court selection keyboard for reply-based flows."""

    t('botapp.ui.booking.create_court_selection_keyboard')
    keyboard = []
    for i in range(0, len(available_courts), 3):
        row = [f"Court {court}" for court in available_courts[i:i+3]]
        keyboard.append(row)
    keyboard.append(["All courts", "Cancel"])
    return ReplyKeyboardMarkup(keyboard, one_time_keyboard=True, resize_keyboard=True)


def create_queue_court_selection_keyboard(available_courts: List[int], translator=None) -> InlineKeyboardMarkup:
    """Create inline court selection keyboard for queue booking flow."""

    t('botapp.ui.booking.create_queue_court_selection_keyboard')

    # Import here to avoid circular dependency
    if translator is None:
        from botapp.i18n.translator import create_translator
        translator = create_translator()

    keyboard = []
    for i in range(0, len(available_courts), 3):
        row = [
            InlineKeyboardButton(
                translator.t("court.label", number=court),
                callback_data=f'queue_court_{court}'
            )
            for court in available_courts[i:i+3]
        ]
        keyboard.append(row)

    keyboard.append([InlineKeyboardButton(translator.t("court.all"), callback_data='queue_court_all')])
    keyboard.append([InlineKeyboardButton(translator.t("nav.back"), callback_data='back_to_queue_time')])
    return InlineKeyboardMarkup(keyboard)


def create_queue_confirmation_keyboard() -> InlineKeyboardMarkup:
    """Create inline confirmation keyboard for queue booking flow."""

    t('botapp.ui.booking.create_queue_confirmation_keyboard')
    keyboard = [
        [
            InlineKeyboardButton("✅ Confirm", callback_data='queue_confirm'),
            InlineKeyboardButton("❌ Cancel", callback_data='queue_cancel'),
        ],
        [InlineKeyboardButton("🔙 Back", callback_data='back_to_queue_courts')],
    ]
    return InlineKeyboardMarkup(keyboard)


def create_day_selection_keyboard(year: int, month: int, flow_type: str = 'immediate') -> InlineKeyboardMarkup:
    """Create day selection calendar keyboard for a given year and month."""

    t('botapp.ui.booking.create_day_selection_keyboard')
    logger = logging.getLogger('TelegramUI')

    cal = calendar.monthcalendar(year, month)
    month_name = calendar.month_name[month]
    today = date.today()

    keyboard: List[List[InlineKeyboardButton]] = []
    keyboard.append([InlineKeyboardButton(f"📅 {month_name} {year}", callback_data="noop")])
    keyboard.append([InlineKeyboardButton(day[:2], callback_data="noop") for day in [
        "Mon", "Tue", "Wed", "Thu", "Fri", "Sat", "Sun"
    ]])

    selectable_dates: List[str] = []

    if flow_type == 'queue_booking':
        config = get_test_mode()
        mexico_tz = pytz.timezone('America/Mexico_City')
        current_time = datetime.now(mexico_tz)
        logger.info(
            "CALENDAR DAY FILTERING (Queue Booking)\nYear-Month: %s-%02d\nCurrent time (Mexico): %s\n48h threshold: %s",
            year,
            month,
            current_time,
            current_time + timedelta(hours=48),
        )

    for week in cal:
        row = []
        for day_num in week:
            if day_num == 0:
                row.append(InlineKeyboardButton(" ", callback_data="noop"))
                continue

            current_date = date(year, month, day_num)
            if current_date < today:
                row.append(InlineKeyboardButton("❌", callback_data="noop"))
                continue

            if flow_type == 'queue_booking':
                mexico_tz = pytz.timezone('America/Mexico_City')
                current_time = datetime.now(mexico_tz)
                allow_within_48h = config.enabled and config.allow_within_48h

                if allow_within_48h:
                    selectable_dates.append(current_date.strftime('%Y-%m-%d'))
                    row.append(
                        InlineKeyboardButton(
                            str(day_num),
                            callback_data=f'future_date_{year}-{month:02d}-{day_num:02d}',
                        )
                    )
                else:
                    has_available_slot = False
                    for hour_str in get_court_hours(current_date):
                        hour, minute = map(int, hour_str.split(':'))
                        slot_datetime_naive = datetime.combine(
                            current_date,
                            datetime.min.time().replace(hour=hour, minute=minute),
                        )
                        slot_datetime = mexico_tz.localize(slot_datetime_naive)
                        if (slot_datetime - current_time).total_seconds() > 48 * 3600:
                            has_available_slot = True
                            break

                    if has_available_slot:
                        selectable_dates.append(current_date.strftime('%Y-%m-%d'))
                        row.append(
                            InlineKeyboardButton(
                                str(day_num),
                                callback_data=f'future_date_{year}-{month:02d}-{day_num:02d}',
                            )
                        )
                    else:
                        row.append(
                            InlineKeyboardButton(
                                "🚫",
                                callback_data=f"blocked_date_{year}-{month:02d}-{day_num:02d}",
                            )
                        )
            else:
                selectable_dates.append(current_date.strftime('%Y-%m-%d'))
                row.append(
                    InlineKeyboardButton(
                        str(day_num),
                        callback_data=f'future_date_{year}-{month:02d}-{day_num:02d}',
                    )
                )
        keyboard.append(row)

    if flow_type == 'queue_booking':
        logger.info(
            "CALENDAR DISPLAY - Queue Booking\nSelectable dates: %d\nDates: %s",
            len(selectable_dates),
            selectable_dates,
        )

    keyboard.append([InlineKeyboardButton(f"🔙 Back to Months", callback_data=f'back_to_month_{year}')])
    return InlineKeyboardMarkup(keyboard)


def create_date_selection_keyboard(dates: List[tuple]) -> InlineKeyboardMarkup:
    """Create date selection keyboard."""

    t('botapp.ui.booking.create_date_selection_keyboard')
    keyboard = []
    for i in range(0, len(dates), 2):
        row = []
        for date_obj, label in dates[i:i+2]:
            date_str = date_obj.strftime('%Y-%m-%d')
            row.append(InlineKeyboardButton(label, callback_data=f'date_{date_str}'))
        keyboard.append(row)

    keyboard.append([InlineKeyboardButton("🔙 Back", callback_data='back_to_reserve')])
    return InlineKeyboardMarkup(keyboard)


def create_time_selection_keyboard(
    available_times: List[str],
    selected_date: str,
    flow_type: str = 'availability',
) -> InlineKeyboardMarkup:
    """Create time selection keyboard with flow-specific callbacks."""

    t('botapp.ui.booking.create_time_selection_keyboard')
    keyboard = []

    try:
        selected_date_obj = datetime.strptime(selected_date, '%Y-%m-%d').date()
        is_today = selected_date_obj == date.today()
        current_time = datetime.now()
    except ValueError:
        is_today = False
        current_time = None

    filtered_times = []
    for time_str in available_times:
        if is_today and current_time:
            try:
                hour, minute = map(int, time_str.split(':'))
                if hour < current_time.hour or (hour == current_time.hour and minute <= current_time.minute):
                    continue
            except ValueError:
                pass
        filtered_times.append(time_str)

    for i in range(0, len(filtered_times), 3):
        row = []
        for time in filtered_times[i:i+3]:
            callback_prefix = 'queue_time' if flow_type == 'queue_booking' else 'time'
            row.append(
                InlineKeyboardButton(
                    time,
                    callback_data=f'{callback_prefix}_{selected_date}_{time}',
                )
            )
        keyboard.append(row)

    back_callback = 'back_to_queue_dates' if flow_type == 'queue_booking' else 'back_to_dates'
    keyboard.append([InlineKeyboardButton("🔙 Back", callback_data=back_callback)])
    return InlineKeyboardMarkup(keyboard)


def create_time_selection_keyboard_simple(day: Optional[str] = None) -> InlineKeyboardMarkup:
    """Create time selection keyboard for modify flow (no parameters)."""

    t('botapp.ui.booking.create_time_selection_keyboard_simple')
    available_times = get_court_hours(day)
    keyboard = []
    for i in range(0, len(available_times), 3):
        row = [
            InlineKeyboardButton(time, callback_data=f'queue_time_modify_{time}')
            for time in available_times[i:i+3]
        ]
        keyboard.append(row)

    keyboard.append([InlineKeyboardButton("🔙 Back", callback_data='back_to_modify')])
    return InlineKeyboardMarkup(keyboard)


def create_modify_court_selection_keyboard() -> InlineKeyboardMarkup:
    """Create court selection keyboard for modification flows."""

    t('botapp.ui.booking.create_modify_court_selection_keyboard')
    available_courts = [1, 2, 3]
    keyboard = []
    for i in range(0, len(available_courts), 3):
        row = [
            InlineKeyboardButton(f"Court {court}", callback_data=f'queue_court_{court}')
            for court in available_courts[i:i+3]
        ]
        keyboard.append(row)

    keyboard.append([InlineKeyboardButton("All Courts", callback_data='queue_court_all')])
    keyboard.append([InlineKeyboardButton("🔙 Back", callback_data='back_to_modify')])
    return InlineKeyboardMarkup(keyboard)


def format_reservation_confirmation(reservation_details: Dict[str, Any]) -> str:
    """Format reservation confirmation message."""

    t('botapp.ui.booking.format_reservation_confirmation')
    courts_text = ', '.join([f"Court {c}" for c in reservation_details['courts']])
    message = (
        "✅ **Reservation Confirmed!**\n\n"
        f"📅 Date: {reservation_details['date']}\n"
        f"⏰ Time: {reservation_details['time']}\n"
        f"🎾 Courts: {courts_text}\n"
        f"👤 Name: {reservation_details.get('name', 'N/A')}\n"
        f"📱 Phone: {reservation_details.get('phone', 'N/A')}\n\n"
        f"Priority: {'High' if reservation_details.get('priority', 1) == 0 else 'Normal'}"
    )
    if 'confirmation_code' in reservation_details:
        message += f"\n🔑 Confirmation: {reservation_details['confirmation_code']}"

    # Add Google Calendar and Cancel/Modify links if available
    google_calendar_link = reservation_details.get('google_calendar_link')
    cancel_modify_link = reservation_details.get('cancel_modify_link')

    if google_calendar_link or cancel_modify_link:
        message += "\n\n**Actions:**"
        if google_calendar_link:
            message += f"\n📅 [Add to Google Calendar]({google_calendar_link})"
        if cancel_modify_link:
            message += f"\n✏️ [Cancel/Modify Reservation]({cancel_modify_link})"

    return message


from typing import Any  # noqa: E402  (append after top? hmm done)**

def format_reservations_list(reservations: List[Dict[str, Any]]) -> str:
    """Format a list of reservations into a user-friendly message."""

    t('botapp.ui.booking.format_reservations_list')
    if not reservations:
        return (
            "📋 **My Reservations**\n\n"
            "You have no active reservations at the moment.\n\n"
            "Use the 'Reserve Court' option to book a court!"
        )

    message = "📋 **My Reservations**\n\n"
    pending = [r for r in reservations if r.get('status') == 'pending']
    scheduled = [r for r in reservations if r.get('status') == 'scheduled']
    confirmed = [r for r in reservations if r.get('status') == 'confirmed']
    waitlisted = [r for r in reservations if r.get('status') == 'waitlisted']
    failed = [r for r in reservations if r.get('status') == 'failed']

    def _append_section(title: str, items: List[Dict[str, Any]], formatter) -> None:
        nonlocal message
        if items:
            message += f"{title}\n"
            for res in items:
                message += formatter(res)

    def _format_entry(res: Dict[str, Any], extra: str = "") -> str:
        courts_text = ', '.join([f"Court {c}" for c in res.get('courts', [])])
        base = (
            f"• {res.get('date')} at {res.get('time')}\n"
            f"  🎾 {courts_text}\n"
        )
        if extra:
            base += f"  {extra}\n"
        base += f"  🆔 ID: {res.get('id', '')[:8]}...\n\n"
        return base

    _append_section("⏳ **Pending Reservations:**", pending, lambda r: _format_entry(r))
    _append_section("📅 **Scheduled for Booking:**", scheduled, lambda r: _format_entry(r))
    _append_section(
        "✅ **Confirmed Reservations:**",
        confirmed,
        lambda r: _format_entry(r, f"🔑 Code: {r.get('confirmation_code', 'N/A')}")
    )
    _append_section(
        "📋 **Waitlisted Reservations:**",
        waitlisted,
        lambda r: _format_entry(r, f"📊 Position: #{r.get('waitlist_position', 'N/A')}")
    )

    if failed:
        message += "❌ **Recent Failed Attempts:**\n"
        for res in failed[:3]:
            courts_text = ', '.join([f"Court {c}" for c in res.get('courts', [])])
            message += (
                f"• {res.get('date')} at {res.get('time')}\n"
                f"  🎾 {courts_text}\n"
                f"  📝 Reason: {res.get('failure_reason', 'Unknown')}\n\n"
            )

    message += f"Total: {len(reservations)} reservation(s)"
    return message


def format_queue_status_message(queue_items: List[Dict[str, Any]], timezone_str: str) -> str:
    """Format queue status message."""

    t('botapp.ui.booking.format_queue_status_message')
    if not queue_items:
        return "📋 No queued reservations."

    message = f"📋 **Queued Reservations ({len(queue_items)})**\n\n"
    for idx, item in enumerate(queue_items, 1):
        courts = ', '.join([f"C{c}" for c in item['courts']])
        message += (
            f"{idx}. {item['date']} at {item['time']}\n"
            f"   Courts: {courts}\n"
            f"   Status: {item['status']}\n"
        )
        if item.get('attempts', 0) > 0:
            message += f"   Attempts: {item['attempts']}\n"
        message += "\n"
    return message


def create_pagination_keyboard(
    current_page: int,
    total_pages: int,
    callback_prefix: str,
) -> List[InlineKeyboardButton]:
    """Create pagination buttons for multi-page displays."""

    t('botapp.ui.booking.create_pagination_keyboard')
    buttons: List[InlineKeyboardButton] = []
    if current_page > 0:
        buttons.append(
            InlineKeyboardButton(
                "⬅️ Previous",
                callback_data=f"{callback_prefix}_page_{current_page-1}",
            )
        )

    buttons.append(
        InlineKeyboardButton(
            f"{current_page+1}/{total_pages}",
            callback_data=f"{callback_prefix}_current",
        )
    )

    if current_page < total_pages - 1:
        buttons.append(
            InlineKeyboardButton(
                "➡️ Next",
                callback_data=f"{callback_prefix}_page_{current_page+1}",
            )
        )

    return buttons


def format_error_message(error_type: str, details: Optional[str] = None) -> str:
    """Format standardized error messages."""

    t('botapp.ui.booking.format_error_message')
    error_messages = {
        'unauthorized': "🔐 You are not authorized to use this bot.\nPlease send /start to request access.",
        'invalid_date': "❌ Invalid date selected. Please choose a valid date.",
        'invalid_time': "❌ Invalid time selected. Please choose from available times.",
        'invalid_court': "❌ Invalid court selection. Please choose valid courts.",
        'no_availability': "😔 No courts available at this time. Please try another time slot.",
        'booking_failed': "❌ Booking failed. Please try again later.",
        'profile_incomplete': "❌ Please complete your profile first using /profile command.",
        'outside_window': "⏰ This time slot is outside the 48-hour booking window.",
        'already_booked': "🚫 You already have a reservation at this time.",
        'system_error': "❌ System error occurred. Please contact admin.",
    }

    message = error_messages.get(error_type, "❌ An error occurred.")
    if details:
        message += f"\n\nDetails: {details}"
    return message


def format_availability_message(
    available_times: Dict[int, List[str]],
    target_date: datetime,
    show_summary: bool = True,
) -> str:
    """Format court availability message."""

    t('botapp.ui.booking.format_availability_message')
    date_str = escape_telegram_markdown(target_date.strftime('%A, %B %d'), escape_special_chars=True)
    hyphen_md = escape_telegram_markdown('-', escape_special_chars=True)

    lines: List[str] = [
        "🎾 *Court Availability*",
        f"📅 {date_str}",
        "",
    ]

    if not available_times:
        lines.append("No courts available for this date.")
        return "\n".join(lines)

    times_by_slot: Dict[str, List[int]] = {}
    for court, times in available_times.items():
        for time in times:
            times_by_slot.setdefault(time, []).append(court)

    sorted_times = sorted(times_by_slot.keys())
    if show_summary:
        lines.append(
            f"⏰ Available slots: {escape_telegram_markdown(str(len(sorted_times)), escape_special_chars=True)}"
        )
        lines.append(
            f"🎾 Courts with availability: {escape_telegram_markdown(str(len(available_times)), escape_special_chars=True)}"
        )
        lines.append("")

    for time in sorted_times:
        courts = ', '.join(f"C{c}" for c in sorted(times_by_slot[time]))
        time_md = escape_telegram_markdown(time, escape_special_chars=True)
        courts_md = escape_telegram_markdown(courts, escape_special_chars=True)
        lines.append(f"• {time_md} {hyphen_md} Courts: {courts_md}")

    return "\n".join(lines)


def format_loading_message(action: str = "Processing") -> str:
    """Format a loading message."""

    t('botapp.ui.booking.format_loading_message')
    return f"⏳ {action}..."


def create_court_availability_keyboard(
    available_times: Dict[int, List[str]],
    selected_date: str,
    layout_type: str = "vertical",
    available_dates: Optional[List[str]] = None,
    *,
    callback_prefix: str = "book_now",
    cycle_prefix: str = "cycle_day_",
    unavailable_prefix: str = "unavailable",
) -> InlineKeyboardMarkup:
    """Create interactive court availability keyboard for immediate booking."""

    t('botapp.ui.booking.create_court_availability_keyboard')
    if layout_type == "matrix":
        return _create_matrix_layout_keyboard(
            available_times,
            selected_date,
            available_dates,
            callback_prefix=callback_prefix,
            cycle_prefix=cycle_prefix,
            unavailable_prefix=unavailable_prefix,
        )
    return _create_vertical_layout_keyboard(available_times, selected_date)


def _create_vertical_layout_keyboard(
    available_times: Dict[int, List[str]],
    selected_date: str,
) -> InlineKeyboardMarkup:
    """Create vertical layout keyboard (current implementation)."""

    t('botapp.ui.booking._create_vertical_layout_keyboard')
    keyboard: List[List[InlineKeyboardButton]] = []
    sorted_courts = sorted(available_times.keys())
    max_times_per_row = 3

    for court_num in sorted_courts:
        times = available_times[court_num]
        if not times:
            continue

        keyboard.append([
            InlineKeyboardButton(
                f"🎾 Court {court_num}", callback_data=f"court_header_{court_num}"
            )
        ])

        for i in range(0, len(times), max_times_per_row):
            row = []
            for time in times[i:i+max_times_per_row]:
                display_time = time.split(' - ')[0] if ' - ' in time else time
                row.append(
                    InlineKeyboardButton(
                        display_time,
                        callback_data=f"book_now_{selected_date}_{court_num}_{display_time}",
                    )
                )
            keyboard.append(row)

    keyboard.append([InlineKeyboardButton("🔙 Back to Menu", callback_data='back_to_menu')])
    return InlineKeyboardMarkup(keyboard)


def _create_matrix_layout_keyboard(
    available_times: Dict[int, List[str]],
    selected_date: str,
    available_dates: Optional[List[str]] = None,
    *,
    callback_prefix: str,
    cycle_prefix: str,
    unavailable_prefix: str,
) -> InlineKeyboardMarkup:
    """Create matrix layout keyboard (new grid format)."""

    t('botapp.ui.booking._create_matrix_layout_keyboard')
    logger = logging.getLogger(__name__)
    logger.info("🎯 TELEGRAM DISPLAY - Creating matrix for date: %s", selected_date)
    logger.info("📊 Available times by court: %s", available_times)

    keyboard: List[List[InlineKeyboardButton]] = []
    time_matrix = _build_time_matrix(available_times)
    filtered_matrix = _filter_empty_time_rows(time_matrix)

    logger.info("🔢 Time matrix built: %s", time_matrix)
    logger.info("📋 Filtered matrix (shown to user): %s", filtered_matrix)

    if not filtered_matrix:
        keyboard.append([InlineKeyboardButton("🔙 Back to Menu", callback_data='back_to_menu')])
        return InlineKeyboardMarkup(keyboard)

    all_courts = [1, 2, 3]

    if available_dates and len(available_dates) > 1:
        day_label = _get_day_label_for_date(selected_date)
        next_date = _get_next_day(selected_date, available_dates)
        keyboard.append([
            InlineKeyboardButton(
                f"📅 {day_label} (tap to cycle)",
                callback_data=f"{cycle_prefix}{next_date}",
            )
        ])

    keyboard.append([
        InlineKeyboardButton(f"🎾 Court {court}", callback_data=f"court_header_{court}")
        for court in all_courts
    ])

    for time_slot in sorted(filtered_matrix.keys()):
        status = " ".join(
            f"C{court}:{'✅' if filtered_matrix[time_slot].get(court, False) else '❌'}"
            for court in all_courts
        )
        logger.info("⏰ %s | %s", time_slot, status)

    keyboard.extend(
        _create_matrix_keyboard_rows(
            filtered_matrix,
            selected_date,
            all_courts,
            callback_prefix=callback_prefix,
            unavailable_prefix=unavailable_prefix,
        )
    )
    keyboard.append([InlineKeyboardButton("🔙 Back to Menu", callback_data='back_to_menu')])
    return InlineKeyboardMarkup(keyboard)


def _build_time_matrix(available_times: Dict[int, List[str]]) -> Dict[str, Dict[int, bool]]:
    """Build time matrix mapping time slots to court availability."""

    t('botapp.ui.booking._build_time_matrix')
    time_matrix: Dict[str, Dict[int, bool]] = {}
    all_times = set()
    for times in available_times.values():
        for time in times:
            display_time = time.split(' - ')[0] if ' - ' in time else time
            all_times.add(display_time)

    all_courts = [1, 2, 3]
    for time_slot in all_times:
        time_matrix[time_slot] = {}
        for court_num in all_courts:
            court_times = available_times.get(court_num, [])
            is_available = any(
                time_slot == (time.split(' - ')[0] if ' - ' in time else time)
                for time in court_times
            )
            time_matrix[time_slot][court_num] = is_available
    return time_matrix


def _filter_empty_time_rows(time_matrix: Dict[str, Dict[int, bool]]) -> Dict[str, Dict[int, bool]]:
    """Filter out time rows where no courts are available."""

    t('botapp.ui.booking._filter_empty_time_rows')
    return {
        time_slot: availability
        for time_slot, availability in time_matrix.items()
        if any(availability.values())
    }


def _create_matrix_keyboard_rows(
    time_matrix: Dict[str, Dict[int, bool]],
    selected_date: str,
    all_courts: List[int],
    *,
    callback_prefix: str,
    unavailable_prefix: str,
) -> List[List[InlineKeyboardButton]]:
    """Create keyboard rows from filtered time matrix."""

    t('botapp.ui.booking._create_matrix_keyboard_rows')
    keyboard_rows: List[List[InlineKeyboardButton]] = []
    sorted_times = sorted(
        time_matrix.keys(), key=lambda t: (int(t.split(':')[0]), int(t.split(':')[1]))
    )

    for time_slot in sorted_times:
        court_availability = time_matrix[time_slot]
        row = []
        for court_num in all_courts:
            if court_availability.get(court_num, False):
                row.append(
                    InlineKeyboardButton(
                        time_slot,
                        callback_data=f"{callback_prefix}_{selected_date}_{court_num}_{time_slot}",
                    )
                )
            else:
                row.append(
                    InlineKeyboardButton(
                        "-",
                        callback_data=f"{unavailable_prefix}_{court_num}_{time_slot}",
                    )
                )
        keyboard_rows.append(row)
    return keyboard_rows


def _get_day_label_for_date(date_str: str) -> str:
    """Get day label for a date string."""

    t('botapp.ui.booking._get_day_label_for_date')
    try:
        target_date = datetime.strptime(date_str, '%Y-%m-%d').date()
        today = datetime.now().date()
        if target_date == today:
            return "Today"
        if target_date == today + timedelta(days=1):
            return "Tomorrow"
        return target_date.strftime('%A')
    except ValueError:
        return "Selected Day"


def _get_next_day(current_date: str, available_dates: List[str]) -> str:
    """Get next available date for intelligent day cycling."""

    t('botapp.ui.booking._get_next_day')
    if not available_dates:
        return current_date
    if len(available_dates) == 1:
        return available_dates[0]
    try:
        current_index = available_dates.index(current_date)
        return available_dates[(current_index + 1) % len(available_dates)]
    except ValueError:
        return available_dates[0]


def format_interactive_availability_message(
    available_times: Dict[int, List[str]],
    target_date: datetime,
    total_slots: Optional[int] = None,
    layout_type: str = "vertical",
) -> str:
    """Format court availability message for interactive booking UI."""

    t('botapp.ui.booking.format_interactive_availability_message')
    if total_slots is None:
        total_slots = sum(len(times) for times in available_times.values())

    if hasattr(target_date, 'date'):
        date_obj = target_date.date()
    else:
        date_obj = target_date

    today = datetime.now().date()
    if date_obj == today:
        day_label = "Today"
    elif date_obj == today + timedelta(days=1):
        day_label = "Tomorrow"
    else:
        day_label = date_obj.strftime('%A')

    day_label_md = escape_telegram_markdown(day_label, escape_special_chars=True)
    total_slots_md = escape_telegram_markdown(str(total_slots), escape_special_chars=True)
    hyphen_md = escape_telegram_markdown('-', escape_special_chars=True)

    return (
        "🎾 *Online Court Availability*\n\n"
        "Select a time to reserve:\n\n"
        f"📅 *{day_label_md} {hyphen_md} {total_slots_md} slots available*"
    )


__all__ = [
    'create_court_selection_keyboard',
    'create_queue_court_selection_keyboard',
    'create_queue_confirmation_keyboard',
    'create_day_selection_keyboard',
    'create_date_selection_keyboard',
    'create_time_selection_keyboard',
    'create_time_selection_keyboard_simple',
    'create_modify_court_selection_keyboard',
    'create_court_availability_keyboard',
    'format_reservation_confirmation',
    'format_reservations_list',
    'format_queue_status_message',
    'format_availability_message',
    'format_error_message',
    'format_loading_message',
    'format_interactive_availability_message',
    'create_pagination_keyboard',
]
