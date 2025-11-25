"""Shared pytest fixtures for NotebookLM Automator tests."""

import os
from typing import Generator
from unittest.mock import MagicMock, PropertyMock

import pytest
from fastapi.testclient import TestClient

from notebooklm_automator.api.app import app
from notebooklm_automator.api.routes import get_automator


@pytest.fixture
def mock_page() -> MagicMock:
    """Create a mocked Playwright Page for UI tests."""
    page = MagicMock()
    page.is_closed.return_value = False
    page.evaluate.return_value = "en"
    page.goto.return_value = None
    page.wait_for_load_state.return_value = None
    page.wait_for_timeout.return_value = None
    page.wait_for_selector.return_value = MagicMock()
    page.set_viewport_size.return_value = None
    page.close.return_value = None

    # Mock locator chain
    mock_locator = MagicMock()
    mock_locator.count.return_value = 1
    mock_locator.is_visible.return_value = True
    mock_locator.first = mock_locator
    mock_locator.last = mock_locator
    mock_locator.nth.return_value = mock_locator
    mock_locator.click.return_value = None
    mock_locator.fill.return_value = None
    mock_locator.press.return_value = None
    mock_locator.inner_text.return_value = "play_arrow"
    mock_locator.scroll_into_view_if_needed.return_value = None
    mock_locator.wait_for.return_value = None

    page.locator.return_value = mock_locator
    page.get_by_text.return_value = mock_locator
    page.get_by_role.return_value = mock_locator
    page.get_by_placeholder.return_value = mock_locator

    return page


@pytest.fixture
def mock_browser() -> MagicMock:
    """Create a mocked Playwright Browser."""
    browser = MagicMock()
    context = MagicMock()
    page = MagicMock()

    page.is_closed.return_value = False
    page.evaluate.return_value = "en"
    context.new_page.return_value = page
    browser.contexts = [context]

    return browser


@pytest.fixture
def mock_playwright(mock_browser: MagicMock) -> MagicMock:
    """Create a mocked Playwright instance."""
    pw = MagicMock()
    pw.chromium.connect_over_cdp.return_value = mock_browser
    pw.stop.return_value = None
    return pw


@pytest.fixture
def mock_automator() -> MagicMock:
    """Create a mock automator for API testing."""
    mock = MagicMock()

    # Configure page mock
    mock_page = MagicMock()
    mock_page.close.return_value = None
    mock.page = mock_page

    # Configure default return values for all automator methods
    mock.add_sources.return_value = [
        {"source": {"type": "url", "content": "http://example.com"}, "success": True}
    ]
    mock.clear_sources.return_value = {
        "success": True, "count": 5, "message": None}
    mock.generate_audio.return_value = "job_123"
    mock.get_audio_status.return_value = {"status": "completed"}
    mock.get_download_url.return_value = "http://download.com/audio.mp3"
    mock.clear_studio.return_value = {
        "success": True, "count": 3, "message": None}
    mock.connect.return_value = None
    mock.close.return_value = None

    return mock


@pytest.fixture
def test_client(mock_automator: MagicMock) -> Generator[TestClient, None, None]:
    """Create a FastAPI TestClient with mocked automator dependency."""
    app.dependency_overrides[get_automator] = lambda: mock_automator
    client = TestClient(app)
    yield client
    app.dependency_overrides.clear()


@pytest.fixture
def test_client_no_mock() -> Generator[TestClient, None, None]:
    """Create a FastAPI TestClient without mocked dependencies (for integration tests)."""
    client = TestClient(app)
    yield client


# E2E Fixtures - Only used when NOTEBOOKLM_URL is set
@pytest.fixture(scope="session")
def e2e_enabled() -> bool:
    """Check if E2E tests should run."""
    return bool(os.getenv("NOTEBOOKLM_URL"))


@pytest.fixture(scope="class")
def real_automator():
    """Create a real automator instance for E2E tests.

    This fixture requires NOTEBOOKLM_URL to be set in the environment.
    """
    from notebooklm_automator.core.automator import NotebookLMAutomator

    url = os.getenv("NOTEBOOKLM_URL")
    if not url:
        pytest.skip("NOTEBOOKLM_URL not set - skipping E2E test")

    port = int(os.getenv("NOTEBOOKLM_CHROME_PORT", "9222"))
    automator = NotebookLMAutomator(notebook_url=url, port=port)
    automator.connect()
    yield automator
    automator.close()


# Helper fixtures for common test data
@pytest.fixture
def sample_url_source() -> dict:
    """Sample URL source for testing."""
    return {"type": "url", "content": "https://example.com/article"}


@pytest.fixture
def sample_youtube_source() -> dict:
    """Sample YouTube source for testing."""
    return {"type": "youtube", "content": "https://www.youtube.com/watch?v=dQw4w9WgXcQ"}


@pytest.fixture
def sample_text_source() -> dict:
    """Sample text source for testing."""
    return {
        "type": "text",
        "content": "This is a sample text source for NotebookLM automation testing.",
    }


@pytest.fixture
def sample_sources(
    sample_url_source: dict, sample_youtube_source: dict, sample_text_source: dict
) -> list:
    """Collection of sample sources for testing."""
    return [sample_url_source, sample_youtube_source, sample_text_source]
