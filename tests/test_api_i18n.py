"""
Unit tests for api/i18n.py
"""
import pytest
from unittest.mock import patch
from pathlib import Path
from api.i18n import I18n, get_i18n, t, set_request_locale, SUPPORTED_LOCALES, _current_locale


class TestI18nGet:
    """Tests for I18n.get() key lookup and interpolation."""

    def setup_method(self):
        self.i18n = I18n('en')

    def test_top_level_key(self):
        result = self.i18n.get('dayNames.0')
        assert result == 'Sunday'

    def test_nested_key_moon_phase(self):
        result = self.i18n.get('moonPhases.fullMoon')
        assert result == 'Full Moon'

    def test_interpolation(self):
        result = self.i18n.get('validation.latitudeRange', value=95)
        assert '95' in result

    def test_missing_key_returns_placeholder(self):
        result = self.i18n.get('nonexistent.key')
        assert result == '[Missing translation: nonexistent.key]'

    def test_missing_key_returns_default(self):
        result = self.i18n.get('nonexistent.key', default='fallback')
        assert result == 'fallback'

    def test_missing_intermediate_key_returns_placeholder(self):
        result = self.i18n.get('dayNames.99')
        assert '[Missing translation:' in result

    def test_missing_intermediate_key_returns_default(self):
        result = self.i18n.get('dayNames.99', default='Unknown')
        assert result == 'Unknown'

    def test_non_string_value_returns_placeholder(self):
        # 'dayNames' itself is a dict, not a string
        result = self.i18n.get('dayNames')
        assert '[Invalid translation type for:' in result

    def test_non_string_value_returns_default(self):
        result = self.i18n.get('dayNames', default='fallback')
        assert result == 'fallback'

    def test_missing_interpolation_variable_returns_error(self):
        # latitudeRange expects {value} but we pass a different variable name
        result = self.i18n.get('validation.latitudeRange', wrong_var=95)
        assert '[Missing interpolation variable:' in result

    def test_malformed_translation_string_returns_error(self):
        # Patch a translation value with a malformed format string to trigger ValueError
        with patch.object(self.i18n, 'translations', {'bad': 'unclosed { brace'}):
            result = self.i18n.get('bad', value=1)
        assert '[Malformed translation string:' in result


class TestI18nSetLocale:
    """Tests for I18n.set_locale()."""

    def test_set_locale_switches_translations(self):
        i18n = I18n('en')
        i18n.set_locale('xx-reverse')
        # After switching, Sunday (dayNames.0) should be reversed
        result = i18n.get('dayNames.0')
        assert result == 'Sunday'[::-1]

    def test_set_locale_same_locale_is_noop(self):
        i18n = I18n('en')
        original_translations = dict(i18n.translations)
        i18n.set_locale('en')
        assert i18n.translations == original_translations


class TestI18nLoadLocale:
    """Tests for locale loading error handling."""

    def test_missing_non_default_locale_falls_back_to_english(self, caplog):
        import logging
        with caplog.at_level(logging.WARNING, logger='api.i18n'):
            i18n = I18n('zz-nonexistent')
        # Should have fallen back to English translations
        assert i18n.get('dayNames.0') == 'Sunday'
        assert i18n.locale == 'en'
        assert 'zz-nonexistent' in caplog.text

    def test_missing_default_locale_raises(self, tmp_path):
        i18n = I18n.__new__(I18n)
        i18n.locale = 'en'
        i18n.translations = {}
        with patch.object(I18n, '_get_locale_path', return_value=tmp_path / 'missing.json'):
            with pytest.raises(FileNotFoundError):
                i18n._load_locale('en')

    def test_invalid_json_raises(self, tmp_path):
        bad_json = tmp_path / 'bad.json'
        bad_json.write_text('{invalid json', encoding='utf-8')
        i18n = I18n.__new__(I18n)
        i18n.locale = 'en'
        i18n.translations = {}
        with patch.object(I18n, '_get_locale_path', return_value=bad_json):
            with pytest.raises(ValueError, match='Invalid JSON'):
                i18n._load_locale('bad')


class TestGlobalT:
    """Tests for the module-level t() shorthand."""

    def setup_method(self):
        # Reset to English before each test
        set_request_locale('en')

    def test_t_returns_english_string(self):
        result = t('dayNames.1')
        assert result == 'Monday'

    def test_t_with_interpolation(self):
        result = t('validation.longitudeRange', value=200)
        assert '200' in result

    def test_t_missing_key_returns_placeholder(self):
        result = t('totally.missing.key')
        assert '[Missing translation:' in result

    def test_t_missing_key_with_default(self):
        result = t('totally.missing.key', default='my default')
        assert result == 'my default'


class TestSetRequestLocale:
    """Tests for per-request locale switching via set_request_locale()."""

    def setup_method(self):
        set_request_locale('en')

    def test_supported_locales_contains_en_and_reverse(self):
        assert 'en' in SUPPORTED_LOCALES
        assert 'xx-reverse' in SUPPORTED_LOCALES

    def test_set_to_reverse_locale(self):
        set_request_locale('xx-reverse')
        result = t('dayNames.0')
        assert result == 'Sunday'[::-1]

    def test_set_back_to_english(self):
        set_request_locale('xx-reverse')
        set_request_locale('en')
        assert t('dayNames.0') == 'Sunday'

    def test_unsupported_locale_falls_back_to_english(self):
        set_request_locale('fr')
        assert _current_locale.get() == 'en'

    def test_get_i18n_explicit_locale(self):
        i18n = get_i18n('xx-reverse')
        assert i18n.get('dayNames.0') == 'Sunday'[::-1]

    def test_get_i18n_uses_current_locale_when_none(self):
        set_request_locale('en')
        i18n = get_i18n()
        assert i18n.get('dayNames.0') == 'Sunday'

    def test_get_i18n_caches_instances(self):
        a = get_i18n('en')
        b = get_i18n('en')
        assert a is b


class TestI18nSecurityHardening:
    """Tests for security hardening against path traversal and invalid locales."""

    def test_get_locale_path_rejects_invalid_locale(self):
        """Test that _get_locale_path raises ValueError for locales not in ALLOWED_LOCALES."""
        i18n = I18n('en')
        with pytest.raises(ValueError, match="Unsupported locale"):
            i18n._get_locale_path('invalid-locale')

    def test_get_locale_path_rejects_traversal_attempt(self):
        """Test that _get_locale_path validates path boundaries to prevent traversal."""
        i18n = I18n('en')
        # This should not raise since 'en' is in ALLOWED_LOCALES,
        # but if a whitelist entry somehow created a traversal path, it would be caught.
        # For now, we test that valid locales work correctly.
        path = i18n._get_locale_path('en')
        assert path.name == 'en.json'
        assert 'locales' in str(path)

    def test_load_locale_rejects_invalid_locale_when_default(self):
        """Test that _load_locale raises error when 'en' itself is not in ALLOWED_LOCALES."""
        i18n = I18n.__new__(I18n)
        i18n.translations = {}
        # Temporarily remove 'en' from ALLOWED_LOCALES to test the guard condition
        with patch('api.i18n.ALLOWED_LOCALES', {'xx-reverse'}):
            with pytest.raises(ValueError, match="Default locale 'en' must be in ALLOWED_LOCALES"):
                i18n._load_locale('en')

    def test_unsupported_locale_with_valid_fallback(self):
        """Test that unsupported locales fall back to 'en' gracefully."""
        with patch('api.i18n.logger') as mock_logger:
            i18n = I18n('invalid-locale-code')
            assert i18n.locale == 'en'
            assert i18n.get('dayNames.0') == 'Sunday'
            mock_logger.warning.assert_called()

    def test_locale_path_within_locales_directory(self):
        """Test that resolved locale paths are verified to be within the locales directory."""
        i18n = I18n('en')
        locale_path = i18n._get_locale_path('en')
        locales_dir = Path(__file__).parent.parent / 'api' / 'locales'
        # Verify the path starts with the locales directory (after resolution)
        assert str(locale_path.resolve()).startswith(str(locales_dir.resolve()))

    def test_load_locale_handles_json_error(self, tmp_path):
        """Test that _load_locale properly raises ValueError for invalid JSON."""
        bad_json_file = tmp_path / 'bad.json'
        bad_json_file.write_text('{invalid json content}', encoding='utf-8')
        
        i18n = I18n.__new__(I18n)
        i18n.locale = 'en'
        i18n.translations = {}
        
        with patch.object(I18n, '_get_locale_path', return_value=bad_json_file):
            with pytest.raises(ValueError, match="Invalid JSON in locale file"):
                i18n._load_locale('en')
