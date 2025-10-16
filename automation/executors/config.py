"""Configuration objects for executor behaviour toggles."""

from __future__ import annotations

from dataclasses import dataclass


@dataclass(frozen=True)
class AsyncExecutorConfig:
    """Feature toggles for the unified async executor."""

    use_experienced_mode: bool = False
    use_smart_navigation: bool = False
    natural_flow: bool = False


DEFAULT_EXECUTOR_CONFIG = AsyncExecutorConfig()
