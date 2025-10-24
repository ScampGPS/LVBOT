"""Shared mixins for handler utilities."""

from __future__ import annotations
from tracking import t

from botapp.messages.message_handlers import MessageHandlers


class CallbackResponseMixin:
    """Provides helper callbacks for answering and editing Telegram messages."""

    async def _safe_answer_callback(self, query, text: str | None = None) -> None:
        t("botapp.handlers.mixins.CallbackResponseMixin._safe_answer_callback")
        try:
            if text:
                await query.answer(text)
            else:
                await query.answer()
        except Exception as exc:
            self.logger.warning("Failed to answer callback query: %s", exc)

    async def _edit_callback_message(self, query, text: str, **kwargs) -> None:
        t("botapp.handlers.mixins.CallbackResponseMixin._edit_callback_message")
        await MessageHandlers.edit_callback_message(
            query,
            text,
            logger=self.logger,
            **kwargs,
        )


__all__ = ["CallbackResponseMixin"]
