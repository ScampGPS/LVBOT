"""
Comprehensive test for all menu buttons to ensure they work and don't raise errors.
Tests all callback routes registered in the bot.
"""
from tracking import t

import pytest
import pytest_asyncio
from unittest.mock import AsyncMock, Mock, patch, MagicMock
from telegram import Update, CallbackQuery, User, Message, Chat
from telegram.ext import ContextTypes

from botapp.runtime.bot_application import BotApplication
from botapp.config import load_bot_config


@pytest_asyncio.fixture
async def bot_app():
    """Create a BotApplication instance for testing."""
    t('tests.bot.test_all_menu_buttons.bot_app')
    config = load_bot_config()
    app = BotApplication(config)
    yield app
    # Cleanup
    if app.browser_pool:
        await app.browser_pool.stop()


@pytest.fixture
def mock_update():
    """Create a mock Telegram Update with CallbackQuery."""
    t('tests.bot.test_all_menu_buttons.mock_update')
    update = Mock(spec=Update)
    update.effective_user = Mock(spec=User)
    update.effective_user.id = 125763357  # Admin user
    update.effective_user.first_name = "Test"
    update.effective_user.last_name = "User"

    # Create mock callback query
    callback_query = Mock(spec=CallbackQuery)
    callback_query.from_user = update.effective_user
    callback_query.answer = AsyncMock()
    callback_query.edit_message_text = AsyncMock()
    callback_query.message = Mock(spec=Message)
    callback_query.message.chat = Mock(spec=Chat)
    callback_query.message.chat.id = 125763357

    update.callback_query = callback_query
    return update


@pytest.fixture
def mock_context():
    """Create a mock Context."""
    t('tests.bot.test_all_menu_buttons.mock_context')
    context = Mock(spec=ContextTypes.DEFAULT_TYPE)
    context.user_data = {}
    context.bot_data = {}
    context.chat_data = {}
    return context


class TestAllMenuButtons:
    """Test all menu button callbacks."""

    @pytest.mark.asyncio
    async def test_menu_reserve(self, bot_app, mock_update, mock_context):
        """Test Reserve Court menu button."""
        t('tests.bot.test_all_menu_buttons.TestAllMenuButtons.test_menu_reserve')
        mock_update.callback_query.data = 'menu_reserve'
        try:
            await bot_app.callback_handler.handle_callback(mock_update, mock_context)
            assert mock_update.callback_query.answer.called
        except Exception as e:
            pytest.fail(f"menu_reserve failed: {str(e)}")

    @pytest.mark.asyncio
    async def test_menu_queued(self, bot_app, mock_update, mock_context):
        """Test Queued Reservations menu button."""
        t('tests.bot.test_all_menu_buttons.TestAllMenuButtons.test_menu_queued')
        mock_update.callback_query.data = 'menu_queued'
        try:
            await bot_app.callback_handler.handle_callback(mock_update, mock_context)
            assert mock_update.callback_query.answer.called
        except Exception as e:
            pytest.fail(f"menu_queued failed: {str(e)}")

    @pytest.mark.asyncio
    async def test_menu_reservations(self, bot_app, mock_update, mock_context):
        """Test Reservations menu button."""
        t('tests.bot.test_all_menu_buttons.TestAllMenuButtons.test_menu_reservations')
        mock_update.callback_query.data = 'menu_reservations'
        try:
            await bot_app.callback_handler.handle_callback(mock_update, mock_context)
            assert mock_update.callback_query.answer.called
        except Exception as e:
            pytest.fail(f"menu_reservations failed: {str(e)}")

    @pytest.mark.asyncio
    async def test_menu_profile(self, bot_app, mock_update, mock_context):
        """Test Profile menu button."""
        t('tests.bot.test_all_menu_buttons.TestAllMenuButtons.test_menu_profile')
        mock_update.callback_query.data = 'menu_profile'
        try:
            await bot_app.callback_handler.handle_callback(mock_update, mock_context)
            assert mock_update.callback_query.answer.called
        except Exception as e:
            pytest.fail(f"menu_profile failed: {str(e)}")

    @pytest.mark.asyncio
    async def test_menu_admin(self, bot_app, mock_update, mock_context):
        """Test Admin Panel menu button."""
        t('tests.bot.test_all_menu_buttons.TestAllMenuButtons.test_menu_admin')
        mock_update.callback_query.data = 'menu_admin'
        try:
            await bot_app.callback_handler.handle_callback(mock_update, mock_context)
            assert mock_update.callback_query.answer.called
        except Exception as e:
            pytest.fail(f"menu_admin failed: {str(e)}")

    @pytest.mark.asyncio
    async def test_back_to_menu(self, bot_app, mock_update, mock_context):
        """Test Back to Menu button."""
        t('tests.bot.test_all_menu_buttons.TestAllMenuButtons.test_back_to_menu')
        mock_update.callback_query.data = 'back_to_menu'
        try:
            await bot_app.callback_handler.handle_callback(mock_update, mock_context)
            assert mock_update.callback_query.answer.called
        except Exception as e:
            pytest.fail(f"back_to_menu failed: {str(e)}")

    @pytest.mark.asyncio
    async def test_edit_profile(self, bot_app, mock_update, mock_context):
        """Test Edit Profile button."""
        t('tests.bot.test_all_menu_buttons.TestAllMenuButtons.test_edit_profile')
        mock_update.callback_query.data = 'edit_profile'
        try:
            await bot_app.callback_handler.handle_callback(mock_update, mock_context)
            assert mock_update.callback_query.answer.called
        except Exception as e:
            pytest.fail(f"edit_profile failed: {str(e)}")

    @pytest.mark.asyncio
    async def test_edit_language(self, bot_app, mock_update, mock_context):
        """Test Change Language button."""
        t('tests.bot.test_all_menu_buttons.TestAllMenuButtons.test_edit_language')
        mock_update.callback_query.data = 'edit_language'
        try:
            await bot_app.callback_handler.handle_callback(mock_update, mock_context)
            assert mock_update.callback_query.answer.called
        except Exception as e:
            pytest.fail(f"edit_language failed: {str(e)}")

    @pytest.mark.asyncio
    async def test_lang_es(self, bot_app, mock_update, mock_context):
        """Test Spanish language selection."""
        t('tests.bot.test_all_menu_buttons.TestAllMenuButtons.test_lang_es')
        mock_update.callback_query.data = 'lang_es'
        try:
            await bot_app.callback_handler.handle_callback(mock_update, mock_context)
            assert mock_update.callback_query.answer.called
        except Exception as e:
            pytest.fail(f"lang_es failed: {str(e)}")

    @pytest.mark.asyncio
    async def test_lang_en(self, bot_app, mock_update, mock_context):
        """Test English language selection."""
        t('tests.bot.test_all_menu_buttons.TestAllMenuButtons.test_lang_en')
        mock_update.callback_query.data = 'lang_en'
        try:
            await bot_app.callback_handler.handle_callback(mock_update, mock_context)
            assert mock_update.callback_query.answer.called
        except Exception as e:
            pytest.fail(f"lang_en failed: {str(e)}")

    @pytest.mark.asyncio
    async def test_admin_toggle_test_mode(self, bot_app, mock_update, mock_context):
        """Test Admin Toggle Test Mode button."""
        t('tests.bot.test_all_menu_buttons.TestAllMenuButtons.test_admin_toggle_test_mode')
        mock_update.callback_query.data = 'admin_toggle_test_mode'
        try:
            await bot_app.callback_handler.handle_callback(mock_update, mock_context)
            assert mock_update.callback_query.answer.called
        except Exception as e:
            pytest.fail(f"admin_toggle_test_mode failed: {str(e)}")

    @pytest.mark.asyncio
    async def test_admin_view_my_reservations(self, bot_app, mock_update, mock_context):
        """Test Admin View My Reservations button."""
        t('tests.bot.test_all_menu_buttons.TestAllMenuButtons.test_admin_view_my_reservations')
        mock_update.callback_query.data = 'admin_view_my_reservations'
        try:
            await bot_app.callback_handler.handle_callback(mock_update, mock_context)
            assert mock_update.callback_query.answer.called
        except Exception as e:
            pytest.fail(f"admin_view_my_reservations failed: {str(e)}")

    @pytest.mark.asyncio
    async def test_admin_view_users_list(self, bot_app, mock_update, mock_context):
        """Test Admin View Users List button."""
        t('tests.bot.test_all_menu_buttons.TestAllMenuButtons.test_admin_view_users_list')
        mock_update.callback_query.data = 'admin_view_users_list'
        try:
            await bot_app.callback_handler.handle_callback(mock_update, mock_context)
            assert mock_update.callback_query.answer.called
        except Exception as e:
            pytest.fail(f"admin_view_users_list failed: {str(e)}")

    @pytest.mark.asyncio
    async def test_admin_view_all_reservations(self, bot_app, mock_update, mock_context):
        """Test Admin View All Reservations button."""
        t('tests.bot.test_all_menu_buttons.TestAllMenuButtons.test_admin_view_all_reservations')
        mock_update.callback_query.data = 'admin_view_all_reservations'
        try:
            await bot_app.callback_handler.handle_callback(mock_update, mock_context)
            assert mock_update.callback_query.answer.called
        except Exception as e:
            pytest.fail(f"admin_view_all_reservations failed: {str(e)}")

    @pytest.mark.asyncio
    async def test_reserve_48h_immediate(self, bot_app, mock_update, mock_context):
        """Test Reserve within 48h button."""
        t('tests.bot.test_all_menu_buttons.TestAllMenuButtons.test_reserve_48h_immediate')
        mock_update.callback_query.data = 'reserve_48h_immediate'
        try:
            await bot_app.callback_handler.handle_callback(mock_update, mock_context)
            assert mock_update.callback_query.answer.called
        except Exception as e:
            pytest.fail(f"reserve_48h_immediate failed: {str(e)}")

    @pytest.mark.asyncio
    async def test_reserve_48h_future(self, bot_app, mock_update, mock_context):
        """Test Reserve after 48h button."""
        t('tests.bot.test_all_menu_buttons.TestAllMenuButtons.test_reserve_48h_future')
        mock_update.callback_query.data = 'reserve_48h_future'
        try:
            await bot_app.callback_handler.handle_callback(mock_update, mock_context)
            assert mock_update.callback_query.answer.called
        except Exception as e:
            pytest.fail(f"reserve_48h_future failed: {str(e)}")
