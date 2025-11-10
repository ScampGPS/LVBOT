"""Playwright-backed regression tests for future date booking flows."""

from __future__ import annotations
from tracking import t

from datetime import date, timedelta
from types import SimpleNamespace
from unittest.mock import AsyncMock, patch

import pytest
from playwright.async_api import async_playwright
from telegram.constants import ParseMode

from botapp.handlers.booking.handler import BookingHandler
from botapp.handlers.dependencies import CallbackDependencies
from infrastructure.settings import TestModeConfig
from tests.bot.harness import BotTestHarness
from tests.bot.fakes import FakeCallbackQuery, FakeContext, FakeUpdate, FakeUser
from tests.helpers import DummyLogger


class _StubReservationQueue:
    """Minimal reservation queue stub for handler dependencies."""

    def get_reservation(self, reservation_id):  # pragma: no cover - behaviour unused here
        t('tests.bot.test_future_date_flow_playwright._StubReservationQueue.get_reservation')
        return None

    def update_reservation(self, reservation_id, payload):  # pragma: no cover - behaviour unused here
        t('tests.bot.test_future_date_flow_playwright._StubReservationQueue.update_reservation')
        return None

    def get_user_reservations(self, user_id):  # pragma: no cover - behaviour unused here
        t('tests.bot.test_future_date_flow_playwright._StubReservationQueue.get_user_reservations')
        return []


class _StubUserManager:
    """Provide the admin check required by the booking handler."""

    def is_admin(self, user_id):
        t('tests.bot.test_future_date_flow_playwright._StubUserManager.is_admin')
        return False


@pytest.mark.asyncio
async def test_future_date_flow_uses_markdown_v2_with_escaped_symbols():
    """Ensure the queue booking flow emits Markdown V2-safe messages.

    The regression that surfaced in production was an unescaped hyphen inside
    the matrix availability message, which Telegram rejected when using
    ``ParseMode.MARKDOWN_V2``. This test drives the handler with fakes and then
    uses Playwright to validate that the emitted text still contains the
    necessary escapes, giving us coverage without launching the full bot.
    """
    t('tests.bot.test_future_date_flow_playwright.test_future_date_flow_uses_markdown_v2_with_escaped_symbols')

    logger = DummyLogger()
    deps = CallbackDependencies(
        logger=logger,
        availability_checker=SimpleNamespace(),
        reservation_queue=_StubReservationQueue(),
        user_manager=_StubUserManager(),
        browser_pool=None,
        booking_handler=None,
        reservation_tracker=None,
    )
    handler = BookingHandler(deps)

    records = []
    user = FakeUser(id=999)
    context = FakeContext()
    context.user_data['current_flow'] = 'queue_booking'

    target_date = date.today() + timedelta(days=1)
    callback_data = f"future_date_{target_date:%Y-%m-%d}"
    query = FakeCallbackQuery(data=callback_data, user=user, records=records)
    update = FakeUpdate(user=user, callback_query=query)

    matrix_payload = {
        target_date.strftime('%Y-%m-%d'): {
            1: ['09:00', '10:00'],
            2: ['11:30'],
        }
    }

    test_mode = TestModeConfig(
        enabled=True,
        allow_within_48h=True,
        trigger_delay_minutes=0.0,
        retain_failed_reservations=False,
    )

    with patch('botapp.handlers.booking.handler.get_test_mode', return_value=test_mode), patch(
        'botapp.handlers.booking.handler.fetch_live_availability_matrix',
        new=AsyncMock(return_value=matrix_payload),
    ):
        await handler.handle_future_date_selection(update, context)

    message_entries = [record for record in records if record['action'] == 'edit_message_text']
    assert message_entries, "Expected the handler to edit the message with availability details"

    message = message_entries[-1]
    assert message['kwargs']['parse_mode'] == ParseMode.MARKDOWN_V2
    rendered_text = message['text']

    # Playwright gives us a lightweight browser context to validate the escape
    # sequence exactly as the client would interpret it.
    async with async_playwright() as playwright:
        browser = await playwright.chromium.launch(headless=True)
        try:
            page = await browser.new_page()
            await page.evaluate(
                """
                (text) => {
                    if (!text.includes('\\-')) {
                        throw new Error('Markdown V2 hyphen was not escaped');
                    }
                }
                """,
                rendered_text,
            )
        finally:
            await browser.close()


@pytest.mark.asyncio
async def test_matrix_selection_skips_additional_court_prompt():
    """Selecting a matrix slot should jump straight to confirmation."""
    t('tests.bot.test_future_date_flow_playwright.test_matrix_selection_skips_additional_court_prompt')

    harness = BotTestHarness()

    target_date = date.today() + timedelta(days=1)
    date_key = target_date.strftime('%Y-%m-%d')
    matrix_payload = {
        date_key: {
            3: ['20:15'],
        }
    }

    test_mode = TestModeConfig(
        enabled=True,
        allow_within_48h=True,
        trigger_delay_minutes=0.0,
        retain_failed_reservations=False,
    )

    try:
        with patch('botapp.handlers.booking.handler.get_test_mode', return_value=test_mode), patch(
            'botapp.handlers.queue.handler.get_test_mode', return_value=test_mode
        ), patch(
            'botapp.handlers.booking.handler.fetch_live_availability_matrix',
            new=AsyncMock(return_value=matrix_payload),
        ):
            await harness.dispatch_callback(f'future_date_{date_key}')
            await harness.dispatch_callback(f'queue_matrix_{date_key}_3_20:15')

        message_entries = [record for record in harness.records if record['action'] == 'edit_message_text']
        assert len(message_entries) >= 2, "Expected both availability and confirmation messages"

        final_message = message_entries[-1]
        assert final_message['kwargs']['parse_mode'] == ParseMode.MARKDOWN_V2
        rendered_text = final_message['text']

        async with async_playwright() as playwright:
            browser = await playwright.chromium.launch(headless=True)
            try:
                page = await browser.new_page()
                await page.evaluate(
                    """
                    (text) => {
                        if (!text.includes('Queue Booking Confirmation')) {
                            throw new Error('Queue confirmation details missing');
                        }
                        if (text.includes('Select your preferred court')) {
                            throw new Error('Court selection prompt should not be shown after matrix selection');
                        }
                    }
                    """,
                    rendered_text,
                )
            finally:
                await browser.close()
    finally:
        harness.close()
