"""UI/Playwright interaction tests for NotebookLM Automator."""

from unittest.mock import MagicMock, patch, PropertyMock

import pytest

from notebooklm_automator.core.automator import NotebookLMAutomator


class TestNotebookLMAutomatorInit:
    """Tests for NotebookLMAutomator initialization."""

    def test_init_default_port(self):
        """Should initialize with default port 9222."""
        automator = NotebookLMAutomator(notebook_url="http://notebooklm.google.com/notebook/123")
        assert automator.port == 9222
        assert automator.notebook_url == "http://notebooklm.google.com/notebook/123"

    def test_init_custom_port(self):
        """Should accept custom port."""
        automator = NotebookLMAutomator(
            notebook_url="http://notebooklm.google.com/notebook/123",
            port=9333,
        )
        assert automator.port == 9333

    def test_init_state(self):
        """Should initialize with null state."""
        automator = NotebookLMAutomator(notebook_url="http://test.com")
        assert automator.playwright is None
        assert automator.browser is None
        assert automator.page is None
        assert automator.lang == "en"


class TestNotebookLMAutomatorConnect:
    """Tests for connect method."""

    @pytest.fixture
    def automator(self) -> NotebookLMAutomator:
        """Create an automator instance for testing."""
        return NotebookLMAutomator(notebook_url="http://notebooklm.google.com/notebook/test")

    def test_connect_success(
        self, automator: NotebookLMAutomator, mock_playwright: MagicMock
    ):
        """Should connect to browser successfully."""
        with patch(
            "notebooklm_automator.core.automator.sync_playwright"
        ) as mock_sync_pw, patch.object(
            automator._chrome_manager, "ensure_running"
        ) as mock_ensure:
            mock_sync_pw.return_value.start.return_value = mock_playwright

            # Set up page mock
            mock_page = MagicMock()
            mock_page.is_closed.return_value = False
            mock_page.evaluate.return_value = "en"
            mock_playwright.chromium.connect_over_cdp.return_value.contexts[
                0
            ].new_page.return_value = mock_page

            automator.connect()

            mock_ensure.assert_called_once()
            assert automator.playwright is not None
            assert automator.page is not None

    def test_connect_skips_if_already_connected(
        self, automator: NotebookLMAutomator
    ):
        """Should skip connection if page is already open."""
        mock_page = MagicMock()
        mock_page.is_closed.return_value = False
        automator.page = mock_page

        with patch(
            "notebooklm_automator.core.automator.sync_playwright"
        ) as mock_sync_pw:
            automator.connect()
            mock_sync_pw.assert_not_called()

    def test_connect_cleans_up_on_failure(self, automator: NotebookLMAutomator):
        """Should clean up resources on connection failure."""
        with patch(
            "notebooklm_automator.core.automator.sync_playwright"
        ) as mock_sync_pw, patch.object(
            automator._chrome_manager, "ensure_running"
        ):
            mock_pw = MagicMock()
            mock_sync_pw.return_value.start.return_value = mock_pw
            mock_pw.chromium.connect_over_cdp.side_effect = Exception(
                "Connection failed"
            )

            with pytest.raises(Exception, match="Connection failed"):
                automator.connect()

            # Should have attempted cleanup
            assert automator.page is None


class TestNotebookLMAutomatorEnsureConnected:
    """Tests for ensure_connected method."""

    @pytest.fixture
    def automator(self) -> NotebookLMAutomator:
        """Create an automator instance."""
        return NotebookLMAutomator(notebook_url="http://test.com")

    def test_ensure_connected_when_disconnected(self, automator: NotebookLMAutomator):
        """Should reconnect when page is None."""
        automator.page = None

        with patch.object(automator, "connect") as mock_connect:
            automator.ensure_connected()
            mock_connect.assert_called_once()

    def test_ensure_connected_when_page_closed(self, automator: NotebookLMAutomator):
        """Should reconnect when page is closed."""
        mock_page = MagicMock()
        mock_page.is_closed.return_value = True
        automator.page = mock_page

        with patch.object(automator, "connect") as mock_connect:
            automator.ensure_connected()
            mock_connect.assert_called_once()

    def test_ensure_connected_when_connected(self, automator: NotebookLMAutomator):
        """Should not reconnect when page is active."""
        mock_page = MagicMock()
        mock_page.is_closed.return_value = False
        mock_page.evaluate.return_value = 2  # 1+1
        automator.page = mock_page

        with patch.object(automator, "connect") as mock_connect:
            automator.ensure_connected()
            mock_connect.assert_not_called()

    def test_ensure_connected_reconnects_on_evaluate_failure(
        self, automator: NotebookLMAutomator
    ):
        """Should reconnect when evaluate fails."""
        mock_page = MagicMock()
        mock_page.is_closed.return_value = False
        mock_page.evaluate.side_effect = Exception("Page crashed")
        automator.page = mock_page

        with patch.object(automator, "connect") as mock_connect:
            automator.ensure_connected()
            mock_connect.assert_called_once()


class TestNotebookLMAutomatorClose:
    """Tests for close method."""

    @pytest.fixture
    def automator(self) -> NotebookLMAutomator:
        """Create an automator instance."""
        return NotebookLMAutomator(notebook_url="http://test.com")

    def test_close_cleans_all_resources(self, automator: NotebookLMAutomator):
        """Should close all resources."""
        mock_page = MagicMock()
        mock_browser = MagicMock()
        mock_playwright = MagicMock()

        automator.page = mock_page
        automator.browser = mock_browser
        automator.playwright = mock_playwright

        with patch.object(automator._chrome_manager, "terminate") as mock_terminate:
            automator.close()

            mock_page.close.assert_called_once()
            mock_browser.close.assert_called_once()
            mock_playwright.stop.assert_called_once()
            mock_terminate.assert_called_once()

        assert automator.page is None
        assert automator.browser is None
        assert automator.playwright is None

    def test_close_handles_exceptions(self, automator: NotebookLMAutomator):
        """Should handle exceptions during close gracefully."""
        mock_page = MagicMock()
        mock_page.close.side_effect = Exception("Close failed")
        automator.page = mock_page

        with patch.object(automator._chrome_manager, "terminate"):
            # Should not raise
            automator.close()

        assert automator.page is None

    def test_close_when_not_connected(self, automator: NotebookLMAutomator):
        """Should handle close when not connected."""
        with patch.object(automator._chrome_manager, "terminate") as mock_terminate:
            automator.close()  # Should not raise
            mock_terminate.assert_called_once()


class TestNotebookLMAutomatorLanguageDetection:
    """Tests for language detection."""

    @pytest.fixture
    def automator(self) -> NotebookLMAutomator:
        """Create an automator instance."""
        return NotebookLMAutomator(notebook_url="http://test.com")

    def test_detect_english(self, automator: NotebookLMAutomator, mock_page: MagicMock):
        """Should detect English language."""
        mock_page.evaluate.return_value = "en-US"
        automator.page = mock_page

        automator._detect_language()

        assert automator.lang == "en"

    def test_detect_hebrew(self, automator: NotebookLMAutomator, mock_page: MagicMock):
        """Should detect Hebrew language."""
        mock_page.evaluate.return_value = "he"
        automator.page = mock_page

        automator._detect_language()

        assert automator.lang == "he"

    def test_detect_hebrew_iw(self, automator: NotebookLMAutomator, mock_page: MagicMock):
        """Should detect Hebrew from 'iw' code."""
        mock_page.evaluate.return_value = "iw"
        automator.page = mock_page

        automator._detect_language()

        assert automator.lang == "he"

    def test_detect_japanese(self, automator: NotebookLMAutomator, mock_page: MagicMock):
        """Should detect Japanese language."""
        mock_page.evaluate.return_value = "ja-JP"
        automator.page = mock_page

        automator._detect_language()

        assert automator.lang == "ja"

    def test_detect_default_on_failure(
        self, automator: NotebookLMAutomator, mock_page: MagicMock
    ):
        """Should default to English on detection failure."""
        mock_page.evaluate.side_effect = Exception("Error")
        automator.page = mock_page

        automator._detect_language()

        assert automator.lang == "en"

    def test_detect_default_for_unknown(
        self, automator: NotebookLMAutomator, mock_page: MagicMock
    ):
        """Should default to English for unknown languages."""
        mock_page.evaluate.return_value = "fr-FR"
        automator.page = mock_page

        automator._detect_language()

        assert automator.lang == "en"


class TestNotebookLMAutomatorSourceOperations:
    """Tests for source-related operations."""

    @pytest.fixture
    def connected_automator(self, mock_page: MagicMock) -> NotebookLMAutomator:
        """Create a connected automator instance."""
        automator = NotebookLMAutomator(notebook_url="http://test.com")
        automator.page = mock_page

        # Set up source manager mock
        mock_source_manager = MagicMock()
        automator._source_manager = mock_source_manager

        return automator

    def test_add_sources_calls_manager(self, connected_automator: NotebookLMAutomator):
        """Should delegate to source manager."""
        sources = [{"type": "url", "content": "http://example.com"}]
        connected_automator._source_manager.add_sources.return_value = [
            {"source": sources[0], "success": True}
        ]

        with patch.object(connected_automator, "ensure_connected"):
            result = connected_automator.add_sources(sources)

        connected_automator._source_manager.add_sources.assert_called_once_with(sources)
        assert len(result) == 1

    def test_clear_sources_calls_manager(self, connected_automator: NotebookLMAutomator):
        """Should delegate to source manager."""
        connected_automator._source_manager.clear_sources.return_value = {
            "success": True,
            "count": 3,
        }

        with patch.object(connected_automator, "ensure_connected"):
            result = connected_automator.clear_sources()

        connected_automator._source_manager.clear_sources.assert_called_once()
        assert result["success"] is True
        assert result["count"] == 3


class TestNotebookLMAutomatorAudioOperations:
    """Tests for audio-related operations."""

    @pytest.fixture
    def connected_automator(self, mock_page: MagicMock) -> NotebookLMAutomator:
        """Create a connected automator instance."""
        automator = NotebookLMAutomator(notebook_url="http://test.com")
        automator.page = mock_page

        # Set up audio manager mock
        mock_audio_manager = MagicMock()
        automator._audio_manager = mock_audio_manager

        return automator

    def test_generate_audio_calls_manager(self, connected_automator: NotebookLMAutomator):
        """Should delegate to audio manager."""
        connected_automator._audio_manager.generate.return_value = "1"

        with patch.object(connected_automator, "ensure_connected"):
            result = connected_automator.generate_audio(
                style="deep_dive", prompt="Make it fun"
            )

        connected_automator._audio_manager.generate.assert_called_once_with(
            "deep_dive", "Make it fun", None
        )
        assert result == "1"

    def test_get_audio_status_calls_manager(
        self, connected_automator: NotebookLMAutomator
    ):
        """Should delegate to audio manager."""
        connected_automator._audio_manager.get_status.return_value = {
            "status": "completed"
        }

        with patch.object(connected_automator, "ensure_connected"):
            result = connected_automator.get_audio_status("1")

        connected_automator._audio_manager.get_status.assert_called_once_with("1")
        assert result["status"] == "completed"

    def test_get_download_url_calls_manager(
        self, connected_automator: NotebookLMAutomator
    ):
        """Should delegate to audio manager."""
        connected_automator._audio_manager.get_download_url.return_value = (
            "http://download.com/audio.mp3"
        )

        with patch.object(connected_automator, "ensure_connected"):
            result = connected_automator.get_download_url("1")

        connected_automator._audio_manager.get_download_url.assert_called_once_with("1")
        assert result == "http://download.com/audio.mp3"

    def test_clear_studio_calls_manager(self, connected_automator: NotebookLMAutomator):
        """Should delegate to audio manager."""
        connected_automator._audio_manager.clear_studio.return_value = {
            "success": True,
            "count": 2,
        }

        with patch.object(connected_automator, "ensure_connected"):
            result = connected_automator.clear_studio()

        connected_automator._audio_manager.clear_studio.assert_called_once()
        assert result["success"] is True
        assert result["count"] == 2

