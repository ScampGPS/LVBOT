"""Reusable helpers for composing Markdown messages."""

from __future__ import annotations
from tracking import t

from typing import Iterable, List
from telegram.helpers import escape_markdown


def escape_telegram_markdown(text: object, *, escape_special_chars: bool = False) -> str:
    """
    Escape text for Telegram Markdown.

    Args:
        text: Text to escape
        escape_special_chars: If True, escape special characters like hyphens, periods, etc.
                            Required when displaying dates, times with special formatting.
                            Default False uses standard Markdown escaping.

    Returns:
        Escaped markdown string safe for Telegram
    """
    t('botapp.ui.text_blocks.escape_telegram_markdown')
    version = 2 if escape_special_chars else 1
    return escape_markdown(str(text), version=version)


def bold_telegram_text(text: object, *, escape_special_chars: bool = False) -> str:
    """
    Return bold Telegram Markdown text.

    Args:
        text: Text to make bold
        escape_special_chars: If True, escape special characters in the text

    Returns:
        Bold markdown string
    """
    t('botapp.ui.text_blocks.bold_telegram_text')
    return f"*{escape_telegram_markdown(text, escape_special_chars=escape_special_chars)}*"


class MarkdownBlockBuilder:
    """Utility for building Markdown messages with bullet support."""

    __slots__ = ("_lines",)

    def __init__(self) -> None:
        t("botapp.ui.text_blocks.MarkdownBlockBuilder.__init__")
        self._lines: List[str] = []

    def line(self, text: str = "") -> "MarkdownBlockBuilder":
        t('botapp.ui.text_blocks.MarkdownBlockBuilder.line')
        self._lines.append(text)
        return self

    def heading(self, text: str) -> "MarkdownBlockBuilder":
        t('botapp.ui.text_blocks.MarkdownBlockBuilder.heading')
        if text:
            self._lines.append(text)
        return self

    def bullet(self, text: str) -> "MarkdownBlockBuilder":
        t('botapp.ui.text_blocks.MarkdownBlockBuilder.bullet')
        if text:
            self._lines.append(f"• {text}")
        return self

    def bullets(self, items: Iterable[str]) -> "MarkdownBlockBuilder":
        t('botapp.ui.text_blocks.MarkdownBlockBuilder.bullets')
        for item in items:
            if item:
                self._lines.append(f"• {item}")
        return self

    def blank(self) -> "MarkdownBlockBuilder":
        t('botapp.ui.text_blocks.MarkdownBlockBuilder.blank')
        self._lines.append("")
        return self

    def extend(self, lines: Iterable[str]) -> "MarkdownBlockBuilder":
        t('botapp.ui.text_blocks.MarkdownBlockBuilder.extend')
        for line in lines:
            self._lines.append(line)
        return self

    def build(self) -> str:
        t('botapp.ui.text_blocks.MarkdownBlockBuilder.build')
        return "\n".join(self._lines)


class MarkdownBuilderBase:
    """Shared base for components that construct Markdown via builders."""

    def __init__(self, builder_factory=MarkdownBlockBuilder) -> None:
        t("botapp.ui.text_blocks.MarkdownBuilderBase.__init__")
        self._builder_factory = builder_factory

    def _new_builder(self) -> MarkdownBlockBuilder:
        t('botapp.ui.text_blocks.MarkdownBuilderBase._new_builder')
        return self._builder_factory()

    def create_builder(self) -> MarkdownBlockBuilder:
        """Return a new builder instance for composing Markdown output."""
        t('botapp.ui.text_blocks.MarkdownBuilderBase.create_builder')

        return self._new_builder()


__all__ = [
    "MarkdownBlockBuilder",
    "MarkdownBuilderBase",
    "escape_telegram_markdown",
    "bold_telegram_text",
]
