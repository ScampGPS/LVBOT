"""Lightweight stand-ins for Telegram objects used by the bot harness."""

from __future__ import annotations

from dataclasses import dataclass
from typing import Any, Dict, List, Optional


@dataclass
class FakeUser:
    """Minimal user representation carrying the identifiers handlers expect."""

    id: int
    first_name: str = "Test"
    last_name: str = "User"
    username: str = "test_user"


class FakeMessage:
    """Collect replies emitted during a scenario."""

    def __init__(self, chat_id: int, records: List[Dict[str, Any]]) -> None:
        self.chat_id = chat_id
        self._records = records

    async def reply_text(self, text: str, **kwargs: Any) -> None:
        self._records.append(
            {
                "action": "reply_text",
                "chat_id": self.chat_id,
                "text": text,
                "kwargs": kwargs,
            }
        )


class FakeCallbackQuery:
    """Simulate the subset of telegram.CallbackQuery used by the handlers."""

    def __init__(
        self,
        *,
        data: str,
        user: FakeUser,
        records: List[Dict[str, Any]],
    ) -> None:
        self.data = data
        self.from_user = user
        self._records = records
        self.message = FakeMessage(chat_id=user.id, records=records)

    async def answer(self, **kwargs: Any) -> None:
        self._records.append(
            {
                "action": "answer",
                "data": self.data,
                "kwargs": kwargs,
            }
        )

    async def edit_message_text(self, text: str, **kwargs: Any) -> None:
        self._records.append(
            {
                "action": "edit_message_text",
                "data": self.data,
                "text": text,
                "kwargs": kwargs,
            }
        )

    async def edit_message_reply_markup(self, reply_markup: Any = None) -> None:
        self._records.append(
            {
                "action": "edit_message_reply_markup",
                "data": self.data,
                "reply_markup": reply_markup,
            }
        )


class FakeUpdate:
    """Simplified telegram.Update analogue for the harness."""

    def __init__(
        self,
        *,
        user: FakeUser,
        message: Optional[FakeMessage] = None,
        callback_query: Optional[FakeCallbackQuery] = None,
    ) -> None:
        self._effective_user = user
        self.message = message
        self.callback_query = callback_query

    @property
    def effective_user(self) -> FakeUser:
        return self._effective_user


class FakeContext:
    """Plain object mirroring the telegram.ext callback context."""

    def __init__(self) -> None:
        self.user_data: Dict[str, Any] = {}
        self.chat_data: Dict[str, Any] = {}
        self.bot_data: Dict[str, Any] = {}
        self.application = None
