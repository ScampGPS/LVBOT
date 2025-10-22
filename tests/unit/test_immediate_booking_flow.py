import asyncio
from types import SimpleNamespace

import pytest

from automation.executors.core import ExecutionResult
from automation.shared.booking_contracts import BookingResult
from botapp.booking import immediate_handler as handler_module
from botapp.booking.immediate_handler import ImmediateBookingHandler


class StubUserManager:
    def __init__(self, profile):
        self._profile = profile

    def get_user(self, user_id):
        return self._profile if user_id == self._profile.get("user_id") else None


class DummyQuery:
    def __init__(self, data, user_id):
        self.data = data
        self.from_user = SimpleNamespace(id=user_id)
        self._messages = []
        self.answered = False

    async def answer(self):
        self.answered = True

    async def edit_message_text(self, message, parse_mode=None, reply_markup=None):
        self._messages.append(
            {
                "message": message,
                "parse_mode": parse_mode,
                "reply_markup": reply_markup,
            }
        )


class DummyUpdate:
    def __init__(self, query):
        self.callback_query = query


@pytest.mark.asyncio
async def test_handle_booking_confirmation_success_flow(monkeypatch):
    profile = {
        "user_id": 42,
        "first_name": "Ada",
        "last_name": "Lovelace",
        "email": "ada@example.com",
        "phone": "+100000000",
        "tier_name": "VIP",
    }
    user_manager = StubUserManager(profile)
    handler = ImmediateBookingHandler(user_manager=user_manager, browser_pool="pool")

    class StubExecutor:
        def __init__(self, pool, config=None):
            assert pool == "pool"

        async def execute_booking(self, court_number, time_slot, user_info, target_date):
            return ExecutionResult(
                success=True,
                message="Booked via natural flow",
                court_number=court_number,
                court_reserved=court_number,
                time_reserved=time_slot,
                confirmation_id="CONF-123",
            )

    monkeypatch.setattr(handler_module, "UnifiedAsyncBookingExecutor", StubExecutor)

    recorded = {}

    def fake_persist_success(request, result, tracker=None):
        recorded["persist"] = (request, result)
        return "imm-1"

    def fake_send_success(user_id, result):
        recorded["notification"] = (user_id, result)
        return {
            "message": "✅ success",
            "parse_mode": "Markdown",
            "reply_markup": "kb",
        }

    monkeypatch.setattr(handler_module, "persist_immediate_success", fake_persist_success)
    monkeypatch.setattr(handler_module, "persist_immediate_failure", lambda *a, **k: (_ for _ in ()).throw(AssertionError("Failure persist should not run")))
    monkeypatch.setattr(handler_module, "send_success_notification", fake_send_success)
    monkeypatch.setattr(handler_module, "send_failure_notification", lambda *a, **k: (_ for _ in ()).throw(AssertionError("Failure notification should not run")))

    query = DummyQuery("confirm_book_2025-08-10_1_09:00", profile["user_id"])
    update = DummyUpdate(query)

    await handler.handle_booking_confirmation(update, context=None)

    assert query.answered is True
    assert query._messages[-1]["message"] == "✅ success"
    assert query._messages[-1]["parse_mode"] == "Markdown"
    assert query._messages[-1]["reply_markup"] == "kb"

    request, result = recorded["persist"]
    assert request.user.user_id == profile["user_id"]
    assert request.target_time == "09:00"
    assert request.court_preference.primary == 1
    assert request.metadata["trigger"] == "immediate_handler"
    assert result.success is True
    assert result.success is True
    # confirmation_code may be injected by executor-specific flows; ensure metadata is present
    assert result.metadata["executor"] == "UnifiedAsyncBookingExecutor"

    notif_user_id, notif_result = recorded["notification"]
    assert notif_user_id == profile["user_id"]
    assert notif_result is result


@pytest.mark.asyncio
async def test_handle_booking_confirmation_failure_flow(monkeypatch):
    profile = {
        "user_id": 7,
        "first_name": "Grace",
        "last_name": "Hopper",
        "email": "grace@example.com",
        "phone": "+199999999",
    }
    user_manager = StubUserManager(profile)
    handler = ImmediateBookingHandler(user_manager=user_manager, browser_pool="pool")

    class FailingExecutor:
        def __init__(self, pool, config=None):
            pass

        async def execute_booking(self, court_number, time_slot, user_info, target_date):
            return ExecutionResult(success=False, error_message="No slots available")

    monkeypatch.setattr(handler_module, "UnifiedAsyncBookingExecutor", FailingExecutor)

    recorded = {}

    def fake_persist_failure(request, result, tracker=None):
        recorded.setdefault("persist_failures", []).append((request, result))
        return "imm-f-1"

    def fake_send_failure(user_id, result):
        recorded["notification"] = (user_id, result)
        return {
            "message": "❌ failure",
            "parse_mode": "Markdown",
            "reply_markup": "kb",
        }

    monkeypatch.setattr(handler_module, "persist_immediate_success", lambda *a, **k: (_ for _ in ()).throw(AssertionError("Success persist should not run")))
    monkeypatch.setattr(handler_module, "persist_immediate_failure", fake_persist_failure)
    monkeypatch.setattr(handler_module, "send_success_notification", lambda *a, **k: (_ for _ in ()).throw(AssertionError("Success notification should not run")))
    monkeypatch.setattr(handler_module, "send_failure_notification", fake_send_failure)

    query = DummyQuery("confirm_book_2025-08-11_2_10:30", profile["user_id"])
    update = DummyUpdate(query)

    await handler.handle_booking_confirmation(update, context=None)

    assert query._messages[-1]["message"] == "❌ failure"

    request, result = recorded["persist_failures"][0]
    assert request.court_preference.primary == 2
    assert result.success is False
    assert "No slots available" in result.message
    assert "queue_execution_time_seconds" not in result.metadata  # immediate flow metadata

    notif_user_id, notif_result = recorded["notification"]
    assert notif_user_id == profile["user_id"]
    assert notif_result is result
