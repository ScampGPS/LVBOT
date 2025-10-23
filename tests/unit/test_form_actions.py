import asyncio

import pytest

from automation.forms.actions import (
    map_user_info,
    validate_required_fields,
    check_booking_success,
)
from automation.shared.booking_contracts import BookingUser


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
    assert map_user_info(info) == expected


def test_validate_required_fields_returns_missing():
    missing = validate_required_fields({'client.firstName': 'Ana'})
    assert 'client.lastName' in missing
    assert 'client.phone' in missing
    assert 'client.email' in missing


class DummyLogger:
    def __init__(self):
        self.messages = []

    def info(self, *args, **kwargs):
        self.messages.append(("info", args))

    def warning(self, *args, **kwargs):
        self.messages.append(("warning", args))

    def error(self, *args, **kwargs):
        self.messages.append(("error", args))


class DummyPage:
    def __init__(self, result):
        self._result = result

    async def evaluate(self, script):  # pragma: no cover - simple stub
        return self._result


@pytest.mark.asyncio
async def test_check_booking_success_handles_success():
    page = DummyPage({
        'success': True,
        'message': 'Reserva confirmada',
    })
    logger = DummyLogger()
    success, message = await check_booking_success(page, logger=logger)
    assert success
    assert message == 'Reserva confirmada'


@pytest.mark.asyncio
async def test_check_booking_success_handles_failure():
    page = DummyPage({
        'success': False,
        'error': 'validation_error',
        'message': 'Errores de validación: email',
    })
    logger = DummyLogger()
    success, message = await check_booking_success(page, logger=logger)
    assert not success
    assert 'Errores de validación' in message
