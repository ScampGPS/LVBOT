"""Language constants and enums for internationalization."""

from enum import Enum


class Language(str, Enum):
    """Supported languages."""
    SPANISH = "es"
    ENGLISH = "en"


# Default language for new users
DEFAULT_LANGUAGE = Language.SPANISH

# Language display names
LANGUAGE_NAMES = {
    Language.SPANISH: "Español",
    Language.ENGLISH: "English",
}

# Language flags for UI
LANGUAGE_FLAGS = {
    Language.SPANISH: "🇪🇸",
    Language.ENGLISH: "🇺🇸",
}
