"""Reusable helpers that mimic human input patterns for Playwright flows."""

from __future__ import annotations

import asyncio
import random
from typing import Optional, Tuple

from playwright.async_api import Page


class HumanLikeActions:
    """Encapsulate typing and mouse patterns that resemble a real user."""

    def __init__(self, page: Page, *, speed_multiplier: float = 2.5) -> None:
        self.page = page
        self.speed_multiplier = speed_multiplier
        self._last_mouse_pos: Optional[Tuple[float, float]] = None

    # ------------------------------------------------------------------
    # Timing helpers
    # ------------------------------------------------------------------
    def _apply_speed(self, value: float) -> float:
        return max(0.05, value / self.speed_multiplier)

    async def pause(self, minimum: float, maximum: float) -> None:
        await asyncio.sleep(self._apply_speed(random.uniform(minimum, maximum)))

    # ------------------------------------------------------------------
    # Typing helpers
    # ------------------------------------------------------------------
    async def type_text(
        self,
        element,
        text: str,
        *,
        mistake_prob: float = 0.12,
        base_delay_range: Tuple[int, int] = (90, 220),
    ) -> None:
        if text is None:
            text = ""

        await element.click()
        await self.pause(0.3, 0.8)
        await element.fill("")
        await self.pause(0.2, 0.5)

        for index, char in enumerate(text):
            if index > 0 and random.random() < mistake_prob:
                await self._type_and_correct(element, base_delay_range, exclude=char.lower())

            delay = max(30, int(random.randint(*base_delay_range) / self.speed_multiplier))
            await element.type(char, delay=delay)

            if random.random() < (0.18 / self.speed_multiplier):
                await self.pause(0.3, 1.2)
            if index and index % 3 == 0 and random.random() < 0.06:
                await self.pause(0.6, 1.4)

        await self.pause(0.5, 1.5)

    async def _type_and_correct(
        self,
        element,
        base_delay_range: Tuple[int, int],
        *,
        exclude: Optional[str] = None,
    ) -> None:
        alphabet = "abcdefghijklmnopqrstuvwxyz"
        wrong_characters = [c for c in alphabet if c != exclude]
        if not wrong_characters:
            return

        wrong_char = random.choice(wrong_characters)
        delay = max(20, int(random.randint(*base_delay_range) / self.speed_multiplier))
        await element.type(wrong_char, delay=delay)
        await self.pause(0.1, 0.4)
        await element.press("Backspace")
        await self.pause(0.2, 0.6)

    # ------------------------------------------------------------------
    # Mouse helpers
    # ------------------------------------------------------------------
    async def move_mouse_random(self) -> None:
        width, height = await self._viewport_dimensions()
        target_x = random.uniform(width * 0.15, width * 0.85)
        target_y = random.uniform(height * 0.15, height * 0.85)
        await self._mouse_curve_to(target_x, target_y)
        await self.pause(0.2, 0.6)

        if random.random() < 0.18:
            delta = random.randint(-200, 220)
            try:
                await self.page.mouse.wheel(0, delta)
                await self.pause(0.4, 0.9)
            except Exception:
                pass

    async def move_mouse_to_element(
        self,
        element,
        *,
        bias: Tuple[float, float] = (0.5, 0.6),
    ) -> None:
        try:
            box = await element.bounding_box()
        except Exception:
            box = None
        if not box:
            return

        target_x = box["x"] + box["width"] * bias[0]
        target_y = box["y"] + box["height"] * bias[1]
        await self._mouse_curve_to(target_x, target_y)
        await self.pause(0.4, 1.0)

    async def _mouse_curve_to(self, target_x: float, target_y: float) -> None:
        start_x, start_y = await self._current_mouse_position()

        control_x1 = start_x + random.uniform(-80, 120)
        control_y1 = start_y + random.uniform(-80, 120)
        control_x2 = target_x + random.uniform(-120, 80)
        control_y2 = target_y + random.uniform(-120, 80)

        steps = random.randint(9, 16)
        easing = random.uniform(0.6, 1.4)

        for i in range(1, steps + 1):
            t_ratio = i / steps
            inv = 1 - t_ratio
            x = (
                inv ** 3 * start_x
                + 3 * inv ** 2 * t_ratio * control_x1
                + 3 * inv * t_ratio ** 2 * control_x2
                + t_ratio ** 3 * target_x
            )
            y = (
                inv ** 3 * start_y
                + 3 * inv ** 2 * t_ratio * control_y1
                + 3 * inv * t_ratio ** 2 * control_y2
                + t_ratio ** 3 * target_y
            )

            try:
                await self.page.mouse.move(x, y)
            except Exception:
                continue

            await asyncio.sleep(self._apply_speed(random.uniform(0.045, 0.095) * easing))

        self._last_mouse_pos = (target_x, target_y)

    async def _current_mouse_position(self) -> Tuple[float, float]:
        if self._last_mouse_pos is not None:
            return self._last_mouse_pos

        width, height = await self._viewport_dimensions()
        initial = (width / 2, height * 0.75)
        try:
            await self.page.mouse.move(*initial)
        except Exception:
            pass
        self._last_mouse_pos = initial
        return initial

    async def _viewport_dimensions(self) -> Tuple[float, float]:
        size = self.page.viewport_size
        if size:
            return float(size.get("width", 1280)), float(size.get("height", 720))

        dims = await self.page.evaluate(
            "({width: window.innerWidth || 1280, height: window.innerHeight || 720})"
        )
        return float(dims.get("width", 1280)), float(dims.get("height", 720))


__all__ = ["HumanLikeActions"]
