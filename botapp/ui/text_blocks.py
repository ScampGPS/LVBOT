"""Reusable helpers for composing Markdown messages."""

from __future__ import annotations
from tracking import t

from typing import Iterable, List


class MarkdownBlockBuilder:
    """Utility for building Markdown messages with bullet support."""

    __slots__ = ("_lines",)

    def __init__(self) -> None:
        t("botapp.ui.text_blocks.MarkdownBlockBuilder.__init__")
        self._lines: List[str] = []

    def line(self, text: str = "") -> "MarkdownBlockBuilder":
        self._lines.append(text)
        return self

    def heading(self, text: str) -> "MarkdownBlockBuilder":
        if text:
            self._lines.append(text)
        return self

    def bullet(self, text: str) -> "MarkdownBlockBuilder":
        if text:
            self._lines.append(f"• {text}")
        return self

    def bullets(self, items: Iterable[str]) -> "MarkdownBlockBuilder":
        for item in items:
            if item:
                self._lines.append(f"• {item}")
        return self

    def blank(self) -> "MarkdownBlockBuilder":
        self._lines.append("")
        return self

    def extend(self, lines: Iterable[str]) -> "MarkdownBlockBuilder":
        for line in lines:
            self._lines.append(line)
        return self

    def build(self) -> str:
        return "\n".join(self._lines)


class MarkdownBuilderBase:
    """Shared base for components that construct Markdown via builders."""

    def __init__(self, builder_factory=MarkdownBlockBuilder) -> None:
        t("botapp.ui.text_blocks.MarkdownBuilderBase.__init__")
        self._builder_factory = builder_factory

    def _new_builder(self) -> MarkdownBlockBuilder:
        return self._builder_factory()

    def create_builder(self) -> MarkdownBlockBuilder:
        """Return a new builder instance for composing Markdown output."""

        return self._new_builder()


__all__ = ["MarkdownBlockBuilder", "MarkdownBuilderBase"]
