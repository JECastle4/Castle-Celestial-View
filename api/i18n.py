"""
i18n (internationalization) module for the API.
Handles loading and providing localized strings.
"""
import json
import logging
import threading
from contextvars import ContextVar
from pathlib import Path
from typing import Any, Dict, Optional

logger = logging.getLogger(__name__)


class I18n:
    """Manages localization for the API."""

    def __init__(self, locale: str = 'en'):
        self.translations: Dict[str, Any] = {}
        self.locale = self._load_locale(locale)

    def _get_locale_path(self, locale: str) -> Path:
        """Get the path to a locale JSON file."""
        locales_dir = Path(__file__).parent / 'locales'
        return locales_dir / f'{locale}.json'

    def _load_locale(self, locale: str) -> str:
        """Load translations for a given locale. Returns the resolved locale."""
        locale_path = self._get_locale_path(locale)

        if not locale_path.exists():
            if locale != 'en':
                # Fallback to English if locale doesn't exist
                logger.warning("Locale '%s' not found, falling back to 'en'", locale)
                return self._load_locale('en')
            raise FileNotFoundError(f"Default locale file not found: {locale_path}")

        try:
            with open(locale_path, 'r', encoding='utf-8') as f:
                self.translations = json.load(f)
        except json.JSONDecodeError as e:
            raise ValueError(
                f"Invalid JSON in locale file {locale_path}: {e}"
            ) from e

        return locale

    def get(self, key: str, default: Optional[str] = None, **kwargs) -> str:
        """
        Get a localized string by key.

        Supports dot notation for nested keys: 'dayNames.0'
        Supports string interpolation: get('validation.latitudeRange', value=45)

        Args:
            key: Dot-separated key path to the translation
            default: Default value if key not found
            **kwargs: Variables for string interpolation

        Returns:
            Localized string with interpolations applied
        """
        # Navigate nested dictionary using dot notation
        parts = key.split('.')
        value = self.translations

        for part in parts:
            if isinstance(value, dict) and part in value:
                value = value[part]
            else:
                return default if default is not None else f"[Missing translation: {key}]"

        if not isinstance(value, str):
            return default if default is not None else f"[Invalid translation type for: {key}]"

        # Apply string interpolation
        if not kwargs:
            return value

        try:
            return value.format(**kwargs)
        except KeyError as e:
            return f"[Missing interpolation variable: {e}] {value}"
        except ValueError as e:
            return f"[Malformed translation string: {e}] {value}"

    def set_locale(self, locale: str) -> None:
        """Switch to a different locale."""
        if locale != self.locale:
            self.locale = self._load_locale(locale)


SUPPORTED_LOCALES = {'en', 'en-uk', 'en-us', 'xx-reverse'}

# Per-request locale stored in an async-safe context variable.
# Defaults to English so callers that don't set a locale get English.
_current_locale: ContextVar[str] = ContextVar('current_locale', default='en')

# Cache I18n instances by locale to avoid repeated file reads.
_locale_cache: Dict[str, I18n] = {}
_locale_cache_lock = threading.Lock()


def set_request_locale(locale: str) -> None:
    """Set the locale for the current request context.

    Falls back to 'en' for any unsupported locale value.
    Safe to call from FastAPI middleware — uses a ContextVar so
    concurrent requests each get their own value.
    """
    _current_locale.set(locale if locale in SUPPORTED_LOCALES else 'en')


def get_i18n(locale: Optional[str] = None) -> I18n:
    """Return a cached I18n instance for *locale* (defaults to current request locale)."""
    requested = locale if locale is not None else _current_locale.get()
    if requested not in _locale_cache:
        with _locale_cache_lock:
            # Re-check inside the lock in case another thread populated it
            # while we were waiting.
            if requested not in _locale_cache:
                instance = I18n(requested)
                # Cache under the resolved locale so missing locales that fall
                # back to 'en' share the same instance rather than creating
                # duplicate entries.
                _locale_cache[instance.locale] = instance
                _locale_cache[requested] = instance
    return _locale_cache[requested]


def t(key: str, default: Optional[str] = None, **kwargs) -> str:
    """
    Shorthand for translating a key using the current request locale.

    Args:
        key: Dot-separated key path
        default: Default value if not found
        **kwargs: Variables for string interpolation

    Returns:
        Localized string
    """
    return get_i18n().get(key, default, **kwargs)
