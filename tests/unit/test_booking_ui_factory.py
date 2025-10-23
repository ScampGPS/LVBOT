from botapp.handlers.booking.ui_factory import BookingUIFactory
from botapp.ui.telegram_ui import TelegramUI


def test_booking_type_selection_view_contains_expected_text():
    factory = BookingUIFactory()
    view = factory.booking_type_selection()

    assert "🎾 Reserve Court" in view.text
    assert view.reply_markup is not None


def test_performance_menu_returns_back_keyboard(monkeypatch):
    monkeypatch.setattr(TelegramUI, "create_back_to_menu_keyboard", lambda: "keyboard")
    factory = BookingUIFactory()

    view = factory.performance_menu()

    assert "📊 Performance" in view.text
    assert view.reply_markup == "keyboard"


def test_admin_reservations_menu_builds_default_keyboard():
    factory = BookingUIFactory()

    view = factory.admin_reservations_menu()

    assert "Admin Reservations Menu" in view.text
    # InlineKeyboardMarkup stores rows in .inline_keyboard attribute
    buttons = view.reply_markup.inline_keyboard
    assert buttons[0][0].callback_data == 'admin_view_my_reservations'
