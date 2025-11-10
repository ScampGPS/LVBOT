"""Translation service for internationalization support."""

from __future__ import annotations
from tracking import t

from typing import Any, Dict, Optional

from .languages import DEFAULT_LANGUAGE, Language
from .strings import STRINGS


class Translator:
    """Handles translation of strings based on user language preference."""

    def __init__(self, language: str | Language = DEFAULT_LANGUAGE):
        """Initialize translator with a specific language.

        Args:
            language: Language code ('es', 'en') or Language enum
        """
        t('botapp.i18n.translator.Translator.__init__')
        # Extract value from enum if needed
        if isinstance(language, Language):
            self.language = language.value
        else:
            self.language = str(language)

    def t(self, key: str, **params: Any) -> str:
        """Translate a key to the current language with optional parameter substitution.

        Args:
            key: Translation key (e.g., 'menu.reserve_court')
            **params: Parameters to substitute in the translated string

        Returns:
            Translated string with parameters substituted

        Example:
            >>> translator = Translator('en')
            >>> translator.t('court.label', number=3)
            'Court 3'
        """
        t('botapp.i18n.translator.Translator.t')
        # Get translation for current language
        default_lang = DEFAULT_LANGUAGE.value if isinstance(DEFAULT_LANGUAGE, Language) else DEFAULT_LANGUAGE
        lang_strings = STRINGS.get(self.language, STRINGS[default_lang])
        translated = lang_strings.get(key)

        # Fallback to default language if key not found
        if translated is None:
            fallback_strings = STRINGS[default_lang]
            translated = fallback_strings.get(key, f"[{key}]")

        # Substitute parameters if provided
        if params:
            try:
                translated = translated.format(**params)
            except KeyError as e:
                # If parameter is missing, return string as-is
                pass

        return translated

    def set_language(self, language: str | Language) -> None:
        """Change the translator's language.

        Args:
            language: New language code or Language enum
        """
        t('botapp.i18n.translator.Translator.set_language')
        # Extract value from enum if needed
        if isinstance(language, Language):
            self.language = language.value
        else:
            self.language = str(language)

    def get_language(self) -> str:
        """Get the current language code.

        Returns:
            Current language code (e.g., 'es', 'en')
        """
        t('botapp.i18n.translator.Translator.get_language')
        return self.language


def create_translator(language: Optional[str | Language] = None) -> Translator:
    """Factory function to create a translator instance.

    Args:
        language: Optional language code. If None, uses DEFAULT_LANGUAGE

    Returns:
        Translator instance
    """
    t('botapp.i18n.translator.create_translator')
    if language is None:
        language = DEFAULT_LANGUAGE
    return Translator(language)


# Global translator instance for convenience (uses default language)
_default_translator = Translator(DEFAULT_LANGUAGE)


def translate(key: str, language: Optional[str | Language] = None, **params: Any) -> str:
    """Convenience function to translate a string.

    Args:
        key: Translation key
        language: Optional language code. If None, uses default translator
        **params: Parameters to substitute in the translated string

    Returns:
        Translated string

    Example:
        >>> translate('menu.reserve_court', language='en')
        '🎾 Reserve Court'
        >>> translate('court.label', language='es', number=2)
        'Cancha 2'
    """
    t('botapp.i18n.translator.translate')
    if language is None:
        return _default_translator.t(key, **params)
    else:
        translator = Translator(language)
        return translator.t(key, **params)
