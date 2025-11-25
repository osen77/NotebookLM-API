"""Unit tests for selectors module."""

import pytest

from notebooklm_automator.core.selectors import (
    DEFAULT_LANGUAGE,
    LANGUAGE_ALIASES,
    get_selector_by_language,
    get_selectors,
)


class TestGetSelectors:
    """Tests for get_selectors function."""

    def test_returns_mapping(self):
        """Should return a mapping of language codes to selector dictionaries."""
        from collections.abc import Mapping

        selectors = get_selectors()
        assert isinstance(selectors, Mapping)
        assert "en" in selectors
        assert "he" in selectors

    def test_english_selectors_present(self):
        """Should have all expected English selectors."""
        selectors = get_selectors()
        en = selectors["en"]

        expected_keys = [
            "add_source_button",
            "source_type_website",
            "source_type_youtube",
            "source_type_text",
            "insert_button",
            "generate_button",
            "delete_menu_item",
            "confirm_delete_button",
        ]

        for key in expected_keys:
            assert key in en, f"Missing key: {key}"

    def test_hebrew_selectors_present(self):
        """Should have Hebrew translations for all keys."""
        selectors = get_selectors()
        en_keys = set(selectors["en"].keys())
        he_keys = set(selectors["he"].keys())

        assert en_keys == he_keys, "Hebrew should have same keys as English"

    def test_selectors_immutable(self):
        """Selectors should be immutable (MappingProxyType)."""
        selectors = get_selectors()
        with pytest.raises(TypeError):
            selectors["en"]["new_key"] = "value"


class TestGetSelectorByLanguage:
    """Tests for get_selector_by_language function."""

    def test_english_selector(self):
        """Should return English selector for 'en' language."""
        result = get_selector_by_language("en", "add_source_button")
        assert result == "Add sources"

    def test_hebrew_selector(self):
        """Should return Hebrew selector for 'he' language."""
        result = get_selector_by_language("he", "add_source_button")
        assert result == "הוספת מקורות"

    def test_language_alias_iw_to_he(self):
        """Should resolve 'iw' alias to 'he' (Hebrew)."""
        result = get_selector_by_language("iw", "add_source_button")
        assert result == "הוספת מקורות"

    def test_fallback_to_english_for_unknown_language(self):
        """Should fallback to English for unknown language codes."""
        result = get_selector_by_language("fr", "add_source_button")
        assert result == "Add sources"

    def test_unknown_key_returns_none(self):
        """Should return None for unknown selector keys."""
        result = get_selector_by_language("en", "nonexistent_key")
        assert result is None

    def test_all_audio_style_buttons(self):
        """Should have all audio style radio button selectors."""
        styles = ["deep_dive", "summary", "critique", "debate"]
        for style in styles:
            key = f"{style}_radio_button"
            result = get_selector_by_language("en", key)
            assert result is not None, f"Missing selector for {key}"


class TestLanguageConstants:
    """Tests for language-related constants."""

    def test_default_language_is_english(self):
        """Default language should be English."""
        assert DEFAULT_LANGUAGE == "en"

    def test_language_aliases_contains_iw(self):
        """Language aliases should map 'iw' to 'he'."""
        assert "iw" in LANGUAGE_ALIASES
        assert LANGUAGE_ALIASES["iw"] == "he"

