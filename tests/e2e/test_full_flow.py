"""End-to-end tests for NotebookLM Automator.

These tests require:
- NOTEBOOKLM_URL environment variable set to a valid notebook URL
- Chrome browser available (or NOTEBOOKLM_CHROME_PATH set)
- Valid Google authentication in the Chrome profile

Run with: pytest tests/e2e/ -v
"""

import os
import time

import pytest

from notebooklm_automator.core.automator import NotebookLMAutomator


# Skip all E2E tests if NOTEBOOKLM_URL is not set
pytestmark = pytest.mark.skipif(
    not os.getenv("NOTEBOOKLM_URL"),
    reason="NOTEBOOKLM_URL not set - skipping E2E tests",
)


class TestE2ESourceOperations:
    """End-to-end tests for source operations."""

    def test_add_url_source(self, real_automator: NotebookLMAutomator):
        """Should add a URL source successfully."""
        sources = [{"type": "url", "content": "https://example.com"}]

        results = real_automator.add_sources(sources)

        assert len(results) == 1
        assert results[0]["success"] is True

    def test_add_text_source(self, real_automator: NotebookLMAutomator):
        """Should add a text source successfully."""
        sources = [
            {
                "type": "text",
                "content": "This is a test text source for NotebookLM E2E testing. "
                "It contains enough content to be processed by the system.",
            }
        ]

        results = real_automator.add_sources(sources)

        assert len(results) == 1
        assert results[0]["success"] is True

    def test_add_multiple_sources(self, real_automator: NotebookLMAutomator):
        """Should add multiple sources successfully."""
        sources = [
            {"type": "url", "content": "https://example.com"},
            {"type": "text", "content": "Test content for multiple source test."},
        ]

        results = real_automator.add_sources(sources)

        assert len(results) == 2
        # At least one should succeed
        assert any(r["success"] for r in results)

    def test_clear_sources(self, real_automator: NotebookLMAutomator):
        """Should clear all sources."""
        # First add a source
        real_automator.add_sources(
            [{"type": "text", "content": "Temporary test content to be cleared."}]
        )
        time.sleep(1)

        # Then clear
        result = real_automator.clear_sources()

        assert "success" in result
        assert "count" in result


class TestE2EAudioGeneration:
    """End-to-end tests for audio generation.

    Note: These tests may take several minutes as they trigger actual audio generation.
    """

    @pytest.mark.slow
    def test_generate_audio_default(self, real_automator: NotebookLMAutomator):
        """Should trigger audio generation with default settings."""
        # Ensure there's content to generate from
        real_automator.add_sources(
            [
                {
                    "type": "text",
                    "content": "This is test content for audio generation. "
                    "The podcast should discuss this interesting topic "
                    "about automated testing and software quality.",
                }
            ]
        )
        time.sleep(2)

        job_id = real_automator.generate_audio()

        assert job_id is not None
        assert job_id.isdigit()

    @pytest.mark.slow
    def test_generate_audio_with_prompt(self, real_automator: NotebookLMAutomator):
        """Should trigger audio generation with custom prompt."""
        job_id = real_automator.generate_audio(prompt="Keep it brief and technical")

        assert job_id is not None
        assert job_id.isdigit()

    def test_get_audio_status(self, real_automator: NotebookLMAutomator):
        """Should check audio generation status."""
        # Get status of any existing item (or generate one)
        status = real_automator.get_audio_status("1")

        assert "status" in status
        assert status["status"] in ["generating", "completed", "failed", "unknown"]

    def test_clear_studio(self, real_automator: NotebookLMAutomator):
        """Should clear generated audio items."""
        result = real_automator.clear_studio()

        assert "success" in result
        assert "count" in result


class TestE2EFullWorkflow:
    """End-to-end tests for complete workflows."""

    @pytest.mark.slow
    def test_complete_workflow(self, real_automator: NotebookLMAutomator):
        """Test the complete workflow: add sources -> generate audio -> check status -> clear."""
        # Step 1: Add sources
        sources = [
            {
                "type": "text",
                "content": "This is comprehensive test content for the full workflow test. "
                "It covers the entire process from adding sources to generating audio.",
            }
        ]
        add_results = real_automator.add_sources(sources)
        assert len(add_results) > 0

        time.sleep(2)

        # Step 2: Generate audio
        job_id = real_automator.generate_audio(prompt="Make it short and informative")
        assert job_id is not None

        # Step 3: Check status
        status = real_automator.get_audio_status(job_id)
        assert status["status"] in ["generating", "completed", "failed", "unknown"]

        # Step 4: Wait briefly and clear
        time.sleep(2)
        clear_result = real_automator.clear_sources()
        assert "success" in clear_result


class TestE2EConnectionResilience:
    """End-to-end tests for connection handling."""

    def test_reconnection_after_page_close(self, real_automator: NotebookLMAutomator):
        """Should reconnect after page is closed."""
        # Close the page
        if real_automator.page:
            real_automator.page.close()

        # Should auto-reconnect on next operation
        real_automator.ensure_connected()

        # Verify connection works
        assert real_automator.page is not None
        assert not real_automator.page.is_closed()

    def test_multiple_operations_same_session(self, real_automator: NotebookLMAutomator):
        """Should handle multiple operations in same session."""
        # Operation 1: Add source
        real_automator.add_sources([{"type": "text", "content": "First operation"}])

        # Operation 2: Check status
        status = real_automator.get_audio_status("1")
        assert "status" in status

        # Operation 3: Clear sources
        result = real_automator.clear_sources()
        assert "success" in result


class TestE2EErrorHandling:
    """End-to-end tests for error handling scenarios."""

    def test_add_invalid_url_source(self, real_automator: NotebookLMAutomator):
        """Should handle invalid URL gracefully."""
        sources = [{"type": "url", "content": "not-a-valid-url"}]

        results = real_automator.add_sources(sources)

        # Should return a result (may be failure)
        assert len(results) == 1
        # The success status depends on how NotebookLM handles invalid URLs

    def test_get_status_nonexistent_job(self, real_automator: NotebookLMAutomator):
        """Should handle nonexistent job ID."""
        status = real_automator.get_audio_status("99999")

        assert status["status"] in ["unknown", "failed"]

    def test_get_download_url_invalid_job(self, real_automator: NotebookLMAutomator):
        """Should handle invalid job for download URL."""
        url = real_automator.get_download_url("invalid")

        assert url is None

