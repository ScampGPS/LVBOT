"""Internationalization (i18n) module for multi-language support.

This module provides translation services for the bot, supporting
Spanish (default) and English languages.

Usage:
    from botapp.i18n import translate, Translator, Language, get_user_translator

    # Simple translation
    text = translate('menu.reserve_court', language='en')

    # Translation with parameters
    text = translate('court.label', language='es', number=3)

    # Create a user-specific translator
    translator = get_user_translator(user_manager, user_id)
    text = translator.t('welcome.title')
"""

from .helpers import get_translator, get_user_translator
from .languages import DEFAULT_LANGUAGE, LANGUAGE_FLAGS, LANGUAGE_NAMES, Language
from .translator import Translator, create_translator, translate

__all__ = [
    'Language',
    'DEFAULT_LANGUAGE',
    'LANGUAGE_NAMES',
    'LANGUAGE_FLAGS',
    'Translator',
    'create_translator',
    'translate',
    'get_translator',
    'get_user_translator',
]
