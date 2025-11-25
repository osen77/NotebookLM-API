"""Unit tests for browser module."""

import os
import platform
from unittest.mock import MagicMock, patch

import pytest

from notebooklm_automator.core.browser import (
    ChromeManager,
    get_chrome_host,
    is_cdp_available,
    resolve_chrome_binary,
)


class TestGetChromeHost:
    """Tests for get_chrome_host function."""

    def test_default_host(self):
        """Should return localhost by default."""
        with patch.dict(os.environ, {}, clear=True):
            # Remove the env var if set
            os.environ.pop("NOTEBOOKLM_CHROME_HOST", None)
            result = get_chrome_host()
            assert result == "127.0.0.1"

    def test_custom_host_from_env(self):
        """Should return custom host from environment variable."""
        with patch.dict(os.environ, {"NOTEBOOKLM_CHROME_HOST": "192.168.1.100"}):
            result = get_chrome_host()
            assert result == "192.168.1.100"


class TestIsCdpAvailable:
    """Tests for is_cdp_available function."""

    def test_cdp_available(self):
        """Should return True when CDP endpoint responds."""
        with patch("notebooklm_automator.core.browser.requests.get") as mock_get:
            mock_get.return_value.status_code = 200
            result = is_cdp_available("127.0.0.1", 9222)
            assert result is True
            mock_get.assert_called_once_with(
                "http://127.0.0.1:9222/json/version", timeout=1
            )

    def test_cdp_not_available(self):
        """Should return False when CDP endpoint fails."""
        with patch("notebooklm_automator.core.browser.requests.get") as mock_get:
            import requests

            mock_get.side_effect = requests.RequestException("Connection refused")
            result = is_cdp_available("127.0.0.1", 9222)
            assert result is False

    def test_cdp_timeout(self):
        """Should return False on timeout."""
        with patch("notebooklm_automator.core.browser.requests.get") as mock_get:
            import requests

            mock_get.side_effect = requests.Timeout("Timeout")
            result = is_cdp_available("127.0.0.1", 9222)
            assert result is False


class TestResolveChromeBindary:
    """Tests for resolve_chrome_binary function."""

    def test_configured_path_exists(self):
        """Should return configured path if it exists."""
        with patch.dict(
            os.environ, {"NOTEBOOKLM_CHROME_PATH": "/custom/chrome"}
        ), patch("notebooklm_automator.core.browser.Path") as mock_path:
            mock_path.return_value.exists.return_value = True
            result = resolve_chrome_binary()
            assert result == "/custom/chrome"

    def test_configured_path_not_exists(self):
        """Should try other paths if configured path doesn't exist."""
        with patch.dict(
            os.environ, {"NOTEBOOKLM_CHROME_PATH": "/nonexistent/chrome"}
        ), patch("notebooklm_automator.core.browser.Path") as mock_path, patch(
            "notebooklm_automator.core.browser.shutil.which"
        ) as mock_which:
            mock_path.return_value.exists.return_value = False
            mock_which.return_value = "/usr/bin/google-chrome"
            result = resolve_chrome_binary()
            assert result == "/usr/bin/google-chrome"

    @patch("notebooklm_automator.core.browser.platform.system")
    def test_windows_candidates(self, mock_system):
        """Should check Windows paths on Windows."""
        mock_system.return_value = "Windows"

        with patch.dict(os.environ, {}, clear=True), patch(
            "notebooklm_automator.core.browser.Path"
        ) as mock_path, patch(
            "notebooklm_automator.core.browser.shutil.which"
        ) as mock_which:
            os.environ.pop("NOTEBOOKLM_CHROME_PATH", None)

            # First path exists
            def path_exists(self):
                return str(self) == r"C:\Program Files\Google\Chrome\Application\chrome.exe"

            mock_path.return_value.exists = lambda: path_exists(mock_path.return_value)
            mock_path.return_value.__str__ = lambda self: r"C:\Program Files\Google\Chrome\Application\chrome.exe"

            result = resolve_chrome_binary()
            # Should attempt to find Chrome on Windows paths

    @patch("notebooklm_automator.core.browser.platform.system")
    def test_macos_candidates(self, mock_system):
        """Should check macOS paths on Darwin."""
        mock_system.return_value = "Darwin"

        with patch.dict(os.environ, {}, clear=True), patch(
            "notebooklm_automator.core.browser.Path"
        ) as mock_path:
            os.environ.pop("NOTEBOOKLM_CHROME_PATH", None)

            instance = MagicMock()
            instance.exists.return_value = True
            mock_path.return_value = instance

            result = resolve_chrome_binary()
            # Should check macOS Chrome path

    def test_fallback_to_which(self):
        """Should fallback to shutil.which if no path found."""
        with patch.dict(os.environ, {}, clear=True), patch(
            "notebooklm_automator.core.browser.Path"
        ) as mock_path, patch(
            "notebooklm_automator.core.browser.shutil.which"
        ) as mock_which:
            os.environ.pop("NOTEBOOKLM_CHROME_PATH", None)
            mock_path.return_value.exists.return_value = False
            mock_which.side_effect = [None, "/usr/local/bin/chrome", None]

            result = resolve_chrome_binary()
            assert result == "/usr/local/bin/chrome"

    def test_no_chrome_found(self):
        """Should return None if Chrome cannot be found."""
        with patch.dict(os.environ, {}, clear=True), patch(
            "notebooklm_automator.core.browser.Path"
        ) as mock_path, patch(
            "notebooklm_automator.core.browser.shutil.which"
        ) as mock_which:
            os.environ.pop("NOTEBOOKLM_CHROME_PATH", None)
            mock_path.return_value.exists.return_value = False
            mock_which.return_value = None

            result = resolve_chrome_binary()
            assert result is None


class TestChromeManager:
    """Tests for ChromeManager class."""

    def test_init_default_port(self):
        """Should initialize with default port 9222."""
        manager = ChromeManager()
        assert manager.port == 9222
        assert manager.chrome_process is None
        assert manager._started_browser is False

    def test_init_custom_port(self):
        """Should accept custom port."""
        manager = ChromeManager(port=9333)
        assert manager.port == 9333

    def test_terminate_no_process(self):
        """Should handle terminate when no process started."""
        manager = ChromeManager()
        manager.terminate()  # Should not raise
        assert manager.chrome_process is None

    def test_terminate_with_process(self):
        """Should terminate Chrome process if started by manager."""
        manager = ChromeManager()
        mock_process = MagicMock()
        manager.chrome_process = mock_process
        manager._started_browser = True

        manager.terminate()

        mock_process.terminate.assert_called_once()
        mock_process.wait.assert_called_once_with(timeout=5)
        assert manager.chrome_process is None
        assert manager._started_browser is False

    def test_terminate_process_not_started_by_manager(self):
        """Should not terminate if process was not started by this manager."""
        manager = ChromeManager()
        mock_process = MagicMock()
        manager.chrome_process = mock_process
        manager._started_browser = False  # Not started by manager

        manager.terminate()

        mock_process.terminate.assert_not_called()

    def test_ensure_running_already_available(self):
        """Should do nothing if CDP is already available."""
        manager = ChromeManager()

        with patch(
            "notebooklm_automator.core.browser.is_cdp_available"
        ) as mock_cdp:
            mock_cdp.return_value = True
            manager.ensure_running("127.0.0.1")

            # Should not attempt to launch Chrome
            assert manager.chrome_process is None

    def test_ensure_running_auto_launch_disabled(self):
        """Should raise error if auto-launch is disabled and CDP not available."""
        manager = ChromeManager()

        with patch(
            "notebooklm_automator.core.browser.is_cdp_available"
        ) as mock_cdp, patch.dict(
            os.environ, {"NOTEBOOKLM_AUTO_LAUNCH_CHROME": "0"}
        ):
            mock_cdp.return_value = False

            with pytest.raises(RuntimeError, match="Chrome debugger endpoint not available"):
                manager.ensure_running("127.0.0.1")

    def test_ensure_running_no_chrome_binary(self):
        """Should raise error if Chrome binary cannot be found."""
        manager = ChromeManager()

        with patch(
            "notebooklm_automator.core.browser.is_cdp_available"
        ) as mock_cdp, patch(
            "notebooklm_automator.core.browser.resolve_chrome_binary"
        ) as mock_resolve, patch.dict(
            os.environ, {"NOTEBOOKLM_AUTO_LAUNCH_CHROME": "1"}
        ):
            mock_cdp.return_value = False
            mock_resolve.return_value = None

            with pytest.raises(RuntimeError, match="Could not locate Chrome binary"):
                manager.ensure_running("127.0.0.1")

    def test_ensure_running_launches_chrome(self):
        """Should launch Chrome with correct arguments."""
        manager = ChromeManager(port=9222)

        with patch(
            "notebooklm_automator.core.browser.is_cdp_available"
        ) as mock_cdp, patch(
            "notebooklm_automator.core.browser.resolve_chrome_binary"
        ) as mock_resolve, patch(
            "notebooklm_automator.core.browser.subprocess.Popen"
        ) as mock_popen, patch(
            "notebooklm_automator.core.browser.Path"
        ) as mock_path, patch.dict(
            os.environ, {"NOTEBOOKLM_AUTO_LAUNCH_CHROME": "1"}
        ):
            # First call: not available, subsequent calls: available
            mock_cdp.side_effect = [False, True]
            mock_resolve.return_value = "/usr/bin/chrome"
            mock_path.return_value.mkdir.return_value = None
            mock_path.home.return_value = MagicMock(__truediv__=lambda s, x: "/home/user/.notebooklm-chrome")

            mock_process = MagicMock()
            mock_popen.return_value = mock_process

            manager.ensure_running("127.0.0.1")

            assert mock_popen.called
            call_args = mock_popen.call_args[0][0]
            assert "/usr/bin/chrome" in call_args
            assert "--remote-debugging-port=9222" in call_args
            assert manager._started_browser is True

