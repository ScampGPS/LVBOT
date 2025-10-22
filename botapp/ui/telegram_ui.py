"""Backwards-compatible facade for Telegram UI helpers."""

from __future__ import annotations

from .admin import create_admin_menu_keyboard as _create_admin_menu_keyboard
from .booking import (
    create_court_availability_keyboard as _create_court_availability_keyboard,
    create_court_selection_keyboard as _create_court_selection_keyboard,
    create_date_selection_keyboard as _create_date_selection_keyboard,
    create_day_selection_keyboard as _create_day_selection_keyboard,
    create_modify_court_selection_keyboard as _create_modify_court_selection_keyboard,
    create_pagination_keyboard as _create_pagination_keyboard,
    create_queue_confirmation_keyboard as _create_queue_confirmation_keyboard,
    create_queue_court_selection_keyboard as _create_queue_court_selection_keyboard,
    create_time_selection_keyboard as _create_time_selection_keyboard,
    create_time_selection_keyboard_simple as _create_time_selection_keyboard_simple,
    format_availability_message as _format_availability_message,
    format_error_message as _format_error_message,
    format_interactive_availability_message as _format_interactive_availability_message,
    format_loading_message as _format_loading_message,
    format_queue_status_message as _format_queue_status_message,
    format_reservation_confirmation as _format_reservation_confirmation,
    format_reservations_list as _format_reservations_list,
)
from .menus import (
    create_48h_booking_type_keyboard as _create_48h_booking_type_keyboard,
    create_back_to_menu_keyboard as _create_back_to_menu_keyboard,
    create_cancel_keyboard as _create_cancel_keyboard,
    create_main_menu_keyboard as _create_main_menu_keyboard,
    create_month_selection_keyboard as _create_month_selection_keyboard,
    create_year_selection_keyboard as _create_year_selection_keyboard,
    create_yes_no_keyboard as _create_yes_no_keyboard,
)
from .profile import (
    create_cancel_edit_keyboard as _create_cancel_edit_keyboard,
    create_email_char_keyboard as _create_email_char_keyboard,
    create_email_confirm_keyboard as _create_email_confirm_keyboard,
    create_edit_profile_keyboard as _create_edit_profile_keyboard,
    create_letter_keyboard as _create_letter_keyboard,
    create_name_type_keyboard as _create_name_type_keyboard,
    create_phone_keypad as _create_phone_keypad,
    create_profile_keyboard as _create_profile_keyboard,
    format_user_profile_message as _format_user_profile_message,
    format_user_tier_badge as _format_user_tier_badge,
)
from .queue import (
    format_time_selection_prompt as _format_time_selection_prompt,
    format_no_time_slots_message as _format_no_time_slots_message,
    format_confirmation_message as _format_queue_confirmation_message,
    format_cancellation_message as _format_queue_cancellation_message,
)


class TelegramUI:
    """Compatibility facade mapping to modular UI helpers."""

    create_main_menu_keyboard = staticmethod(_create_main_menu_keyboard)
    create_yes_no_keyboard = staticmethod(_create_yes_no_keyboard)
    create_cancel_keyboard = staticmethod(_create_cancel_keyboard)
    create_back_to_menu_keyboard = staticmethod(_create_back_to_menu_keyboard)
    create_48h_booking_type_keyboard = staticmethod(_create_48h_booking_type_keyboard)
    create_year_selection_keyboard = staticmethod(_create_year_selection_keyboard)
    create_month_selection_keyboard = staticmethod(_create_month_selection_keyboard)

    create_court_selection_keyboard = staticmethod(_create_court_selection_keyboard)
    create_queue_court_selection_keyboard = staticmethod(_create_queue_court_selection_keyboard)
    create_queue_confirmation_keyboard = staticmethod(_create_queue_confirmation_keyboard)
    create_day_selection_keyboard = staticmethod(_create_day_selection_keyboard)
    create_date_selection_keyboard = staticmethod(_create_date_selection_keyboard)
    create_time_selection_keyboard = staticmethod(_create_time_selection_keyboard)
    create_time_selection_keyboard_simple = staticmethod(_create_time_selection_keyboard_simple)
    create_modify_court_selection_keyboard = staticmethod(_create_modify_court_selection_keyboard)
    create_court_availability_keyboard = staticmethod(_create_court_availability_keyboard)
    create_pagination_keyboard = staticmethod(_create_pagination_keyboard)

    create_profile_keyboard = staticmethod(_create_profile_keyboard)
    create_edit_profile_keyboard = staticmethod(_create_edit_profile_keyboard)
    create_cancel_edit_keyboard = staticmethod(_create_cancel_edit_keyboard)
    create_phone_keypad = staticmethod(_create_phone_keypad)
    create_name_type_keyboard = staticmethod(_create_name_type_keyboard)
    create_letter_keyboard = staticmethod(_create_letter_keyboard)
    create_email_confirm_keyboard = staticmethod(_create_email_confirm_keyboard)
    create_email_char_keyboard = staticmethod(_create_email_char_keyboard)

    create_admin_menu_keyboard = staticmethod(_create_admin_menu_keyboard)

    format_reservation_confirmation = staticmethod(_format_reservation_confirmation)
    format_reservations_list = staticmethod(_format_reservations_list)
    format_queue_status_message = staticmethod(_format_queue_status_message)
    format_availability_message = staticmethod(_format_availability_message)
    format_error_message = staticmethod(_format_error_message)
    format_loading_message = staticmethod(_format_loading_message)
    format_interactive_availability_message = staticmethod(_format_interactive_availability_message)
    format_user_profile_message = staticmethod(_format_user_profile_message)
    format_user_tier_badge = staticmethod(_format_user_tier_badge)
    format_queue_time_prompt = staticmethod(_format_time_selection_prompt)
    format_queue_no_times = staticmethod(_format_no_time_slots_message)
    format_queue_confirmation_message = staticmethod(_format_queue_confirmation_message)
    format_queue_cancellation_message = staticmethod(_format_queue_cancellation_message)


__all__ = ['TelegramUI']
