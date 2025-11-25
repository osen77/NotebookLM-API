"""Unit tests for sources module."""

from unittest.mock import MagicMock

import pytest

from notebooklm_automator.core.sources import SourceManager, group_sources


class TestGroupSources:
    """Tests for group_sources function."""

    def test_groups_url_sources(self):
        """Should combine multiple URL sources into one with newlines."""
        sources = [
            {"type": "url", "content": "http://example1.com"},
            {"type": "url", "content": "http://example2.com"},
        ]
        result = group_sources(sources)

        assert len(result) == 1
        assert result[0]["type"] == "url"
        assert "http://example1.com\nhttp://example2.com" == result[0]["content"]

    def test_groups_youtube_sources(self):
        """Should combine YouTube sources together."""
        sources = [
            {"type": "youtube", "content": "https://youtube.com/watch?v=1"},
            {"type": "youtube", "content": "https://youtube.com/watch?v=2"},
        ]
        result = group_sources(sources)

        assert len(result) == 1
        assert result[0]["type"] == "youtube"
        assert "\n" in result[0]["content"]

    def test_groups_url_and_youtube_together(self):
        """Should group URL and YouTube sources together."""
        sources = [
            {"type": "url", "content": "http://example.com"},
            {"type": "youtube", "content": "https://youtube.com/watch?v=1"},
        ]
        result = group_sources(sources)

        assert len(result) == 1
        # Type should be from first url-like source
        assert result[0]["type"] == "url"

    def test_text_sources_not_grouped(self):
        """Text sources should remain separate."""
        sources = [
            {"type": "text", "content": "First text"},
            {"type": "text", "content": "Second text"},
        ]
        result = group_sources(sources)

        assert len(result) == 2
        assert result[0]["type"] == "text"
        assert result[1]["type"] == "text"

    def test_mixed_sources(self):
        """Should group URLs together but keep text separate."""
        sources = [
            {"type": "url", "content": "http://example1.com"},
            {"type": "text", "content": "Some text"},
            {"type": "url", "content": "http://example2.com"},
            {"type": "text", "content": "More text"},
        ]
        result = group_sources(sources)

        # Should have: 1 grouped URL + 2 text sources
        assert len(result) == 3
        assert result[0]["type"] == "url"
        assert "http://example1.com\nhttp://example2.com" == result[0]["content"]
        assert result[1]["type"] == "text"
        assert result[2]["type"] == "text"

    def test_empty_sources(self):
        """Should handle empty source list."""
        result = group_sources([])
        assert result == []

    def test_single_url_source(self):
        """Single URL source should pass through unchanged."""
        sources = [{"type": "url", "content": "http://example.com"}]
        result = group_sources(sources)

        assert len(result) == 1
        assert result[0]["content"] == "http://example.com"

    def test_preserves_source_order(self):
        """Text sources should maintain order relative to grouped URLs."""
        sources = [
            {"type": "text", "content": "Before"},
            {"type": "url", "content": "http://example.com"},
            {"type": "text", "content": "After"},
        ]
        result = group_sources(sources)

        # URL comes first in result, then text sources in order
        assert result[0]["type"] == "url"
        assert result[1]["content"] == "Before"
        assert result[2]["content"] == "After"


class TestSourceManager:
    """Tests for SourceManager class."""

    @pytest.fixture
    def source_manager(self, mock_page: MagicMock) -> SourceManager:
        """Create a SourceManager with mocked page."""

        def get_text(key: str) -> str:
            texts = {
                "add_source_button": "Add sources",
                "source_type_website": "Website",
                "source_type_youtube": "YouTube",
                "source_type_text": "Copied text",
                "insert_button": "Insert",
                "delete_source_menu_item": "Remove source",
                "confirm_delete_button": "Delete",
                "url_input_placeholder": "Paste URLs*",
            }
            return texts.get(key, "")

        return SourceManager(mock_page, get_text)

    def test_is_dialog_open_true(self, source_manager: SourceManager):
        """Should return True when dialog is visible."""
        source_manager.page.locator.return_value.last.is_visible.return_value = True
        assert source_manager.is_dialog_open() is True

    def test_is_dialog_open_false(self, source_manager: SourceManager):
        """Should return False when dialog is not visible."""
        source_manager.page.locator.return_value.last.is_visible.return_value = False
        assert source_manager.is_dialog_open() is False

    def test_is_dialog_open_exception(self, source_manager: SourceManager):
        """Should return False on exception."""
        source_manager.page.locator.side_effect = Exception("Error")
        assert source_manager.is_dialog_open() is False

    def test_open_dialog_when_closed(self, source_manager: SourceManager):
        """Should click add button when dialog is closed."""
        # Set up: dialog locator returns closed state
        dialog_locator = MagicMock()
        dialog_locator.last.is_visible.return_value = False

        # Add button is visible
        mock_button = MagicMock()
        mock_button.count.return_value = 1
        mock_button.is_visible.return_value = True
        mock_button.first = mock_button

        def locator_side_effect(selector, *args, **kwargs):
            if "mat-dialog-container" in selector:
                return dialog_locator
            return mock_button

        source_manager.page.locator.side_effect = locator_side_effect

        source_manager.open_dialog()

        mock_button.click.assert_called_once()

    def test_open_dialog_already_open(self, source_manager: SourceManager):
        """Should not click when dialog is already open."""
        source_manager.page.locator.return_value.last.is_visible.return_value = True

        source_manager.open_dialog()

        # Click should not be called since dialog is open
        # (is_dialog_open returns True)
        assert source_manager.page.locator.return_value.first.click.call_count == 0

    def test_add_sources_calls_correct_methods(self, source_manager: SourceManager):
        """Should call appropriate add method for each source type."""
        # Set up dialog mock properly
        dialog_locator = MagicMock()
        dialog_locator.last.is_visible.return_value = False

        button_locator = MagicMock()
        button_locator.count.return_value = 1
        button_locator.is_visible.return_value = True
        button_locator.first = button_locator

        close_locator = MagicMock()
        close_locator.count.return_value = 0

        def locator_side_effect(selector, *args, **kwargs):
            if "mat-dialog-container" in selector:
                return dialog_locator
            elif "close" in selector:
                return close_locator
            return button_locator

        source_manager.page.locator.side_effect = locator_side_effect
        source_manager.page.get_by_text.return_value = button_locator
        source_manager.page.get_by_role.return_value = button_locator
        source_manager.page.get_by_placeholder.return_value = button_locator

        sources = [{"type": "url", "content": "http://example.com"}]
        results = source_manager.add_sources(sources)

        assert len(results) == 1
        assert results[0]["success"] is True

    def test_add_sources_handles_error(self, source_manager: SourceManager):
        """Should capture errors and return failure result."""
        source_manager.page.locator.side_effect = Exception("UI Error")

        sources = [{"type": "url", "content": "http://example.com"}]
        results = source_manager.add_sources(sources)

        assert len(results) == 1
        assert results[0]["success"] is False
        assert "UI Error" in results[0]["error"]

    def test_add_sources_unknown_type(self, source_manager: SourceManager):
        """Should return error for unknown source type."""
        # Set up to pass dialog checks
        dialog_locator = MagicMock()
        dialog_locator.last.is_visible.return_value = False
        dialog_locator.count.return_value = 0
        source_manager.page.locator.return_value = dialog_locator

        sources = [{"type": "unknown", "content": "something"}]
        results = source_manager.add_sources(sources)

        assert len(results) == 1
        assert results[0]["success"] is False
        assert "Unknown source type" in results[0]["error"]

    def test_clear_sources_returns_count(self, source_manager: SourceManager):
        """Should return success and count of cleared sources."""
        # Set up empty source list
        source_manager.page.locator.return_value.count.return_value = 0

        result = source_manager.clear_sources()

        assert result["success"] is False  # No sources to clear
        assert result["count"] == 0

