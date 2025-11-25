"""Unit tests for audio module."""

from unittest.mock import MagicMock

import pytest

from notebooklm_automator.core.audio import AudioManager


class TestAudioManager:
    """Tests for AudioManager class."""

    @pytest.fixture
    def audio_manager(self, mock_page: MagicMock) -> AudioManager:
        """Create an AudioManager with mocked page."""

        def get_text(key: str) -> str:
            texts = {
                "generate_button": "Generate",
                "prompt_textarea_placeholder": "Things to try",
                "generating_status_text": "Generating",
                "error_text": "Error",
                "play_arrow_button": "Play",
                "close_audio_player_button": "Close audio player",
                "more_button": "More",
                "delete_menu_item": "Delete",
                "confirm_delete_button": "Delete",
                "deep_dive_radio_button": "Deep Dive",
                "summary_radio_button": "Summary",
            }
            return texts.get(key, "")

        return AudioManager(mock_page, get_text)

    def test_get_status_invalid_job_id(self, audio_manager: AudioManager):
        """Should return unknown status for invalid job_id format."""
        result = audio_manager.get_status("not_a_number")

        assert result["status"] == "unknown"
        assert "Invalid job_id format" in result["error"]

    def test_get_status_job_not_found(self, audio_manager: AudioManager):
        """Should return unknown status when job_id index is out of range."""
        # Set up parent with no children
        parent = MagicMock()
        children = MagicMock()
        children.count.return_value = 0
        parent.locator.return_value = children
        audio_manager.page.locator.return_value = parent

        result = audio_manager.get_status("5")

        assert result["status"] == "unknown"
        assert "Job ID not found" in result["error"]

    def test_get_status_generating(self, audio_manager: AudioManager):
        """Should return generating status when sync icon present."""
        parent = MagicMock()
        children = MagicMock()
        children.count.return_value = 1

        item = MagicMock()
        item.inner_text.return_value = "sync Generating..."
        item.locator.return_value.is_visible.return_value = False
        children.nth.return_value = item

        parent.locator.return_value = children
        audio_manager.page.locator.return_value = parent

        result = audio_manager.get_status("1")

        assert result["status"] == "generating"

    def test_get_status_completed(self, audio_manager: AudioManager):
        """Should return completed status when play button visible."""
        parent = MagicMock()
        children = MagicMock()
        children.count.return_value = 1

        item = MagicMock()
        item.inner_text.return_value = "Ready to play"
        play_icon = MagicMock()
        play_icon.is_visible.return_value = True
        item.locator.return_value = play_icon
        children.nth.return_value = item

        parent.locator.return_value = children
        audio_manager.page.locator.return_value = parent

        result = audio_manager.get_status("1")

        assert result["status"] == "completed"

    def test_get_status_failed(self, audio_manager: AudioManager):
        """Should return failed status when error text present."""
        parent = MagicMock()
        children = MagicMock()
        children.count.return_value = 1

        item = MagicMock()
        item.inner_text.return_value = "Error occurred"
        item.locator.return_value.is_visible.return_value = False
        children.nth.return_value = item

        parent.locator.return_value = children
        audio_manager.page.locator.return_value = parent

        result = audio_manager.get_status("1")

        assert result["status"] == "failed"

    def test_get_download_url_invalid_job_id(self, audio_manager: AudioManager):
        """Should return None for invalid job_id."""
        result = audio_manager.get_download_url("invalid")
        assert result is None

    def test_get_download_url_job_not_found(self, audio_manager: AudioManager):
        """Should return None when job_id not found."""
        parent = MagicMock()
        items = MagicMock()
        items.count.return_value = 0
        parent.locator.return_value = items
        audio_manager.page.locator.return_value = parent

        result = audio_manager.get_download_url("5")

        assert result is None

    def test_get_download_url_negative_index(self, audio_manager: AudioManager):
        """Should return None for negative index (job_id = 0)."""
        parent = MagicMock()
        items = MagicMock()
        items.count.return_value = 1
        parent.locator.return_value = items
        audio_manager.page.locator.return_value = parent

        result = audio_manager.get_download_url("0")

        assert result is None

    def test_clear_studio_no_items(self, audio_manager: AudioManager):
        """Should return failure when no items to clear."""
        parent = MagicMock()
        parent.count.return_value = 0
        audio_manager.page.locator.return_value = parent

        result = audio_manager.clear_studio()

        assert result["success"] is False
        assert result["count"] == 0
        assert "No generated items found" in result["message"]

    def test_clear_studio_clears_items(self, audio_manager: AudioManager):
        """Should successfully clear available items."""
        parent = MagicMock()
        parent.count.return_value = 1

        items = MagicMock()
        # First call returns 1 item, second call returns 0
        items.count.side_effect = [1, 0]

        item = MagicMock()
        item.scroll_into_view_if_needed.return_value = None

        more_btn = MagicMock()
        more_btn.count.return_value = 1
        more_btn.is_visible.return_value = True
        more_btn.first = more_btn
        item.locator.return_value = more_btn

        items.first = item
        parent.locator.return_value = items
        audio_manager.page.locator.return_value = parent

        delete_menu = MagicMock()
        delete_menu.count.return_value = 1
        delete_menu.is_visible.return_value = True
        delete_menu.first = delete_menu

        confirm_btn = MagicMock()
        confirm_btn.count.return_value = 1
        confirm_btn.is_visible.return_value = True
        confirm_btn.first = confirm_btn

        audio_manager.page.get_by_role.side_effect = [delete_menu, confirm_btn]

        result = audio_manager.clear_studio()

        assert result["success"] is True
        assert result["count"] == 1


class TestAudioManagerGenerate:
    """Tests for AudioManager.generate method."""

    @pytest.fixture
    def audio_manager_for_generate(self, mock_page: MagicMock) -> AudioManager:
        """Create AudioManager configured for generate tests."""

        def get_text(key: str) -> str:
            texts = {
                "generate_button": "Generate",
                "prompt_textarea_placeholder": "Things to try",
                "deep_dive_radio_button": "Deep Dive",
                "summary_radio_button": "Summary",
            }
            return texts.get(key, "")

        # Configure page for generate flow
        edit_icon = MagicMock()
        edit_icon.is_visible.return_value = True

        dialog = MagicMock()
        dialog.is_visible.return_value = True

        generate_btn = MagicMock()
        generate_btn.is_visible.return_value = True
        generate_btn.last = generate_btn

        items = MagicMock()
        items.count.return_value = 1

        def locator_side_effect(selector, *args, **kwargs):
            if "edit" in selector:
                return edit_icon
            elif "mat-dialog-actions" in selector:
                return generate_btn
            elif "artifact-library" in selector:
                return items
            elif "mat-radio" in selector:
                radio = MagicMock()
                radio.count.return_value = 1
                radio.is_visible.return_value = True
                return radio
            elif "textarea" in selector:
                textarea = MagicMock()
                textarea.is_visible.return_value = True
                return textarea
            elif "mat-select" in selector:
                select = MagicMock()
                select.is_visible.return_value = False
                return select
            return MagicMock()

        mock_page.locator.side_effect = locator_side_effect
        mock_page.wait_for_selector.return_value = dialog

        return AudioManager(mock_page, get_text)

    def test_generate_returns_job_id(self, audio_manager_for_generate: AudioManager):
        """Should return job ID as string count."""
        result = audio_manager_for_generate.generate()
        assert result == "1"

    def test_generate_with_style(self, audio_manager_for_generate: AudioManager):
        """Should click style radio button when style provided."""
        result = audio_manager_for_generate.generate(style="deep_dive")
        assert result == "1"

    def test_generate_with_prompt(self, audio_manager_for_generate: AudioManager):
        """Should fill prompt textarea when prompt provided."""
        result = audio_manager_for_generate.generate(prompt="Make it fun")
        assert result == "1"

