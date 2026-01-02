"""Main automator class for Google NotebookLM."""

import logging
from typing import Any, Dict, List, Optional, Tuple

from playwright.sync_api import sync_playwright, Error as PlaywrightError

import os

from notebooklm_automator.core.browser import ChromeManager, get_chrome_host
from notebooklm_automator.core.cookies import (
    get_auth_state,
    has_chrome_login_state,
    save_storage_state,
)
from notebooklm_automator.core.selectors import get_selector_by_language
from notebooklm_automator.core.sources import SourceManager
from notebooklm_automator.core.audio import AudioManager

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
)
logger = logging.getLogger(__name__)


class NotebookLMAutomator:
    """
    Automator for Google NotebookLM.

    Handles connecting to an existing Chrome session via CDP,
    adding sources, and generating audio.
    """

    def __init__(self, notebook_url: str, port: int = 9222):
        """
        Initialize the automator.

        Args:
            notebook_url: The URL of the NotebookLM notebook to automate.
            port: The CDP port to connect to (default 9222).
        """
        self.notebook_url = notebook_url
        self.port = port
        self.playwright = None
        self.browser = None
        self.page = None
        self.lang = "en"
        self._chrome_manager = ChromeManager(port)
        self._source_manager: Optional[SourceManager] = None
        self._audio_manager: Optional[AudioManager] = None

    def connect(self) -> None:
        """Connect to the browser and navigate to the notebook."""
        if self.page and not self.page.is_closed():
            return

        if self.playwright:
            try:
                self.playwright.stop()
            except Exception:
                pass
            self.playwright = None

        self.playwright = sync_playwright().start()

        # Check if using WebSocket endpoint (browserless) or CDP
        ws_endpoint = os.getenv("BROWSER_WS_ENDPOINT")

        try:
            if ws_endpoint:
                # Connect via WebSocket (browserless/chrome)
                logger.info(f"Connecting to browserless via: {ws_endpoint}")

                # browserless exposes CDP at the base WebSocket URL
                # We need to use connect_over_cdp with the WebSocket URL directly
                # Format: ws://host:port -> connect_over_cdp expects this format
                self.browser = self.playwright.chromium.connect_over_cdp(
                    ws_endpoint, timeout=60000
                )
                logger.info("Successfully connected to browserless")

                # Set viewport size large enough for NotebookLM full layout
                # (requires width > 1051 for non-tab mode, height > 640 for audio visibility)
                context = self.browser.new_context(
                    viewport={"width": 1280, "height": 800}
                )
            else:
                # Connect via CDP (local Chrome)
                chrome_host = get_chrome_host()
                logger.info(f"Connecting to Chrome via CDP on {chrome_host}:{self.port}...")
                self._chrome_manager.ensure_running(chrome_host)
                self.browser = self.playwright.chromium.connect_over_cdp(
                    f"http://{chrome_host}:{self.port}"
                )
                context = self.browser.contexts[0]

            # Prefer existing NotebookLM page over creating new one (CDP mode only)
            existing_page = None
            if not ws_endpoint:
                for page in context.pages:
                    if "notebooklm.google.com" in page.url:
                        existing_page = page
                        break

            if existing_page:
                self.page = existing_page
                logger.info("Reusing existing NotebookLM page")
            else:
                # Inject auth state if needed
                # WebSocket mode: always inject (browserless has no persistent state)
                # CDP mode: only inject if Chrome doesn't have existing login state
                should_inject = ws_endpoint or not has_chrome_login_state()
                if should_inject:
                    auth_state = get_auth_state()
                    if auth_state:
                        try:
                            # auth_state can be a file path (str) or dict
                            if isinstance(auth_state, str):
                                # Load from file path
                                import json
                                with open(auth_state, "r") as f:
                                    state = json.load(f)
                            else:
                                state = auth_state

                            # Add cookies from storage state
                            cookies = state.get("cookies", [])
                            if cookies:
                                context.add_cookies(cookies)
                                logger.info(f"Injected {len(cookies)} cookies from storage state")
                        except Exception as e:
                            logger.warning(f"Failed to inject auth state: {e}")
                else:
                    logger.info("Chrome already has login state, skipping injection")

                self.page = context.new_page()
                self.page.set_viewport_size({"width": 1280, "height": 800})
                logger.info(f"Navigating to {self.notebook_url}...")
                self.page.goto(self.notebook_url, timeout=10000)
                try:
                    self.page.wait_for_load_state("networkidle", timeout=10000)
                except PlaywrightError:
                    logger.warning("Network idle timeout, continuing anyway...")

                # Handle Google account chooser if present
                self._handle_account_chooser()

            self._detect_language()
            self._init_managers()
            logger.info(f"Connected. Detected language: {self.lang}")

        except Exception as e:
            logger.error(f"Failed to connect: {e}")
            self.close()
            raise

    def ensure_connected(self) -> None:
        """Ensure the automation is connected to the browser."""
        try:
            if not self.page or self.page.is_closed():
                self.connect()
            else:
                self.page.evaluate("1+1")
        except Exception:
            logger.info("Connection lost, reconnecting...")
            self.connect()

    def save_login_state(self, path: Optional[str] = None) -> bool:
        """
        Save current browser login state to storage_state.json.

        This captures cookies and localStorage, which can be reused
        in future sessions to avoid re-login.

        Args:
            path: Optional path to save to (defaults to local/cookies/storage_state.json)

        Returns:
            True if saved successfully, False otherwise.
        """
        if not self.page or self.page.is_closed():
            logger.error("Cannot save login state: no active page")
            return False

        try:
            context = self.page.context
            state = context.storage_state()
            return save_storage_state(state, path)
        except Exception as e:
            logger.error(f"Failed to save login state: {e}")
            return False

    def close(self) -> None:
        """Close the connection and clean up resources."""
        try:
            if self.page:
                self.page.close()
        except Exception:
            pass

        try:
            if self.browser:
                self.browser.close()
        except Exception:
            pass

        try:
            if self.playwright:
                self.playwright.stop()
        except Exception:
            pass

        self.page = None
        self.browser = None
        self.playwright = None
        self._source_manager = None
        self._audio_manager = None
        self._chrome_manager.terminate()

    def _handle_account_chooser(self) -> None:
        """Handle Google account chooser page if present."""
        try:
            # Check if we're on an account chooser page
            if "accounts.google.com" not in self.page.url:
                return

            # Look for "Choose an account" text or similar
            choose_account = self.page.locator("text=Choose an account")
            if choose_account.count() == 0:
                return

            logger.info("Account chooser detected, selecting account...")

            # Get preferred account from env var
            preferred_account = os.getenv("GOOGLE_ACCOUNT_EMAIL")

            if preferred_account:
                # Click on the account with matching email
                # Google uses div[data-identifier] with role="link" for account items
                account_item = self.page.locator(
                    f"div[data-identifier='{preferred_account}']"
                ).first
                if account_item.count() > 0:
                    logger.info(f"Selecting account: {preferred_account}")
                    account_item.click()
                else:
                    # Fallback: try matching by email text in the list
                    account_item = self.page.locator(
                        f"li:has(div[data-email='{preferred_account}'])"
                    ).first
                    if account_item.count() > 0:
                        logger.info(f"Selecting account (fallback): {preferred_account}")
                        account_item.click()
                    else:
                        logger.warning(
                            f"Account {preferred_account} not found in chooser"
                        )
                        return
            else:
                # No preferred account, click the first available account
                # Account items are div elements with data-identifier attribute
                first_account = self.page.locator(
                    "div[data-identifier][role='link']"
                ).first
                if first_account.count() > 0:
                    logger.info("No preferred account set, selecting first account")
                    first_account.click()
                else:
                    logger.warning("No accounts found in chooser")
                    return

            # Wait for navigation after account selection
            self.page.wait_for_timeout(2000)
            try:
                self.page.wait_for_load_state("networkidle", timeout=10000)
            except PlaywrightError:
                pass

            logger.info(f"Account selected, now at: {self.page.url}")

        except Exception as e:
            logger.warning(f"Failed to handle account chooser: {e}")

    def _detect_language(self) -> None:
        """Detect the UI language from the page."""
        try:
            lang_attr = self.page.evaluate("document.documentElement.lang")
            if lang_attr:
                if lang_attr.startswith("he") or lang_attr.startswith("iw"):
                    self.lang = "he"
                elif lang_attr.startswith("zh"):
                    self.lang = "zh"
                elif lang_attr.startswith("ja"):
                    self.lang = "ja"
                else:
                    self.lang = "en"
        except Exception:
            self.lang = "en"

    def _get_text(self, key: str) -> str:
        """Get localized text for a selector key."""
        return get_selector_by_language(self.lang, key)

    def _init_managers(self) -> None:
        """Initialize source and audio managers after page is ready."""
        self._source_manager = SourceManager(self.page, self._get_text)
        self._audio_manager = AudioManager(self.page, self._get_text)

    def add_sources(self, sources: List[Dict[str, str]]) -> List[Dict[str, Any]]:
        """
        Add sources to the notebook.

        Args:
            sources: List of dicts with 'type' ('url', 'youtube', 'text') and 'content'.

        Returns:
            List of results for each source.
        """
        self.ensure_connected()
        return self._source_manager.add_sources(sources)

    def clear_sources(self) -> Dict[str, Any]:
        """
        Clear all sources from the notebook.

        Returns:
            Dict with 'success' and 'count' keys.
        """
        self.ensure_connected()
        return self._source_manager.clear_sources()

    def generate_audio(
        self,
        style: Optional[str] = None,
        prompt: Optional[str] = None,
        language: Optional[str] = None,
        duration: Optional[str] = None,
    ) -> str:
        """
        Generate an audio overview.

        Args:
            style: Optional style for the audio (e.g., 'deep_dive', 'summary').
            prompt: Optional prompt text for customization.
            language: Optional language selection.
            duration: Optional duration selection ('short' or 'default').

        Returns:
            Job ID string for tracking the generation.
        """
        self.ensure_connected()
        return self._audio_manager.generate(style, prompt, language, duration)

    def get_audio_status(self, job_id: str) -> Dict[str, str]:
        """
        Check the status of an audio generation job.

        Args:
            job_id: The job ID returned from generate_audio.

        Returns:
            Dict with 'status' key (generating, completed, failed, unknown).
        """
        self.ensure_connected()
        return self._audio_manager.get_status(job_id)

    def get_download_url(self, job_id: str) -> Optional[str]:
        """
        Get the direct download URL for generated audio.

        Args:
            job_id: The job ID returned from generate_audio.

        Returns:
            URL string or None if not available.
        """
        self.ensure_connected()
        return self._audio_manager.get_download_url(job_id)

    def download_audio_file(self, job_id: str) -> Optional[Tuple[bytes, str, int]]:
        """
        Download the audio file by clicking Download in the UI.

        Args:
            job_id: The job ID of the audio to download.

        Returns:
            Tuple of (file_content, file_name, file_size) or None if failed.
        """
        self.ensure_connected()
        return self._audio_manager.download_file(job_id)

    def clear_studio(self) -> Dict[str, Any]:
        """
        Delete all generated audio items.

        Returns:
            Dict with 'success', 'count', and optional 'message' keys.
        """
        self.ensure_connected()
        self._source_manager.close_dialog()
        return self._audio_manager.clear_studio()
