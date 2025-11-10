"""Reusable helpers that mimic human input patterns for Playwright flows."""

from __future__ import annotations
from tracking import t

import asyncio
import random
from typing import Optional, Tuple

from playwright.async_api import Page


class HumanLikeActions:
    """Encapsulate typing and mouse patterns that resemble a real user."""

    def __init__(self, page: Page, *, speed_multiplier: float = 2.5) -> None:
        t('automation.executors.flows.human_behaviors.HumanLikeActions.__init__')
        self.page = page
        self.speed_multiplier = speed_multiplier
        self._last_mouse_pos: Optional[Tuple[float, float]] = None

    # ------------------------------------------------------------------
    # Timing helpers
    # ------------------------------------------------------------------
    def _apply_speed(self, value: float) -> float:
        t('automation.executors.flows.human_behaviors.HumanLikeActions._apply_speed')
        return max(0.05, value / self.speed_multiplier)

    async def pause(self, minimum: float, maximum: float) -> None:
        t('automation.executors.flows.human_behaviors.HumanLikeActions.pause')
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
        t('automation.executors.flows.human_behaviors.HumanLikeActions.type_text')
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
        t('automation.executors.flows.human_behaviors.HumanLikeActions._type_and_correct')
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
        t('automation.executors.flows.human_behaviors.HumanLikeActions.move_mouse_random')
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
        t('automation.executors.flows.human_behaviors.HumanLikeActions.move_mouse_to_element')
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
        t('automation.executors.flows.human_behaviors.HumanLikeActions._mouse_curve_to')
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
        t('automation.executors.flows.human_behaviors.HumanLikeActions._current_mouse_position')
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
        t('automation.executors.flows.human_behaviors.HumanLikeActions._viewport_dimensions')
        size = self.page.viewport_size
        if size:
            return float(size.get("width", 1280)), float(size.get("height", 720))

        dims = await self.page.evaluate(
            "({width: window.innerWidth || 1280, height: window.innerHeight || 720})"
        )
        return float(dims.get("width", 1280)), float(dims.get("height", 720))

    # ------------------------------------------------------------------
    # Enhanced behavioral patterns (Solution 2 - Anti-bot evasion)
    # ------------------------------------------------------------------
    async def scroll_naturally(
        self,
        *,
        scroll_count_range: Tuple[int, int] = (2, 4),
        scroll_amount_range: Tuple[int, int] = (100, 400),
        scroll_back_prob: float = 0.3,
    ) -> None:
        """Scroll page naturally like a human reading content.

        Args:
            scroll_count_range: Min/max number of scroll actions
            scroll_amount_range: Min/max pixels to scroll per action
            scroll_back_prob: Probability of scrolling back up (like re-reading)
        """
        t('automation.executors.flows.human_behaviors.HumanLikeActions.scroll_naturally')
        scroll_count = random.randint(*scroll_count_range)

        for _ in range(scroll_count):
            scroll_amount = random.randint(*scroll_amount_range)
            try:
                await self.page.mouse.wheel(0, scroll_amount)
            except Exception:
                pass
            await self.pause(0.8, 1.5)

        # Sometimes scroll back up like re-reading
        if random.random() < scroll_back_prob:
            scroll_back = random.randint(50, 150)
            try:
                await self.page.mouse.wheel(0, -scroll_back)
            except Exception:
                pass
            await self.pause(0.5, 1.0)

    async def click_with_hesitation(
        self,
        element,
        *,
        hesitation_prob: float = 0.7,
        correction_count_range: Tuple[int, int] = (0, 2),
    ) -> None:
        """Click element with human-like hesitation and aiming.

        Instead of moving directly to button, move near it first,
        make small corrections (like aiming), then click.

        Args:
            element: The element to click
            hesitation_prob: Probability of showing hesitation (0.0-1.0)
            correction_count_range: Range for number of small aim corrections
        """
        t('automation.executors.flows.human_behaviors.HumanLikeActions.click_with_hesitation')
        try:
            box = await element.bounding_box()
        except Exception:
            # Fallback to simple click if bounding box fails
            await element.click()
            return

        if not box:
            await element.click()
            return

        # If hesitating, move near the button first
        if random.random() < hesitation_prob:
            # Move to area near button (not directly on it)
            near_x = box["x"] + box["width"] * random.uniform(0.3, 0.7)
            near_y = box["y"] + box["height"] * random.uniform(0.3, 0.7)

            # Add slight random offset
            near_x += random.uniform(-20, 20)
            near_y += random.uniform(-20, 20)

            await self._mouse_curve_to(near_x, near_y)
            await self.pause(0.3, 0.8)

            # Small corrections (like fine-tuning aim)
            correction_count = random.randint(*correction_count_range)
            for _ in range(correction_count):
                adjust_x = near_x + random.uniform(-10, 10)
                adjust_y = near_y + random.uniform(-10, 10)
                try:
                    await self.page.mouse.move(adjust_x, adjust_y)
                except Exception:
                    pass
                await self.pause(0.1, 0.3)

        # Now move to button center and click
        target_x = box["x"] + box["width"] * 0.5
        target_y = box["y"] + box["height"] * 0.5
        await self._mouse_curve_to(target_x, target_y)
        await self.pause(0.2, 0.5)

        await element.click()

    async def reading_pause(
        self, *, duration_range: Tuple[float, float] = (2.0, 4.0)
    ) -> None:
        """Pause as if reading or thinking about the content.

        Args:
            duration_range: Min/max seconds to pause
        """
        t('automation.executors.flows.human_behaviors.HumanLikeActions.reading_pause')
        await self.pause(*duration_range)

    async def natural_page_interaction(
        self,
        *,
        scroll: bool = True,
        reading_pause: bool = True,
    ) -> None:
        """Perform natural page interaction (scrolling, reading pauses).

        Combines scrolling and reading pauses in a realistic sequence.
        Use this before performing booking actions.

        Args:
            scroll: Whether to perform scrolling
            reading_pause: Whether to add reading pauses
        """
        t('automation.executors.flows.human_behaviors.HumanLikeActions.natural_page_interaction')
        if scroll:
            await self.scroll_naturally()

        if reading_pause:
            await self.reading_pause()


__all__ = ["HumanLikeActions"]
