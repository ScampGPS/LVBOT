import types
import pytest

from botapp.handlers.dependencies import CallbackDependencies
from botapp.handlers.queue.handler import QueueHandler


class DummyContext:
    def __init__(self):
        self.user_data = {}


class DummyQuery:
    def __init__(self, data="noop", user_id=1):
        self.data = data
        self.from_user = types.SimpleNamespace(id=user_id)

    async def answer(self, text=None):
        return text


class DummyUpdate:
    def __init__(self, data="noop", user_id=1):
        self.callback_query = DummyQuery(data, user_id)


class FailingQuery(DummyQuery):
    async def answer(self, text=None):
        raise RuntimeError("boom")


class CallRecorder:
    def __init__(self):
        self.calls = []

    def record_async(self, name):
        async def _call(*args, **kwargs):
            self.calls.append((name, args, kwargs))
        return _call

    def record_sync(self, name):
        def _call(*args, **kwargs):
            self.calls.append((name, args, kwargs))
        return _call


@pytest.fixture
def handler_with_spies(monkeypatch):
    deps = CallbackDependencies(
        logger=types.SimpleNamespace(warning=lambda *a, **k: None, error=lambda *a, **k: None, info=lambda *a, **k: None),
        availability_checker=None,
        reservation_queue=types.SimpleNamespace(),
        user_manager=types.SimpleNamespace(is_admin=lambda _uid: False),
        browser_pool=None,
        booking_handler=None,
        reservation_tracker=None,
    )

    handler = QueueHandler(deps)

    booking_recorder = CallRecorder()
    reservation_recorder = CallRecorder()

    handler.booking_flow = types.SimpleNamespace(
        show_menu=booking_recorder.record_async("show_menu"),
        select_date=booking_recorder.record_async("select_date"),
        select_time=booking_recorder.record_async("select_time"),
        select_courts=booking_recorder.record_async("select_courts"),
        confirm=booking_recorder.record_async("confirm"),
        cancel=booking_recorder.record_async("cancel"),
        handle_blocked_date=booking_recorder.record_async("handle_blocked_date"),
        back_to_courts=booking_recorder.record_async("back_to_courts"),
        _show_time_selection=booking_recorder.record_async("_show_time_selection"),
        clear_state=booking_recorder.record_sync("clear_state"),
    )

    handler.reservation_manager = types.SimpleNamespace(
        show_user_menu=reservation_recorder.record_async("show_user_menu"),
        manage_reservation=reservation_recorder.record_async("manage_reservation"),
        manage_queue_reservation=reservation_recorder.record_async("manage_queue_reservation"),
        handle_action=reservation_recorder.record_async("handle_action"),
        cancel_reservation=reservation_recorder.record_async("cancel_reservation"),
        modify_reservation=reservation_recorder.record_async("modify_reservation"),
        share_reservation=reservation_recorder.record_async("share_reservation"),
        modify_option=reservation_recorder.record_async("modify_option"),
        time_modification=reservation_recorder.record_async("time_modification"),
        display_user_reservations=reservation_recorder.record_async("display_user_reservations"),
        display_all_reservations=reservation_recorder.record_async("display_all_reservations"),
    )

    return handler, booking_recorder, reservation_recorder


@pytest.mark.asyncio
async def test_booking_handler_delegation(handler_with_spies):
    handler, booking_recorder, _ = handler_with_spies
    update = DummyUpdate()
    context = DummyContext()

    await handler.handle_queue_booking_menu(update, context)
    await handler.handle_queue_booking_date_selection(update, context)
    await handler.handle_queue_booking_time_selection(update, context)
    await handler.handle_queue_booking_court_selection(update, context)
    await handler.handle_queue_booking_confirm(update, context)
    await handler.handle_queue_booking_cancel(update, context)
    await handler.handle_blocked_date_selection(update, context)
    await handler.handle_back_to_queue_courts(update, context)
    handler.clear_queue_booking_state(context)
    await handler._show_queue_time_selection(update, context, None)  # type: ignore[arg-type]

    called = {name for name, _, _ in booking_recorder.calls}
    expected = {
        "show_menu",
        "select_date",
        "select_time",
        "select_courts",
        "confirm",
        "cancel",
        "handle_blocked_date",
        "back_to_courts",
        "clear_state",
        "_show_time_selection",
    }
    assert expected.issubset(called)


@pytest.mark.asyncio
async def test_reservation_manager_delegation(handler_with_spies):
    handler, _, reservation_recorder = handler_with_spies
    update = DummyUpdate()
    context = DummyContext()

    await handler.handle_my_reservations_menu(update, context)
    await handler.handle_manage_reservation(update, context)
    await handler.handle_manage_queue_reservation(update, context)
    await handler.handle_reservation_action(update, context)
    await handler.handle_cancel_reservation(update, context, "res-1")
    await handler.handle_modify_reservation(update, context, "res-2")
    await handler.handle_share_reservation(update, context, "res-3")
    await handler.handle_modify_option(update, context)
    await handler.handle_time_modification(update, context)
    await handler._display_user_reservations(update, context, 1)
    await handler._display_all_reservations(update.callback_query, [])

    called = {name for name, _, _ in reservation_recorder.calls}
    expected = {
        "show_user_menu",
        "manage_reservation",
        "manage_queue_reservation",
        "handle_action",
        "cancel_reservation",
        "modify_reservation",
        "share_reservation",
        "modify_option",
        "time_modification",
        "display_user_reservations",
        "display_all_reservations",
    }
    assert expected.issubset(called)


@pytest.mark.asyncio
async def test_safe_answer_callback_branches(handler_with_spies):
    handler, _, _ = handler_with_spies

    query = DummyQuery()
    await handler._safe_answer_callback(query, "text")
    await handler._safe_answer_callback(query)

    failing_query = FailingQuery()
    await handler._safe_answer_callback(failing_query)
