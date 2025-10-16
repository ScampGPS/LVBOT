"""Compatibility shim for migrated tennis executor."""

from automation.executors.tennis import TennisExecutor, create_tennis_config_from_user_info

__all__ = ["TennisExecutor", "create_tennis_config_from_user_info"]
