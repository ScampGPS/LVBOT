"""Test to send confirmation message with booking links from latest logs.

This test hijacks the Telegram bot token to send the user a confirmation
message with the calendar links extracted from the latest booking logs.

This uses the production notification code to ensure consistency.
"""
from tracking import t

import asyncio
import json
import re
from pathlib import Path

import pytest
from telegram import Bot

from automation.shared.booking_contracts import BookingResult, BookingStatus, BookingUser
from botapp.notifications import send_success_notification
from infrastructure.settings import get_settings


# User ID from logs
USER_ID = 125763357

# Booking details from logs
BOOKING_INFO = {
    "court": 1,
    "date": "2025-11-07",
    "time": "13:00",
    "google_calendar_link": "https://www.google.com/calendar/render?action=TEMPLATE&text=TENNIS+CANCHA+1+%28A+TENNIS+CANCHA+1%29&dates=20251106T190000Z/20251106T200000Z&location=&details=%0A%0AVer%2Fmodificar+cita%3A%0Ahttps%3A%2F%2Fapp.acuityscheduling.com%2Fschedule.php%3Fowner%3D20292217%26id%255B%255D%3D89ba3b12a8cdd5e7587c820291cd3248%26action%3Dappt%26ref%3Dcalendar%0A%0A%28created+by+Acuity+Scheduling%29%0AAcuityID%3D1567952495%0AGoogle&sf=true&output=xml",
    "cancel_modify_link": "https://app.acuityscheduling.com/schedule.php?owner=20292217&action=appt&id%5B%5D=89ba3b12a8cdd5e7587c820291cd3248",
    "ics_calendar_link": "https://app.acuityscheduling.com/schedule.php?owner=20292217&action=appt&m=ics&id%5B%5D=89ba3b12a8cdd5e7587c820291cd3248",
}


def create_booking_result_from_log_data(booking_info: dict) -> BookingResult:
    """Create a BookingResult object from log data to use production notification code."""
    t('tests.bot.test_send_confirmation_message.create_booking_result_from_log_data')

    user = BookingUser(
        user_id=USER_ID,
        first_name="SAULIN",
        last_name="CAMPOS",
        email="msaulcampos@gmail.com",
        phone="31874277",
        tier=None
    )

    metadata = {
        "target_date": booking_info["date"],
        "target_time": booking_info["time"],
        "google_calendar_link": booking_info["google_calendar_link"],
        "cancel_modify_link": booking_info["cancel_modify_link"],
        "ics_calendar_link": booking_info["ics_calendar_link"],
        "source": "test",
    }

    return BookingResult(
        status=BookingStatus.SUCCESS,
        user=user,
        request_id="test_manual_confirmation",
        court_reserved=booking_info["court"],
        time_reserved=booking_info["time"],
        confirmation_code=None,
        confirmation_url=None,
        message="Your tennis court has been successfully booked!",
        errors=(),
        metadata=metadata,
    )


async def send_confirmation_to_user(language: str = "es"):
    """Send the confirmation message to the user via Telegram using production code.

    Args:
        language: Language code ('es' for Spanish, 'en' for English)
    """
    t('tests.bot.test_send_confirmation_message.send_confirmation_to_user')

    # Get bot token from settings
    settings = get_settings()
    bot_token = settings.bot_token

    # Create bot instance
    bot = Bot(token=bot_token)

    # Create BookingResult using production data structures
    booking_result = create_booking_result_from_log_data(BOOKING_INFO)

    # Use production notification formatter with language support
    notification_payload = send_success_notification(USER_ID, booking_result, language=language)

    print(f"\n{'='*60}")
    print("Sending confirmation message to user...")
    print(f"User ID: {USER_ID}")
    print(f"Language: {language.upper()}")
    print(f"Court: {BOOKING_INFO['court']}")
    print(f"Date: {BOOKING_INFO['date']}")
    print(f"Time: {BOOKING_INFO['time']}")
    print(f"{'='*60}\n")
    print("Using PRODUCTION notification code with i18n support!")
    print(f"{'='*60}\n")

    # Send the message with production formatting
    try:
        sent_message = await bot.send_message(
            chat_id=notification_payload["user_id"],
            text=notification_payload["message"],
            parse_mode=notification_payload["parse_mode"],
            reply_markup=notification_payload["reply_markup"],
        )

        print("[SUCCESS] Message sent successfully!")
        print(f"Message ID: {sent_message.message_id}")
        print(f"Chat ID: {sent_message.chat_id}")
        print(f"Has inline keyboard: {sent_message.reply_markup is not None}")
        if sent_message.reply_markup:
            button_count = sum(len(row) for row in sent_message.reply_markup.inline_keyboard)
            print(f"Number of buttons: {button_count}")
        return sent_message

    except Exception as e:
        print(f"[FAILED] Failed to send message: {e}")
        raise


@pytest.mark.asyncio
async def test_send_confirmation_message_spanish():
    """Test sending confirmation message with booking links to user in Spanish."""
    t('tests.bot.test_send_confirmation_message.test_send_confirmation_message_spanish')

    result = await send_confirmation_to_user(language="es")

    # Verify message was sent
    assert result is not None
    assert result.message_id > 0
    assert result.chat_id == USER_ID
    assert "Reserva Confirmada" in result.text

    # Verify inline keyboard buttons are present
    assert result.reply_markup is not None
    assert len(result.reply_markup.inline_keyboard) > 0

    # Verify we have the calendar buttons in Spanish
    button_texts = []
    for row in result.reply_markup.inline_keyboard:
        for button in row:
            button_texts.append(button.text)

    assert any("Google Calendar" in text for text in button_texts)
    assert any("Outlook/iCal" in text for text in button_texts)
    assert any("Cancelar" in text or "Modificar" in text for text in button_texts)


@pytest.mark.asyncio
async def test_send_confirmation_message_english():
    """Test sending confirmation message with booking links to user in English."""
    t('tests.bot.test_send_confirmation_message.test_send_confirmation_message_english')

    result = await send_confirmation_to_user(language="en")

    # Verify message was sent
    assert result is not None
    assert result.message_id > 0
    assert result.chat_id == USER_ID
    assert "Booking Confirmed" in result.text

    # Verify inline keyboard buttons are present
    assert result.reply_markup is not None
    assert len(result.reply_markup.inline_keyboard) > 0

    # Verify we have the calendar buttons in English
    button_texts = []
    for row in result.reply_markup.inline_keyboard:
        for button in row:
            button_texts.append(button.text)

    assert any("Google Calendar" in text for text in button_texts)
    assert any("Outlook/iCal" in text for text in button_texts)
    assert any("Cancel" in text or "Modify" in text for text in button_texts)


def extract_links_from_logs(log_file_path: Path) -> dict:
    """Extract booking links from log file for future use.

    This function can be used to dynamically parse logs instead of hardcoding.
    """
    t('tests.bot.test_send_confirmation_message.extract_links_from_logs')

    if not log_file_path.exists():
        return {}

    log_content = log_file_path.read_text(encoding='utf-8')

    # Patterns to extract links
    google_pattern = r"'google_calendar_link': '(https://www\.google\.com/calendar/render[^']+)'"
    cancel_pattern = r"'cancel_modify_link': '(https://app\.acuityscheduling\.com/schedule\.php[^']+)'"
    ics_pattern = r"'ics_calendar_link': '(https://app\.acuityscheduling\.com/schedule\.php[^']+m=ics[^']+)'"

    links = {}

    google_match = re.search(google_pattern, log_content)
    if google_match:
        links['google_calendar_link'] = google_match.group(1)

    cancel_match = re.search(cancel_pattern, log_content)
    if cancel_match:
        links['cancel_modify_link'] = cancel_match.group(1)

    ics_match = re.search(ics_pattern, log_content)
    if ics_match:
        links['ics_calendar_link'] = ics_match.group(1)

    return links


if __name__ == "__main__":
    # Run the test directly
    asyncio.run(send_confirmation_to_user())
