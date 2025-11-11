"""Queue booking specific UI formatters."""

from __future__ import annotations
from tracking import t

from datetime import date
from botapp.ui.text_blocks import escape_telegram_markdown, bold_telegram_text
from botapp.i18n import get_translator


def _md(value: object) -> str:
    """Escape text for Telegram Markdown with special character escaping."""
    t('botapp.ui.queue._md')
    return escape_telegram_markdown(value, escape_special_chars=True)


def _bold(value: object) -> str:
    """Return bold Markdown text with proper escaping."""
    t('botapp.ui.queue._bold')
    return bold_telegram_text(value, escape_special_chars=True)


def _resolve_translator(translator=None, language=None):
    """Return a translator instance honoring overrides."""

    t('botapp.ui.queue._resolve_translator')
    if translator is not None:
        return translator
    return get_translator(language)


def format_time_selection_prompt(
    selected_date: date,
    availability_note: str | None = None,
    *,
    translator=None,
    language=None,
) -> str:
    """Return the message shown before picking a time slot."""

    t('botapp.ui.queue.format_time_selection_prompt')
    tr = _resolve_translator(translator, language)
    lines = [
        f"⏰ {_bold(tr.t('queue.booking_title'))}",
        "",
        _md(tr.t('queue.selected_date', date=selected_date.strftime('%A, %B %d, %Y'))),
        "",
        _md(tr.t('queue.select_time')),
    ]
    if availability_note:
        lines.append(_md(availability_note))
    return "\n".join(lines)


def format_no_time_slots_message(
    selected_date: date,
    *,
    translator=None,
    language=None,
) -> str:
    """Return the message shown when no time slots remain."""

    t('botapp.ui.queue.format_no_time_slots_message')
    tr = _resolve_translator(translator, language)
    return "\n".join(
        [
            f"⚠️ {_bold(tr.t('queue.no_slots_title'))}",
            "",
            _md(tr.t('queue.selected_date', date=selected_date.strftime('%A, %B %d, %Y'))),
            "",
            _md(tr.t('queue.no_slots_within_window')),
            _md(tr.t('queue.no_slots_cta')),
        ]
    )


def format_confirmation_message(
    selected_date: date,
    selected_time: str,
    courts_text: str,
    *,
    translator=None,
    language=None,
) -> str:
    """Return the queue confirmation summary shown before enqueueing."""

    t('botapp.ui.queue.format_confirmation_message')
    tr = _resolve_translator(translator, language)
    lines = [
        f"⏰ {_bold(tr.t('queue.confirmation_title'))}",
        "",
        f"{tr.t('notif.date')}: {_md(selected_date.strftime('%A, %B %d, %Y'))}",
        f"{tr.t('notif.time')}: {_md(selected_time)}",
        f"{tr.t('notif.courts')}: {_md(courts_text)}",
        "",
        _md(tr.t('queue.confirmation_notice')),
        "",
        _bold(tr.t('queue.confirmation_cta')),
    ]
    return "\n".join(lines)


def format_cancellation_message(*, translator=None, language=None) -> str:
    """Return the user-facing cancellation message."""

    t('botapp.ui.queue.format_cancellation_message')
    tr = _resolve_translator(translator, language)
    return "\n".join(
        [
            f"❌ {_bold(tr.t('queue.cancelled_title'))}",
            "",
            _md(tr.t('queue.cancelled_body')),
            "",
            _md(tr.t('queue.cancelled_cta')),
        ]
    )


def format_court_selection_prompt(
    selected_date: date,
    selected_time: str,
    *,
    translator=None,
    language=None,
) -> str:
    """Return the prompt shown before choosing preferred courts."""

    t('botapp.ui.queue.format_court_selection_prompt')
    tr = _resolve_translator(translator, language)
    lines = [
        f"⏰ {_bold(tr.t('queue.booking_title'))}",
        "",
        f"{tr.t('notif.date')}: {_md(selected_date.strftime('%A, %B %d, %Y'))}",
        f"{tr.t('notif.time')}: {_md(selected_time)}",
        "",
        _md(tr.t('queue.select_court_prompt')),
    ]
    return "\n".join(lines)
