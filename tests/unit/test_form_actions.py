from tracking import t
import asyncio

import pytest

from automation.forms.actions import AcuityFormService
from automation.shared.booking_contracts import BookingUser
from tests.helpers import DummyLogger


@pytest.fixture(autouse=True)
def fast_sleep(monkeypatch):
    t('tests.unit.test_form_actions.fast_sleep')
    async def _no_sleep(_duration):
        t('tests.unit.test_form_actions.fast_sleep._no_sleep')
        return None

    monkeypatch.setattr(asyncio, "sleep", _no_sleep)


@pytest.mark.parametrize(
    "info,expected",
    [
        ({"first_name": "Ana", "last_name": "Perez", "phone": "123", "email": "ana@example.com"},
         {
             'client.firstName': 'Ana',
             'client.lastName': 'Perez',
             'client.phone': '123',
             'client.email': 'ana@example.com',
         }),
        ({}, {
            'client.firstName': '',
            'client.lastName': '',
            'client.phone': '',
            'client.email': '',
        }),
        (BookingUser(user_id=5, first_name='Luis', last_name='Lopez', email='luis@example.com', phone='555-0000'), {
            'client.firstName': 'Luis',
            'client.lastName': 'Lopez',
            'client.phone': '555-0000',
            'client.email': 'luis@example.com',
        }),
    ],
)
def test_map_user_info(info, expected):
    t('tests.unit.test_form_actions.test_map_user_info')
    service = AcuityFormService(enable_tracing=False)
    assert service.map_user_info(info) == expected


def test_validate_required_fields_returns_missing():
    t('tests.unit.test_form_actions.test_validate_required_fields_returns_missing')
    service = AcuityFormService(enable_tracing=False)
    missing = service.validate({'client.firstName': 'Ana'})
    assert 'client.lastName' in missing
    assert 'client.phone' in missing
    assert 'client.email' in missing


class DummyTracing:
    async def start(self, *args, **kwargs):  # pragma: no cover - not invoked when tracing disabled
        t('tests.unit.test_form_actions.DummyTracing.start')
        return None

    async def stop(self, *args, **kwargs):  # pragma: no cover - not invoked when tracing disabled
        t('tests.unit.test_form_actions.DummyTracing.stop')
        return None


class DummyContext:
    def __init__(self):
        t('tests.unit.test_form_actions.DummyContext.__init__')
        self.tracing = DummyTracing()


class DummyPage:
    def __init__(self, result):
        t('tests.unit.test_form_actions.DummyPage.__init__')
        if isinstance(result, list):
            self._results = list(result)
            self._single_result = None
        else:
            self._results = None
            self._single_result = result
        self.evaluate_calls = []
        self.context = DummyContext()

    async def evaluate(self, script, *args):  # pragma: no cover - simple stub
        t('tests.unit.test_form_actions.DummyPage.evaluate')
        self.evaluate_calls.append((script, args))
        if self._results is not None:
            if not self._results:
                raise AssertionError("No queued evaluate results remaining")
            return self._results.pop(0)
        return self._single_result


@pytest.mark.asyncio
async def test_check_booking_success_handles_success():
    t('tests.unit.test_form_actions.test_check_booking_success_handles_success')
    page = DummyPage({
        'success': True,
        'message': 'Reserva confirmada',
    })
    logger = DummyLogger()
    service = AcuityFormService(logger=logger, enable_tracing=False)
    success, message = await service.check_success(page)
    assert success
    assert message == 'Reserva confirmada'


@pytest.mark.asyncio
async def test_check_booking_success_handles_failure():
    t('tests.unit.test_form_actions.test_check_booking_success_handles_failure')
    page = DummyPage({
        'success': False,
        'error': 'validation_error',
        'message': 'Errores de validación: email',
    })
    logger = DummyLogger()
    service = AcuityFormService(logger=logger, enable_tracing=False)
    success, message = await service.check_success(page)
    assert not success
    assert 'Errores de validación' in message


@pytest.mark.asyncio
async def test_fill_and_submit_success_path():
    t('tests.unit.test_form_actions.test_fill_and_submit_success_path')
    page = DummyPage([
        {'filled': 4, 'messages': ('ok',)},
        {'hasErrors': False, 'errors': ()},
        {'success': True, 'buttonText': 'Confirmar'},
        {'success': True, 'message': 'Reserva confirmada'},
    ])
    logger = DummyLogger()
    service = AcuityFormService(logger=logger, enable_tracing=False)

    success, message = await service.fill_and_submit(
        page,
        {
            'client.firstName': 'Ana',
            'client.lastName': 'Perez',
            'client.phone': '123',
            'client.email': 'ana@example.com',
        },
    )

    assert success
    assert message == 'Reserva confirmada'
    assert len(page.evaluate_calls) == 4


@pytest.mark.asyncio
async def test_fill_and_submit_validation_failure():
    t('tests.unit.test_form_actions.test_fill_and_submit_validation_failure')
    page = DummyPage([
        {'filled': 4, 'messages': ()},
        {'hasErrors': True, 'errors': ('Email required',)},
    ])
    service = AcuityFormService(logger=DummyLogger(), enable_tracing=False)

    success, message = await service.fill_and_submit(
        page,
        {
            'client.firstName': 'Ana',
            'client.lastName': 'Perez',
            'client.phone': '123',
            'client.email': 'ana@example.com',
        },
    )

    assert not success
    assert 'Form validation failed' in message
    assert len(page.evaluate_calls) == 2


@pytest.mark.asyncio
async def test_fill_and_submit_missing_required_fields_short_circuit():
    t('tests.unit.test_form_actions.test_fill_and_submit_missing_required_fields_short_circuit')
    page = DummyPage([])
    service = AcuityFormService(logger=DummyLogger(), enable_tracing=False)

    success, message = await service.fill_and_submit(
        page,
        {
            'client.firstName': 'Ana',
            'client.lastName': '',
            'client.phone': '',
            'client.email': '',
        },
    )

    assert not success
    assert message.startswith('Missing required fields')
    assert page.evaluate_calls == []


@pytest.mark.asyncio
async def test_fill_and_submit_submit_failure():
    t('tests.unit.test_form_actions.test_fill_and_submit_submit_failure')
    page = DummyPage([
        {'filled': 4, 'messages': ()},
        {'hasErrors': False, 'errors': ()},
        {'success': False, 'error': 'No submit button found'},
    ])
    service = AcuityFormService(logger=DummyLogger(), enable_tracing=False)

    success, message = await service.fill_and_submit(
        page,
        {
            'client.firstName': 'Ana',
            'client.lastName': 'Perez',
            'client.phone': '123',
            'client.email': 'ana@example.com',
        },
    )

    assert not success
    assert message == '❌ Form submission failed'
    assert len(page.evaluate_calls) == 3


@pytest.mark.asyncio
async def test_fill_and_submit_accepts_booking_user():
    t('tests.unit.test_form_actions.test_fill_and_submit_accepts_booking_user')
    booking_user = BookingUser(
        user_id=1,
        first_name='Ana',
        last_name='Perez',
        email='ana@example.com',
        phone='123',
    )
    page = DummyPage([
        {'filled': 4, 'messages': ()},
        {'hasErrors': False, 'errors': ()},
        {'success': True, 'buttonText': 'Confirmar'},
        {'success': True, 'message': 'Reserva confirmada'},
    ])
    service = AcuityFormService(logger=DummyLogger(), enable_tracing=False)

    success, message = await service.fill_and_submit(page, booking_user)

    assert success
    assert message == 'Reserva confirmada'
    filled_payload = page.evaluate_calls[0][1][0]
    assert filled_payload['client.firstName'] == 'Ana'


@pytest.mark.asyncio
async def test_check_validation_handles_exception():
    t('tests.unit.test_form_actions.test_check_validation_handles_exception')
    class RaisingPage(DummyPage):
        async def evaluate(self, script, *args):
            t('tests.unit.test_form_actions.test_check_validation_handles_exception.RaisingPage.evaluate')
            raise RuntimeError('boom')

    page = RaisingPage({})
    service = AcuityFormService(logger=DummyLogger(), enable_tracing=False)

    has_errors, errors = await service.check_validation(page)

    assert has_errors
    assert errors and 'boom' in errors[0]


@pytest.mark.asyncio
async def test_fill_form_uses_playwright_strategy(monkeypatch):
    t('tests.unit.test_form_actions.test_fill_form_uses_playwright_strategy')
    service = AcuityFormService(logger=DummyLogger(), use_javascript=False, enable_tracing=False)

    async def fake_playwright(page, payload):
        t('tests.unit.test_form_actions.test_fill_form_uses_playwright_strategy.fake_playwright')
        return 3

    monkeypatch.setattr(service, '_fill_via_playwright', fake_playwright)

    result = await service.fill_form(DummyPage({}), {'client.firstName': 'Ana'})

    assert result == 3
