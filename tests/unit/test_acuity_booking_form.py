import asyncio

import pytest

from automation.forms import acuity_booking_form as acuity_module


class FakeLogger:
    def __init__(self):
        self.messages = []

    def info(self, *args, **kwargs):
        self.messages.append(("info", args))

    def warning(self, *args, **kwargs):
        self.messages.append(("warning", args))

    def error(self, *args, **kwargs):
        self.messages.append(("error", args))


@pytest.fixture(autouse=True)
def no_sleep(monkeypatch):
    async def _no_sleep(_duration):
        return None

    monkeypatch.setattr(asyncio, "sleep", _no_sleep)


@pytest.mark.asyncio
async def test_fill_booking_form_delegates_to_service(monkeypatch):
    created = []

    class DummyService:
        def __init__(self, **kwargs):
            self.kwargs = kwargs
            self.logger = FakeLogger()
            created.append(self)

        async def fill_and_submit(self, page, user_data):
            self.called_with = (page, user_data)
            return True, "ok"

    monkeypatch.setattr(acuity_module, "AcuityFormService", DummyService)

    page = object()
    result = await acuity_module.fill_booking_form(page, {"client.firstName": "Ana"})

    assert result == (True, "ok")
    assert created
    assert created[0].called_with[0] is page
    assert created[0].kwargs['use_javascript'] is True


@pytest.mark.asyncio
async def test_fill_form_delegates_and_logs(monkeypatch):
    created = []

    class DummyService:
        def __init__(self, **kwargs):
            self.kwargs = kwargs
            self.logger = FakeLogger()
            created.append(self)

        def map_user_info(self, user_info):
            self.mapped = user_info
            return {
                'client.firstName': user_info.get('first_name', ''),
            }

        async def fill_form(self, page, user_data):
            self.fill_args = (page, user_data)
            return 1

        async def check_validation(self, page):
            self.check_called = True
            return False, ()

    monkeypatch.setattr(acuity_module, "AcuityFormService", DummyService)

    page = object()
    user_info = {'first_name': 'Ana'}
    result = await acuity_module.fill_form(page, user_info)

    assert result is True
    service = created[0]
    assert service.mapped is user_info
    assert service.fill_args[0] is page
    assert service.check_called
    assert service.logger.messages[-1][0] == "info"


@pytest.mark.asyncio
async def test_acuity_booking_form_uses_injected_service():
    class DummyService:
        def __init__(self):
            self.logger = FakeLogger()

        async def fill_and_submit(self, page, user_data):
            self.called = (page, user_data)
            return True, "done"

        def map_user_info(self, user_info):
            self.mapped = user_info
            return {'client.firstName': 'Ana'}

        async def fill_form(self, page, user_data):
            self.fill_called = (page, user_data)
            return 1

        async def check_validation(self, page):
            self.validation_called = True
            return False, ()

        async def submit(self, page):
            self.submit_called = True
            return True

        async def check_success(self, page):
            self.success_called = True
            return True, "done"

    service = DummyService()
    form = acuity_module.AcuityBookingForm(service=service)

    result = await form.fill_booking_form("page", {'client.firstName': 'Ana'})
    assert result == (True, "done")
    assert service.called[0] == "page"

    form_result = await form.fill_form("page", {'first_name': 'Ana'})
    assert form_result is True
    assert service.fill_called[0] == "page"
    assert service.validation_called

    validation = await form.check_form_validation_errors("page")
    assert validation == (False, [])

    submit = await form._submit_form_simple("page")
    assert submit is True
    assert service.submit_called

    success = await form.check_booking_success("page")
    assert success == (True, "done")
    assert service.success_called
