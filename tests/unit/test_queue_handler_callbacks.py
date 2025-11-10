from tracking import t
import types
import pytest

from botapp.handlers.dependencies import CallbackDependencies
from botapp.handlers.queue.handler import QueueHandler
from botapp.handlers.queue.session import QueueSessionStore
from botapp.handlers.state import get_session_state
from reservations.models import ReservationRequest


class DummyReservationQueue:
    def __init__(self, duplicate=False):
        t('tests.unit.test_queue_handler_callbacks.DummyReservationQueue.__init__')
        self.duplicate = duplicate
        self.added_requests = []

    def add_reservation_request(self, request):
        t('tests.unit.test_queue_handler_callbacks.DummyReservationQueue.add_reservation_request')
        self.added_requests.append(request)
        if self.duplicate:
            raise ValueError("duplicate")
        return "new-res-id"

    def get_user_reservations(self, user_id):
        t('tests.unit.test_queue_handler_callbacks.DummyReservationQueue.get_user_reservations')
        return []

    def get_pending_reservations(self):
        t('tests.unit.test_queue_handler_callbacks.DummyReservationQueue.get_pending_reservations')
        return []

    def get_reservation(self, reservation_id):
        t('tests.unit.test_queue_handler_callbacks.DummyReservationQueue.get_reservation')
        return {
            "id": reservation_id,
            "target_date": "2025-10-23",
            "target_time": "13:00",
            "court_preferences": [1, 2],
            "status": "pending",
            "created_at": "2025-10-21T10:00:00",
        }

    def remove_reservation(self, reservation_id):
        t('tests.unit.test_queue_handler_callbacks.DummyReservationQueue.remove_reservation')
        return True

    def update_reservation(self, reservation_id, reservation):
        t('tests.unit.test_queue_handler_callbacks.DummyReservationQueue.update_reservation')
        return reservation


class DummyBookingHandler:
    async def handle_booking_request(self, *args, **kwargs):
        t('tests.unit.test_queue_handler_callbacks.DummyBookingHandler.handle_booking_request')
        raise NotImplementedError

    async def handle_booking_confirmation(self, *args, **kwargs):
        t('tests.unit.test_queue_handler_callbacks.DummyBookingHandler.handle_booking_confirmation')
        raise NotImplementedError

    async def handle_booking_cancellation(self, *args, **kwargs):
        t('tests.unit.test_queue_handler_callbacks.DummyBookingHandler.handle_booking_cancellation')
        raise NotImplementedError


class DummyTracker:
    def get_user_active_reservations(self, user_id):
        t('tests.unit.test_queue_handler_callbacks.DummyTracker.get_user_active_reservations')
        return []


class DummyQuery:
    def __init__(self, data, user_id=1):
        t('tests.unit.test_queue_handler_callbacks.DummyQuery.__init__')
        self.data = data
        self.from_user = types.SimpleNamespace(id=user_id)
        self.edits = []
        self.answered = None

    async def answer(self, text=None):
        t('tests.unit.test_queue_handler_callbacks.DummyQuery.answer')
        self.answered = text

    async def edit_message_text(self, text, **kwargs):
        t('tests.unit.test_queue_handler_callbacks.DummyQuery.edit_message_text')
        self.edits.append((text, kwargs))


class DummyContext:
    def __init__(self):
        t('tests.unit.test_queue_handler_callbacks.DummyContext.__init__')
        self.user_data = {}


class DummyUpdate:
    def __init__(self, data, user_id=1):
        t('tests.unit.test_queue_handler_callbacks.DummyUpdate.__init__')
        self.callback_query = DummyQuery(data, user_id)


@pytest.fixture
def deps(monkeypatch):
    t('tests.unit.test_queue_handler_callbacks.deps')
    deps = CallbackDependencies(
        logger=types.SimpleNamespace(warning=lambda *a, **k: None, error=lambda *a, **k: None, info=lambda *a, **k: None),
        availability_checker=object(),
        reservation_queue=DummyReservationQueue(),
        user_manager=types.SimpleNamespace(is_admin=lambda _uid: False, get_user=lambda _uid: {"first_name": "Test", "last_name": "User", "email": "t@example.com"}, get_user_tier=lambda _uid: types.SimpleNamespace(name="REGULAR")),
        browser_pool=None,
        booking_handler=DummyBookingHandler(),
        reservation_tracker=DummyTracker(),
    )

    monkeypatch.setattr('botapp.handlers.queue.handler.TelegramUI.create_back_to_menu_keyboard', lambda: 'back-keyboard')
    monkeypatch.setattr('botapp.handlers.queue.handler.format_queue_reservation_added', lambda summary, reservation_id, test_mode_config=None: f"added:{reservation_id}")
    monkeypatch.setattr('botapp.handlers.queue.handler.format_duplicate_reservation_message', lambda msg: f"dup:{msg}")
    return deps


@pytest.mark.asyncio
async def test_queue_confirm_success_clears_state(deps):
    t('tests.unit.test_queue_handler_callbacks.test_queue_confirm_success_clears_state')
    handler = QueueHandler(deps)
    context = DummyContext()
    # prepopulate state as booking flow would
    store = QueueSessionStore(context)
    store.summary = {
        'user_id': 1,
        'first_name': 'Test',
        'last_name': 'User',
        'email': 't@example.com',
        'phone': '555-0100',
        'tier': None,
        'court_preferences': [1, 2],
        'target_date': '2025-10-23',
        'target_time': '13:00',
        'created_at': '2025-10-21T09:00:00',
    }

    update = DummyUpdate('queue_confirm')

    await handler.handle_queue_booking_confirm(update, context)

    assert deps.reservation_queue.added_requests, "Reservation should be enqueued"
    stored_request = deps.reservation_queue.added_requests[0]
    assert isinstance(stored_request, ReservationRequest)
    assert stored_request.court_preferences == [1, 2]
    assert 'queue_booking_summary' not in context.user_data
    # ensure session state cleared
    session = get_session_state(context)
    assert not session.queue.summary
    # confirm UI feedback sent
    assert update.callback_query.edits[-1][0] == 'added:new-res-id'


@pytest.mark.asyncio
async def test_queue_confirm_duplicate_clears_state(monkeypatch, deps):
    t('tests.unit.test_queue_handler_callbacks.test_queue_confirm_duplicate_clears_state')
    deps.reservation_queue = DummyReservationQueue(duplicate=True)
    handler = QueueHandler(deps)
    context = DummyContext()
    store = QueueSessionStore(context)
    store.summary = {
        'user_id': 1,
        'first_name': 'Test',
        'last_name': 'User',
        'email': 't@example.com',
        'phone': '555-0100',
        'tier': None,
        'court_preferences': [1, 2, 3],
        'target_date': '2025-10-23',
        'target_time': '13:00',
        'created_at': '2025-10-21T09:00:00',
    }

    update = DummyUpdate('queue_confirm')

    await handler.handle_queue_booking_confirm(update, context)

    assert 'queue_booking_summary' not in context.user_data
    assert update.callback_query.edits[-1][0].startswith('dup:')


@pytest.mark.asyncio
async def test_blocked_date_allows_selection_in_test_mode(monkeypatch, deps):
    t('tests.unit.test_queue_handler_callbacks.test_blocked_date_allows_selection_in_test_mode')
    handler = QueueHandler(deps)

    class Config:
        enabled = True
        allow_within_48h = True

    monkeypatch.setattr('botapp.handlers.queue.handler.get_test_mode', lambda: Config)

    captured = []

    async def fake_show(update, context, selected_date):
        t('tests.unit.test_queue_handler_callbacks.test_blocked_date_allows_selection_in_test_mode.fake_show')
        captured.append(selected_date)

    monkeypatch.setattr(handler, '_show_queue_time_selection', fake_show)

    update = DummyUpdate('blocked_date_2025-10-22')
    context = DummyContext()

    await handler.handle_blocked_date_selection(update, context)

    assert captured and captured[0].isoformat() == '2025-10-22'
    assert QueueSessionStore(context).selected_date.isoformat() == '2025-10-22'
    assert context.user_data.get('current_flow') == 'queue_booking'


@pytest.mark.asyncio
async def test_blocked_date_rejected_when_not_allowed(monkeypatch, deps):
    t('tests.unit.test_queue_handler_callbacks.test_blocked_date_rejected_when_not_allowed')
    handler = QueueHandler(deps)

    class Config:
        enabled = False
        allow_within_48h = False

    monkeypatch.setattr('botapp.handlers.queue.handler.get_test_mode', lambda: Config)

    messages = []

    async def fake_edit(query, text, **kwargs):
        t('tests.unit.test_queue_handler_callbacks.test_blocked_date_rejected_when_not_allowed.fake_edit')
        messages.append(text)

    monkeypatch.setattr(handler, '_edit_callback_message', fake_edit)

    update = DummyUpdate('blocked_date_2025-10-22')
    context = DummyContext()

    await handler.handle_blocked_date_selection(update, context)

    assert messages and any('48' in msg for msg in messages)
