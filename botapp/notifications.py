"""Notification helpers that operate on shared booking results."""

from __future__ import annotations

import asyncio
from datetime import datetime
from typing import Any, Dict, Optional, Sequence, Union, NamedTuple

from tracking import t

from automation.shared.booking_contracts import BookingResult
from botapp.i18n.translator import Translator, create_translator
from botapp.ui.telegram_ui import TelegramUI
from botapp.ui.text_blocks import (
    MarkdownBlockBuilder,
    MarkdownBuilderBase,
    escape_telegram_markdown,
    bold_telegram_text,
)
from infrastructure.settings import TestModeConfig
from telegram import InlineKeyboardButton, InlineKeyboardMarkup

_WEEKDAY_KEYS = [
    "day.monday",
    "day.tuesday",
    "day.wednesday",
    "day.thursday",
    "day.friday",
    "day.saturday",
    "day.sunday",
]

_MONTH_KEYS = [
    "month.january",
    "month.february",
    "month.march",
    "month.april",
    "month.may",
    "month.june",
    "month.july",
    "month.august",
    "month.september",
    "month.october",
    "month.november",
    "month.december",
]

# Deprecated: Use translator instead
SUCCESS_HEADER = "✅ *Booking Confirmed!*"
FAILURE_HEADER = "❌ *Booking Attempt Failed*"


class NotificationBuilder(MarkdownBuilderBase):
    """Build common booking notifications with shared Markdown formatting."""

    def __init__(self, builder_factory=MarkdownBlockBuilder, translator: Optional[Translator] = None) -> None:
        t('botapp.notifications.NotificationBuilder.__init__')
        super().__init__(builder_factory=builder_factory)
        self.translator = translator or create_translator()

    def success_message(self, result: BookingResult) -> str:
        t('botapp.notifications.NotificationBuilder.success_message')
        builder = self.create_builder().heading(self.translator.t("notif.booking_confirmed"))

        if result.court_reserved:
            builder.bullet(f"{self.translator.t('notif.court')}: {result.court_reserved}")
        if result.time_reserved:
            builder.bullet(f"{self.translator.t('notif.time')}: {result.time_reserved}")
        if result.confirmation_code:
            builder.bullet(f"{self.translator.t('notif.confirmation')}: `{result.confirmation_code}`")

        if result.message:
            builder.blank().line(result.message)

        # Note: Calendar links are now shown as inline buttons instead of text links
        builder.blank().line(self.translator.t("notif.calendar_help"))

        return builder.build()

    def failure_message(self, result: BookingResult) -> str:
        t('botapp.notifications.NotificationBuilder.failure_message')
        builder = self.create_builder().heading(self.translator.t("notif.booking_failed"))

        if result.message:
            builder.line(result.message)
        if result.errors:
            builder.blank().bullets(result.errors)

        return builder.build()

    def duplicate_warning(self, error_message: str) -> str:
        t('botapp.notifications.NotificationBuilder.duplicate_warning')
        lines = [
            f"⚠️ {bold_telegram_text(self.translator.t('notif.duplicate_warning'), escape_special_chars=True)}",
            "",
            escape_telegram_markdown(error_message, escape_special_chars=True),
            "",
            escape_telegram_markdown(
                self.translator.t("notif.duplicate_message"),
                escape_special_chars=True,
            ),
        ]
        return "\n".join(lines)

    def queue_reservation_added(
        self,
        booking_summary: Dict[str, object],
        reservation_id: str,
        *,
        test_mode_config: TestModeConfig,
    ) -> str:
        t('botapp.notifications.NotificationBuilder.queue_reservation_added')
        date_obj = datetime.strptime(
            booking_summary["target_date"], "%Y-%m-%d"
        ).date()
        weekday_label = self.translator.t(_WEEKDAY_KEYS[date_obj.weekday()])
        month_label = self.translator.t(_MONTH_KEYS[date_obj.month - 1])
        display_date = f"{weekday_label}, {month_label} {date_obj.day:02d}, {date_obj.year}"
        courts = booking_summary.get("court_preferences", [])

        if isinstance(courts, str) and courts == "all":
            courts_label = self.translator.t("court.all")
        else:
            court_values: Sequence[int] = courts if isinstance(courts, Sequence) else []
            courts_label = (
                ", ".join(
                    self.translator.t("court.label", number=court)
                    for court in sorted(court_values)
                )
                or self.translator.t("court.all")
            )

        lines = [
            escape_telegram_markdown(
                self.translator.t("notif.queue_added"),
                escape_special_chars=True,
            ),
            "",
            f"{self.translator.t('notif.date')}: {escape_telegram_markdown(display_date, escape_special_chars=True)}",
            f"{self.translator.t('notif.time')}: {escape_telegram_markdown(booking_summary['target_time'], escape_special_chars=True)}",
            f"{self.translator.t('notif.courts')}: {escape_telegram_markdown(courts_label, escape_special_chars=True)}",
            "",
            f"{escape_telegram_markdown(self.translator.t('notif.queue_id'), escape_special_chars=True)} {escape_telegram_markdown(reservation_id[:8] + '...', escape_special_chars=True)}",
            "",
        ]

        if test_mode_config.enabled:
            lines.append(
                escape_telegram_markdown(
                    self.translator.t("notif.queue_test_mode"),
                    escape_special_chars=True,
                )
            )
            lines.append(
                escape_telegram_markdown(
                    self.translator.t(
                        "notif.queue_test_eta",
                        minutes=test_mode_config.trigger_delay_minutes,
                    ),
                    escape_special_chars=True,
                )
            )
            lines.append("")
        else:
            lines.append(
                escape_telegram_markdown(
                    self.translator.t("notif.queue_added_description"),
                    escape_special_chars=True,
                )
            )
            lines.append("")

        lines.append(
            escape_telegram_markdown(
                self.translator.t("notif.queue_view_hint"),
                escape_special_chars=True,
            )
        )

        return "\n".join(lines)


_NOTIFICATIONS = NotificationBuilder()


def _format_notification(method_name: str, doc: str):
    t('botapp.notifications._format_notification')
    def _format(result: BookingResult, language: Optional[str] = None) -> str:
        # Create builder with appropriate translator if language is specified
        t('botapp.notifications._format_notification._format')
        if language:
            translator = create_translator(language)
            builder = NotificationBuilder(translator=translator)
        else:
            builder = _NOTIFICATIONS

        builder_method = getattr(builder, method_name)
        return builder_method(result)

    _format.__name__ = f"format_{method_name}"
    _format.__doc__ = doc
    return _format


format_success_message = _format_notification(
    "success_message",
    "Generate a Markdown-formatted success message.",
)

format_failure_message = _format_notification(
    "failure_message",
    "Generate a Markdown-formatted failure message with error context.",
)


def _send_notification(
    formatter,
    user_id: int,
    result: BookingResult,
    language: Optional[str] = None,
) -> Dict[str, object]:
    # Build inline keyboard with calendar links and cancel button
    t('botapp.notifications._send_notification')
    keyboard = []

    # Create translator for button text
    translator = create_translator(language) if language else create_translator()

    # Extract links from metadata
    google_calendar_link = result.metadata.get("google_calendar_link")
    ics_calendar_link = result.metadata.get("ics_calendar_link")
    cancel_modify_link = result.metadata.get("cancel_modify_link")

    # Add calendar buttons (first row)
    calendar_row = []
    if google_calendar_link:
        calendar_row.append(InlineKeyboardButton(translator.t("calendar.add_google"), url=google_calendar_link))
    if ics_calendar_link:
        calendar_row.append(InlineKeyboardButton(translator.t("calendar.add_outlook"), url=ics_calendar_link))
    if calendar_row:
        keyboard.append(calendar_row)

    # Add cancel/modify button (second row)
    if cancel_modify_link:
        keyboard.append([
            InlineKeyboardButton(
                translator.t("reservation.cancel_modify"),
                url=cancel_modify_link
            )
        ])

    # Create inline keyboard markup if we have buttons
    reply_markup = InlineKeyboardMarkup(keyboard) if keyboard else TelegramUI.create_back_to_menu_keyboard()

    return {
        "user_id": user_id,
        "message": formatter(result, language=language),
        "parse_mode": "Markdown",
        "reply_markup": reply_markup,
    }


def send_success_notification(user_id: int, result: BookingResult, language: Optional[str] = None) -> Dict[str, object]:
    """Prepare payload for delivering a success notification to Telegram."""
    t('botapp.notifications.send_success_notification')

    return _send_notification(format_success_message, user_id, result, language=language)


def send_failure_notification(
    user_id: int,
    result: BookingResult,
    language: Optional[str] = None,
) -> Dict[str, object]:
    """Prepare payload for delivering a failure notification to Telegram."""
    t('botapp.notifications.send_failure_notification')

    return _send_notification(format_failure_message, user_id, result, language=language)


def format_queue_reservation_added(
    booking_summary: Dict[str, object],
    reservation_id: str,
    *,
    test_mode_config: TestModeConfig,
) -> str:
    """Build the confirmation message when a queue reservation is added."""
    t('botapp.notifications.format_queue_reservation_added')

    return _NOTIFICATIONS.queue_reservation_added(
        booking_summary,
        reservation_id,
        test_mode_config=test_mode_config,
    )


def format_duplicate_reservation_message(error_message: str) -> str:
    """Build a user-friendly duplicate reservation warning message."""
    t('botapp.notifications.format_duplicate_reservation_message')

    return _NOTIFICATIONS.duplicate_warning(error_message)


class _NotificationPayload(NamedTuple):
    text: str
    parse_mode: str
    reply_markup: Any
    preview: str


def _normalize_notification_payload(message: Union[str, Dict[str, Any]]) -> _NotificationPayload:
    """Normalize notification payloads so delivery always receives text + markup."""
    t('botapp.notifications._normalize_notification_payload')

    if isinstance(message, dict):
        text = message.get("message") or message.get("text") or ""
        parse_mode = message.get("parse_mode") or "Markdown"
        reply_markup = message.get("reply_markup")
    else:
        text = message or ""
        parse_mode = "Markdown"
        reply_markup = None

    preview = text[:50] if text else ""
    return _NotificationPayload(text=text, parse_mode=parse_mode, reply_markup=reply_markup, preview=preview)


async def deliver_notification_with_menu(
    application,
    user_manager,
    user_id: int,
    message: Union[str, Dict[str, Any]],
    *,
    logger,
    follow_up_delay_seconds: int = 7,
) -> None:
    """Send a notification and optionally follow up with the main menu."""

    t("botapp.notifications.deliver_notification_with_menu")

    if not application:
        logger.warning("No application context for notification to %s", user_id)
        return

    payload = _normalize_notification_payload(message)
    if not payload.text:
        logger.warning("Skipping notification to %s - empty message payload", user_id)
        return

    await application.bot.send_message(
        chat_id=user_id,
        text=payload.text,
        parse_mode=payload.parse_mode,
        reply_markup=payload.reply_markup,
    )
    logger.info("Sent notification to %s: %s", user_id, payload.preview)

    def _looks_like_booking_result(text: str) -> bool:
        t('botapp.notifications.deliver_notification_with_menu._looks_like_booking_result')
        lower_text = text.lower()
        return (
            ("✅" in text and ("reservation" in lower_text or "booked" in lower_text))
            or ("❌" in text and "reservation" in lower_text)
            or ("⚠️" in text and "booking" in lower_text)
        )

    if not _looks_like_booking_result(payload.text):
        return

    await asyncio.sleep(max(0, follow_up_delay_seconds))

    is_admin = user_manager.is_admin(user_id)
    tier = user_manager.get_user_tier(user_id)
    tier_badge = TelegramUI.format_user_tier_badge(tier.name)

    reply_markup = TelegramUI.create_main_menu_keyboard(is_admin=is_admin)
    await application.bot.send_message(
        chat_id=user_id,
        text=f"🎾 What would you like to do next? {tier_badge}",
        reply_markup=reply_markup,
    )
    logger.info("Sent main menu follow-up to %s", user_id)


__all__ = [
    "NotificationBuilder",
    "format_success_message",
    "format_failure_message",
    "send_success_notification",
    "send_failure_notification",
    "format_queue_reservation_added",
    "format_duplicate_reservation_message",
    "deliver_notification_with_menu",
]
