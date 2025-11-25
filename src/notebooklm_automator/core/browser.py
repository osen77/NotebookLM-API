"""Browser and Chrome management utilities for NotebookLM Automator."""

import os
import logging
import platform
import shutil
import subprocess
import time
from pathlib import Path
from typing import List, Optional

import requests

logger = logging.getLogger(__name__)


def get_chrome_host() -> str:
    """Get the Chrome host from environment or default."""
    return os.getenv("NOTEBOOKLM_CHROME_HOST", "127.0.0.1")


def is_cdp_available(host: str, port: int) -> bool:
    """Check if Chrome DevTools Protocol is available at the given host and port."""
    try:
        requests.get(f"http://{host}:{port}/json/version", timeout=1)
        return True
    except requests.RequestException:
        return False


def resolve_chrome_binary() -> Optional[str]:
    """Find the Chrome binary path based on OS and environment."""
    configured_path = os.getenv("NOTEBOOKLM_CHROME_PATH")
    if configured_path and Path(configured_path).exists():
        return configured_path

    system = platform.system()
    candidates: List[str] = []

    if system == "Windows":
        candidates.extend([
            r"C:\Program Files\Google\Chrome\Application\chrome.exe",
            r"C:\Program Files (x86)\Google\Chrome\Application\chrome.exe",
        ])
    elif system == "Darwin":
        candidates.append(
            "/Applications/Google Chrome.app/Contents/MacOS/Google Chrome"
        )
    else:
        candidates.extend([
            "/usr/bin/google-chrome",
            "/usr/bin/google-chrome-stable",
            "/usr/bin/chromium-browser",
            "/usr/bin/chromium",
        ])

    for candidate in candidates:
        if Path(candidate).exists():
            return candidate

    return (
        shutil.which("google-chrome")
        or shutil.which("chrome")
        or shutil.which("chromium")
    )


class ChromeManager:
    """Manages Chrome browser process lifecycle."""

    def __init__(self, port: int = 9222):
        self.port = port
        self.chrome_process: Optional[subprocess.Popen] = None
        self._started_browser = False

    def terminate(self) -> None:
        """Terminate the Chrome process if it was started by this manager."""
        if self.chrome_process and self._started_browser:
            try:
                self.chrome_process.terminate()
                self.chrome_process.wait(timeout=5)
            except Exception:
                try:
                    self.chrome_process.kill()
                except Exception:
                    pass
            finally:
                self.chrome_process = None
                self._started_browser = False

    def ensure_running(self, host: str) -> None:
        """Ensure Chrome is running with remote debugging enabled."""
        if is_cdp_available(host, self.port):
            return

        auto_launch = os.getenv("NOTEBOOKLM_AUTO_LAUNCH_CHROME", "1").lower()
        if auto_launch in {"0", "false", "no"}:
            raise RuntimeError(
                f"Chrome debugger endpoint not available on {host}:{self.port} "
                "and NOTEBOOKLM_AUTO_LAUNCH_CHROME is disabled."
            )

        chrome_binary = resolve_chrome_binary()
        if not chrome_binary:
            raise RuntimeError(
                "Could not locate Chrome binary. "
                "Set NOTEBOOKLM_CHROME_PATH to the Chrome/Chromium executable."
            )

        user_data_dir = os.getenv("NOTEBOOKLM_CHROME_USER_DATA_DIR")
        if not user_data_dir:
            user_data_dir = str(Path.home() / ".notebooklm-chrome")

        Path(user_data_dir).mkdir(parents=True, exist_ok=True)

        launch_args = [
            chrome_binary,
            f"--remote-debugging-port={self.port}",
            f"--user-data-dir={user_data_dir}",
            "--disable-popup-blocking",
            "--no-first-run",
            "--no-default-browser-check",
        ]

        creationflags = 0
        if os.name == "nt":
            creationflags = subprocess.CREATE_NO_WINDOW

        self.chrome_process = subprocess.Popen(
            launch_args,
            stdout=subprocess.DEVNULL,
            stderr=subprocess.DEVNULL,
            creationflags=creationflags,
        )
        self._started_browser = True

        deadline = time.time() + 20
        while time.time() < deadline:
            if is_cdp_available(host, self.port):
                logger.info("Started Chrome with remote debugging automatically.")
                return
            time.sleep(0.5)

        self.terminate()
        raise RuntimeError(
            "Timed out waiting for Chrome to expose the remote debugging port."
        )

