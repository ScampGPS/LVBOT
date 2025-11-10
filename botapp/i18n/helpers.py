"""Helper functions for i18n in handlers and UI components."""

from __future__ import annotations
from tracking import t

from typing import TYPE_CHECKING, Optional

from .translator import Translator, create_translator

if TYPE_CHECKING:
    from users.manager import UserManager


def get_user_translator(user_manager: 'UserManager', user_id: int) -> Translator:
    """Get a translator instance for a specific user based on their language preference.

    Args:
        user_manager: UserManager instance to retrieve user data
        user_id: Telegram user ID

    Returns:
        Translator instance configured for the user's language (defaults to Spanish)
    """
    t('botapp.i18n.helpers.get_user_translator')
    language = user_manager.get_user_language(user_id)
    return create_translator(language)


def get_translator(language: Optional[str] = None) -> Translator:
    """Get a translator instance for a specific language.

    Args:
        language: Language code ('es' or 'en'). If None, uses default (Spanish)

    Returns:
        Translator instance
    """
    t('botapp.i18n.helpers.get_translator')
    return create_translator(language)
