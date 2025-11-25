"""Tests for NotebookLM Automator API routes."""

from unittest.mock import MagicMock

import pytest
from fastapi.testclient import TestClient


class TestHealthEndpoint:
    """Tests for GET /health endpoint."""

    def test_health_check_returns_ok(self, test_client: TestClient):
        """Health endpoint should return ok status."""
        response = test_client.get("/health")
        assert response.status_code == 200
        assert response.json() == {"status": "ok"}


class TestUploadSourcesEndpoint:
    """Tests for POST /sources/upload endpoint."""

    def test_upload_single_url_source(
        self, test_client: TestClient, mock_automator: MagicMock
    ):
        """Should upload a single URL source successfully."""
        response = test_client.post(
            "/sources/upload",
            json={"sources": [{"type": "url", "content": "http://example.com"}]},
        )

        assert response.status_code == 200
        data = response.json()
        assert data["overall_success"] is True
        assert len(data["results"]) == 1
        assert data["results"][0]["success"] is True
        mock_automator.add_sources.assert_called_once()

    def test_upload_multiple_sources(
        self, test_client: TestClient, mock_automator: MagicMock
    ):
        """Should upload multiple sources successfully."""
        mock_automator.add_sources.return_value = [
            {"source": {"type": "url", "content": "http://example1.com"}, "success": True},
            {"source": {"type": "text", "content": "Some text"}, "success": True},
        ]

        response = test_client.post(
            "/sources/upload",
            json={
                "sources": [
                    {"type": "url", "content": "http://example1.com"},
                    {"type": "text", "content": "Some text"},
                ]
            },
        )

        assert response.status_code == 200
        data = response.json()
        assert data["overall_success"] is True
        assert len(data["results"]) == 2

    def test_upload_youtube_source(
        self, test_client: TestClient, mock_automator: MagicMock
    ):
        """Should upload YouTube source successfully."""
        mock_automator.add_sources.return_value = [
            {
                "source": {"type": "youtube", "content": "https://youtube.com/watch?v=123"},
                "success": True,
            }
        ]

        response = test_client.post(
            "/sources/upload",
            json={
                "sources": [
                    {"type": "youtube", "content": "https://youtube.com/watch?v=123"}
                ]
            },
        )

        assert response.status_code == 200
        assert response.json()["overall_success"] is True

    def test_upload_text_source(
        self, test_client: TestClient, mock_automator: MagicMock
    ):
        """Should upload text source successfully."""
        mock_automator.add_sources.return_value = [
            {"source": {"type": "text", "content": "Test content"}, "success": True}
        ]

        response = test_client.post(
            "/sources/upload",
            json={"sources": [{"type": "text", "content": "Test content"}]},
        )

        assert response.status_code == 200
        assert response.json()["overall_success"] is True

    def test_upload_partial_failure(
        self, test_client: TestClient, mock_automator: MagicMock
    ):
        """Should handle partial upload failures."""
        mock_automator.add_sources.return_value = [
            {"source": {"type": "url", "content": "http://valid.com"}, "success": True},
            {
                "source": {"type": "url", "content": "http://invalid.com"},
                "success": False,
                "error": "Failed to add source",
            },
        ]

        response = test_client.post(
            "/sources/upload",
            json={
                "sources": [
                    {"type": "url", "content": "http://valid.com"},
                    {"type": "url", "content": "http://invalid.com"},
                ]
            },
        )

        assert response.status_code == 200
        data = response.json()
        assert data["overall_success"] is False
        assert data["results"][0]["success"] is True
        assert data["results"][1]["success"] is False

    def test_upload_empty_sources_list(
        self, test_client: TestClient, mock_automator: MagicMock
    ):
        """Should handle empty sources list."""
        mock_automator.add_sources.return_value = []

        response = test_client.post("/sources/upload", json={"sources": []})

        assert response.status_code == 200
        data = response.json()
        assert data["overall_success"] is True
        assert len(data["results"]) == 0

    def test_upload_invalid_source_type(self, test_client: TestClient):
        """Should reject invalid source type."""
        response = test_client.post(
            "/sources/upload",
            json={"sources": [{"type": "invalid", "content": "something"}]},
        )

        assert response.status_code == 422  # Validation error

    def test_upload_missing_content(self, test_client: TestClient):
        """Should reject source without content."""
        response = test_client.post(
            "/sources/upload", json={"sources": [{"type": "url"}]}
        )

        assert response.status_code == 422

    def test_upload_missing_sources_key(self, test_client: TestClient):
        """Should reject request without sources key."""
        response = test_client.post("/sources/upload", json={})

        assert response.status_code == 422


class TestClearSourcesEndpoint:
    """Tests for POST /sources/clear endpoint."""

    def test_clear_sources_success(
        self, test_client: TestClient, mock_automator: MagicMock
    ):
        """Should clear sources successfully."""
        mock_automator.clear_sources.return_value = {
            "success": True,
            "count": 5,
            "message": None,
        }

        response = test_client.post("/sources/clear")

        assert response.status_code == 200
        data = response.json()
        assert data["success"] is True
        assert data["count"] == 5
        mock_automator.clear_sources.assert_called_once()

    def test_clear_sources_no_sources(
        self, test_client: TestClient, mock_automator: MagicMock
    ):
        """Should handle case when no sources to clear."""
        mock_automator.clear_sources.return_value = {
            "success": False,
            "count": 0,
            "message": "No sources found",
        }

        response = test_client.post("/sources/clear")

        assert response.status_code == 200
        data = response.json()
        assert data["success"] is False
        assert data["count"] == 0


class TestGenerateAudioEndpoint:
    """Tests for POST /audio/generate endpoint."""

    def test_generate_audio_default(
        self, test_client: TestClient, mock_automator: MagicMock
    ):
        """Should generate audio with default settings."""
        response = test_client.post("/audio/generate", json={})

        assert response.status_code == 200
        data = response.json()
        assert data["job_id"] == "job_123"
        assert data["status"] == "started"
        mock_automator.generate_audio.assert_called_once_with(
            style=None, language=None, prompt=None
        )

    def test_generate_audio_with_style(
        self, test_client: TestClient, mock_automator: MagicMock
    ):
        """Should generate audio with specified style."""
        response = test_client.post("/audio/generate", json={"style": "deep_dive"})

        assert response.status_code == 200
        mock_automator.generate_audio.assert_called_once_with(
            style="deep_dive", language=None, prompt=None
        )

    def test_generate_audio_with_prompt(
        self, test_client: TestClient, mock_automator: MagicMock
    ):
        """Should generate audio with custom prompt."""
        response = test_client.post(
            "/audio/generate", json={"prompt": "Make it funny and engaging"}
        )

        assert response.status_code == 200
        mock_automator.generate_audio.assert_called_once_with(
            style=None, language=None, prompt="Make it funny and engaging"
        )

    def test_generate_audio_with_language(
        self, test_client: TestClient, mock_automator: MagicMock
    ):
        """Should generate audio with specified language."""
        response = test_client.post("/audio/generate", json={"language": "Spanish"})

        assert response.status_code == 200
        mock_automator.generate_audio.assert_called_once_with(
            style=None, language="Spanish", prompt=None
        )

    def test_generate_audio_all_options(
        self, test_client: TestClient, mock_automator: MagicMock
    ):
        """Should generate audio with all options specified."""
        response = test_client.post(
            "/audio/generate",
            json={
                "style": "summary",
                "prompt": "Keep it short",
                "language": "French",
            },
        )

        assert response.status_code == 200
        mock_automator.generate_audio.assert_called_once_with(
            style="summary", language="French", prompt="Keep it short"
        )

    def test_generate_audio_all_styles(
        self, test_client: TestClient, mock_automator: MagicMock
    ):
        """Should accept all valid audio styles."""
        styles = ["summary", "deep_dive", "criticism", "debate"]

        for style in styles:
            mock_automator.generate_audio.reset_mock()
            response = test_client.post("/audio/generate", json={"style": style})
            assert response.status_code == 200, f"Style {style} should be valid"

    def test_generate_audio_invalid_style(self, test_client: TestClient):
        """Should reject invalid audio style."""
        response = test_client.post(
            "/audio/generate", json={"style": "invalid_style"}
        )

        assert response.status_code == 422

    def test_generate_audio_exception(
        self, test_client: TestClient, mock_automator: MagicMock
    ):
        """Should return 500 on generation exception."""
        mock_automator.generate_audio.side_effect = Exception("Generation failed")

        response = test_client.post("/audio/generate", json={})

        assert response.status_code == 500
        assert "Generation failed" in response.json()["detail"]


class TestAudioStatusEndpoint:
    """Tests for GET /audio/status/{job_id} endpoint."""

    def test_status_completed(
        self, test_client: TestClient, mock_automator: MagicMock
    ):
        """Should return completed status with download URL."""
        mock_automator.get_audio_status.return_value = {"status": "completed"}
        mock_automator.get_download_url.return_value = "http://download.com/audio.mp3"

        response = test_client.get("/audio/status/job_123")

        assert response.status_code == 200
        data = response.json()
        assert data["job_id"] == "job_123"
        assert data["status"] == "completed"
        assert data["download_url"] == "http://download.com/audio.mp3"

    def test_status_generating(
        self, test_client: TestClient, mock_automator: MagicMock
    ):
        """Should return generating status without download URL."""
        mock_automator.get_audio_status.return_value = {"status": "generating"}

        response = test_client.get("/audio/status/job_456")

        assert response.status_code == 200
        data = response.json()
        assert data["status"] == "generating"
        assert data["download_url"] is None
        mock_automator.page.close.assert_called()

    def test_status_failed(
        self, test_client: TestClient, mock_automator: MagicMock
    ):
        """Should return failed status."""
        mock_automator.get_audio_status.return_value = {"status": "failed"}

        response = test_client.get("/audio/status/job_789")

        assert response.status_code == 200
        assert response.json()["status"] == "failed"

    def test_status_unknown(
        self, test_client: TestClient, mock_automator: MagicMock
    ):
        """Should return unknown status."""
        mock_automator.get_audio_status.return_value = {"status": "unknown"}

        response = test_client.get("/audio/status/unknown_job")

        assert response.status_code == 200
        assert response.json()["status"] == "unknown"


class TestAudioFileEndpoint:
    """Tests for GET /audio/file/{job_id} endpoint."""

    def test_get_download_url_success(
        self, test_client: TestClient, mock_automator: MagicMock
    ):
        """Should return download URL for completed audio."""
        mock_automator.get_audio_status.return_value = {"status": "completed"}
        mock_automator.get_download_url.return_value = "http://download.com/audio.mp3"

        response = test_client.get("/audio/file/job_123")

        assert response.status_code == 200
        assert response.json()["url"] == "http://download.com/audio.mp3"

    def test_get_download_url_not_completed(
        self, test_client: TestClient, mock_automator: MagicMock
    ):
        """Should return 400 when audio not completed."""
        mock_automator.get_audio_status.return_value = {"status": "generating"}

        response = test_client.get("/audio/file/job_123")

        assert response.status_code == 400
        assert "not completed" in response.json()["detail"]

    def test_get_download_url_failed(
        self, test_client: TestClient, mock_automator: MagicMock
    ):
        """Should return 400 when audio generation failed."""
        mock_automator.get_audio_status.return_value = {"status": "failed"}

        response = test_client.get("/audio/file/job_123")

        assert response.status_code == 400

    def test_get_download_url_missing(
        self, test_client: TestClient, mock_automator: MagicMock
    ):
        """Should return 500 when download URL cannot be retrieved."""
        mock_automator.get_audio_status.return_value = {"status": "completed"}
        mock_automator.get_download_url.return_value = None

        response = test_client.get("/audio/file/job_123")

        assert response.status_code == 500
        assert "Could not retrieve download URL" in response.json()["detail"]


class TestClearStudioEndpoint:
    """Tests for POST /studio/clear endpoint."""

    def test_clear_studio_success(
        self, test_client: TestClient, mock_automator: MagicMock
    ):
        """Should clear studio successfully."""
        mock_automator.clear_studio.return_value = {
            "success": True,
            "count": 3,
            "message": None,
        }

        response = test_client.post("/studio/clear")

        assert response.status_code == 200
        data = response.json()
        assert data["success"] is True
        assert data["count"] == 3
        mock_automator.clear_studio.assert_called_once()

    def test_clear_studio_nothing_to_clear(
        self, test_client: TestClient, mock_automator: MagicMock
    ):
        """Should handle case when nothing to clear."""
        mock_automator.clear_studio.return_value = {
            "success": False,
            "count": 0,
            "message": "No generated items found",
        }

        response = test_client.post("/studio/clear")

        assert response.status_code == 200
        data = response.json()
        assert data["success"] is False
        assert data["count"] == 0
        assert data["message"] == "No generated items found"


class TestRunTestsEndpoint:
    """Tests for POST /run-tests endpoint."""

    def test_run_tests_default(self, test_client: TestClient):
        """Should run all tests by default."""
        from unittest.mock import patch, MagicMock

        mock_result = MagicMock()
        mock_result.returncode = 0
        mock_result.stdout = "5 passed in 1.5s"
        mock_result.stderr = ""

        with patch("notebooklm_automator.api.routes.subprocess.run") as mock_run:
            mock_run.return_value = mock_result
            response = test_client.post("/run-tests")

        assert response.status_code == 200
        data = response.json()
        assert data["success"] is True
        assert "output" in data
        assert data["test_type"] == "all"

    def test_run_tests_with_type(self, test_client: TestClient):
        """Should accept test_type parameter."""
        from unittest.mock import patch, MagicMock

        mock_result = MagicMock()
        mock_result.returncode = 0
        mock_result.stdout = "10 passed in 2.0s"
        mock_result.stderr = ""

        with patch("notebooklm_automator.api.routes.subprocess.run") as mock_run:
            mock_run.return_value = mock_result
            response = test_client.post("/run-tests?test_type=unit")

        assert response.status_code == 200
        data = response.json()
        assert data["success"] is True
        assert data["test_type"] == "unit"

    def test_run_tests_invalid_type(self, test_client: TestClient):
        """Should reject invalid test type."""
        response = test_client.post("/run-tests?test_type=invalid")

        assert response.status_code == 400
        assert "Invalid test_type" in response.json()["detail"]

    def test_run_tests_failure(self, test_client: TestClient):
        """Should handle test failures correctly."""
        from unittest.mock import patch, MagicMock

        mock_result = MagicMock()
        mock_result.returncode = 1
        mock_result.stdout = "3 passed, 2 failed in 1.5s"
        mock_result.stderr = "FAILED test_example.py"

        with patch("notebooklm_automator.api.routes.subprocess.run") as mock_run:
            mock_run.return_value = mock_result
            response = test_client.post("/run-tests")

        assert response.status_code == 200
        data = response.json()
        assert data["success"] is False
        assert data["summary"]["passed"] == 3
        assert data["summary"]["failed"] == 2

    def test_run_tests_verbose(self, test_client: TestClient):
        """Should pass verbose flag to pytest."""
        from unittest.mock import patch, MagicMock

        mock_result = MagicMock()
        mock_result.returncode = 0
        mock_result.stdout = "5 passed"
        mock_result.stderr = ""

        with patch("notebooklm_automator.api.routes.subprocess.run") as mock_run:
            mock_run.return_value = mock_result
            response = test_client.post("/run-tests?verbose=true")

        assert response.status_code == 200
        # Verify -v was passed to pytest
        call_args = mock_run.call_args[0][0]
        assert "-v" in call_args

