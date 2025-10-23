import pytest

from botapp.handlers.queue.messages import QueueMessageFactory
from botapp.handlers.queue.guards import (
    IncompleteProfileError,
    MissingModificationContextError,
    MissingQueueSummaryError,
    ensure_modification,
    ensure_profile_fields,
    ensure_summary,
)
from botapp.handlers.queue import session as queue_session


class DummyContext:
    def __init__(self):
        self.user_data = {}


def test_queue_message_factory_all_methods():
    factory = QueueMessageFactory()
    assert factory.session_expired() == factory.SESSION_EXPIRED
    assert factory.session_expired_retry() == factory.SESSION_EXPIRED_RETRY
    assert factory.invalid_date() == factory.INVALID_DATE

    profile_message = factory.profile_incomplete(["email", "phone"])
    assert "email" in profile_message and "phone" in profile_message

    assert factory.reservation_details_error() == factory.RESERVATION_DETAILS_ERROR
    assert factory.reservation_list_error() == factory.RESERVATION_LIST_ERROR
    assert factory.reservation_cancelled() == factory.RESERVATION_CANCELLED
    assert factory.modification_prompt() == factory.MODIFY_PROMPT
    assert factory.modification_unavailable() == factory.MODIFY_UNAVAILABLE

    time_message = factory.time_updated("09:00")
    assert "09:00" in time_message

    courts_message = factory.courts_updated("Courts 1, 2")
    assert "Courts 1, 2" in courts_message
    default_courts_message = factory.courts_updated()
    assert "updated." in default_courts_message


def test_ensure_summary_success_and_failure():
    context = DummyContext()
    queue_session.set_summary(context, {"value": 1})
    assert ensure_summary(context)["value"] == 1

    context_missing = DummyContext()
    with pytest.raises(MissingQueueSummaryError):
        ensure_summary(context_missing)


def test_ensure_modification_success_and_failure():
    context = DummyContext()
    queue_session.set_modification(context, "res-1", "time")
    modifying_id, option = ensure_modification(context)
    assert modifying_id == "res-1"
    assert option == "time"

    context_missing = DummyContext()
    with pytest.raises(MissingModificationContextError):
        ensure_modification(context_missing)


def test_ensure_profile_fields():
    ensure_profile_fields({"email": "a@b", "phone": "123"}, ["email", "phone"])

    with pytest.raises(IncompleteProfileError) as exc:
        ensure_profile_fields({"email": "a@b"}, ["email", "phone"])
    assert exc.value.missing_fields == ("phone",)

    with pytest.raises(IncompleteProfileError):
        ensure_profile_fields(None, ["email"])
