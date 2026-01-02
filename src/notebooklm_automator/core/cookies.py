"""Cookie and storage state utilities for NotebookLM Automator."""

import json
import logging
import os
from pathlib import Path
from typing import Any, Dict, List, Optional, Union

logger = logging.getLogger(__name__)

# Storage state file name (Playwright JSON format)
STORAGE_STATE_FILE = "storage_state.json"

# CookieCloud JSON file name
COOKIECLOUD_FILE = "cookie.json"


def parse_cookies_txt(file_path: str) -> List[Dict[str, Any]]:
    """
    Parse Netscape cookies.txt format and return Playwright-compatible cookies.

    Args:
        file_path: Path to the cookies.txt file.

    Returns:
        List of cookie dicts in Playwright format.

    Netscape cookies.txt format (tab-separated):
        domain, include_subdomains, path, secure, expiration, name, value
    """
    cookies = []
    path = Path(file_path)

    if not path.exists():
        logger.warning(f"Cookies file not found: {file_path}")
        return []

    try:
        with open(path, "r", encoding="utf-8") as f:
            for line in f:
                line = line.strip()
                # Skip empty lines and comments
                if not line or line.startswith("#"):
                    continue

                parts = line.split("\t")
                if len(parts) < 7:
                    continue

                domain, _flag, cookie_path, secure, expiration, name, value = parts[:7]

                # Only include Google-related cookies
                # Include all google.com subdomains (accounts, notebooklm, etc.)
                if not (
                    "google.com" in domain
                    or "google." in domain
                    or "gstatic.com" in domain
                    or "googleapis.com" in domain
                    or "youtube.com" in domain
                ):
                    continue

                cookie = {
                    "name": name,
                    "value": value,
                    "domain": domain,
                    "path": cookie_path,
                    "secure": secure.upper() == "TRUE",
                    "httpOnly": False,  # Cannot be determined from cookies.txt
                }

                # Add expiration if valid (0 means session cookie)
                try:
                    exp = int(expiration)
                    if exp > 0:
                        cookie["expires"] = exp
                except ValueError:
                    pass

                cookies.append(cookie)

        logger.info(f"Parsed {len(cookies)} cookies from {file_path}")
        return cookies

    except Exception as e:
        logger.warning(f"Failed to parse cookies file: {e}")
        return []


def has_chrome_login_state() -> bool:
    """
    Check if Chrome user data directory already has login state.

    Returns:
        True if Chrome Cookies database exists, False otherwise.
    """
    user_data_dir = os.getenv("NOTEBOOKLM_CHROME_USER_DATA_DIR")
    if not user_data_dir:
        user_data_dir = str(Path.home() / ".notebooklm-chrome")

    # Chrome stores cookies in Default/Cookies (SQLite database)
    cookies_db = Path(user_data_dir) / "Default" / "Cookies"
    if cookies_db.exists():
        logger.debug(f"Chrome login state found: {cookies_db}")
        return True

    return False


def get_default_cookies_dir() -> Path:
    """Get the default cookies directory path (project_root/local/cookies)."""
    # Navigate from this file to project root: core -> notebooklm_automator -> src -> project_root
    project_root = Path(__file__).parent.parent.parent.parent
    return project_root / "local" / "cookies"


def find_cookies_file() -> Optional[str]:
    """
    Find cookies file with priority:
    1. NOTEBOOKLM_COOKIES_FILE env var (--cookies-file argument)
    2. Default directory (local/cookies/cookies.txt)

    Returns:
        Path to cookies file or None if not found.
    """
    # Priority 1: env var (from --cookies-file)
    cookies_file = os.getenv("NOTEBOOKLM_COOKIES_FILE")
    if cookies_file:
        if Path(cookies_file).exists():
            logger.info(f"Using cookies file from argument: {cookies_file}")
            return cookies_file
        else:
            logger.warning(f"Cookies file from argument not found: {cookies_file}")

    # Priority 2: default directory
    default_file = get_default_cookies_dir() / "cookies.txt"
    if default_file.exists():
        logger.info(f"Using cookies file from default location: {default_file}")
        return str(default_file)

    return None


def get_cookies_from_env() -> Optional[List[Dict[str, Any]]]:
    """
    Get cookies from file with fallback priority.

    Priority:
    1. --cookies-file argument (NOTEBOOKLM_COOKIES_FILE env var)
    2. Default location (local/cookies/cookies.txt)
    3. Manual login (returns None)

    Returns:
        List of cookies or None if not found.
    """
    cookies_file = find_cookies_file()
    if not cookies_file:
        return None

    cookies = parse_cookies_txt(cookies_file)
    if not cookies:
        return None

    return cookies


def parse_cookiecloud_json(file_path: str) -> List[Dict[str, Any]]:
    """
    Parse CookieCloud JSON format and return Playwright-compatible cookies.

    CookieCloud format:
    [
      {
        "data": {
          "domain.com": [
            {
              "domain": ".domain.com",
              "name": "cookie_name",
              "value": "cookie_value",
              "expirationDate": 1234567890.123,
              "path": "/",
              "secure": true,
              "httpOnly": false,
              "sameSite": "lax"
            }
          ]
        }
      }
    ]

    Args:
        file_path: Path to the cookie.json file.

    Returns:
        List of cookie dicts in Playwright format.
    """
    cookies = []
    path = Path(file_path)

    if not path.exists():
        logger.warning(f"CookieCloud file not found: {file_path}")
        return []

    try:
        with open(path, "r", encoding="utf-8") as f:
            data = json.load(f)

        # CookieCloud format: array with data object
        if not isinstance(data, list) or len(data) == 0:
            logger.warning("Invalid CookieCloud format: expected non-empty array")
            return []

        cookie_data = data[0].get("data", {})
        if not cookie_data:
            logger.warning("No cookie data found in CookieCloud file")
            return []

        # Iterate through all domains
        for domain_key, domain_cookies in cookie_data.items():
            for cc_cookie in domain_cookies:
                domain = cc_cookie.get("domain", "")

                # Only include Google-related cookies
                if not (
                    "google.com" in domain
                    or "google." in domain
                    or "gstatic.com" in domain
                    or "googleapis.com" in domain
                    or "youtube.com" in domain
                ):
                    continue

                # Convert to Playwright format
                cookie = {
                    "name": cc_cookie.get("name", ""),
                    "value": cc_cookie.get("value", ""),
                    "domain": domain,
                    "path": cc_cookie.get("path", "/"),
                    "secure": cc_cookie.get("secure", False),
                    "httpOnly": cc_cookie.get("httpOnly", False),
                }

                # Handle expiration (CookieCloud uses expirationDate as float)
                exp_date = cc_cookie.get("expirationDate")
                if exp_date and exp_date > 0:
                    cookie["expires"] = int(exp_date)

                # Handle sameSite
                # CookieCloud uses: "strict", "lax", "no_restriction", "unspecified"
                # Playwright expects: "Strict", "Lax", "None"
                same_site = cc_cookie.get("sameSite", "").lower()
                if same_site == "strict":
                    cookie["sameSite"] = "Strict"
                elif same_site == "lax":
                    cookie["sameSite"] = "Lax"
                elif same_site in ("none", "no_restriction"):
                    cookie["sameSite"] = "None"
                # "unspecified" -> don't set sameSite (browser default)

                cookies.append(cookie)

        logger.info(f"Parsed {len(cookies)} cookies from CookieCloud file: {file_path}")
        return cookies

    except Exception as e:
        logger.warning(f"Failed to parse CookieCloud file: {e}")
        return []


def find_cookiecloud_file() -> Optional[str]:
    """
    Find CookieCloud JSON file with priority:
    1. COOKIECLOUD_FILE env var
    2. Default directory (local/cookies/cookie.json)

    Returns:
        Path to cookie.json file or None if not found.
    """
    # Priority 1: env var
    cookiecloud_file = os.getenv("COOKIECLOUD_FILE")
    if cookiecloud_file:
        if Path(cookiecloud_file).exists():
            logger.info(f"Using CookieCloud file from env: {cookiecloud_file}")
            return cookiecloud_file
        else:
            logger.warning(f"CookieCloud file from env not found: {cookiecloud_file}")

    # Priority 2: default directory
    default_file = get_default_cookies_dir() / COOKIECLOUD_FILE
    logger.debug(f"Checking CookieCloud file at: {default_file}")
    if default_file.exists():
        logger.info(f"Using CookieCloud file from default location: {default_file}")
        return str(default_file)

    logger.debug(f"CookieCloud file not found at default location: {default_file}")
    return None


def get_cookies_from_cookiecloud() -> Optional[List[Dict[str, Any]]]:
    """
    Get cookies from CookieCloud JSON file.

    Returns:
        List of cookies or None if not found.
    """
    cookiecloud_file = find_cookiecloud_file()
    if not cookiecloud_file:
        return None

    cookies = parse_cookiecloud_json(cookiecloud_file)
    if not cookies:
        return None

    return cookies


def get_storage_state_path() -> Path:
    """Get the path to storage_state.json file."""
    return get_default_cookies_dir() / STORAGE_STATE_FILE


def find_storage_state() -> Optional[str]:
    """
    Find storage state file with priority:
    1. NOTEBOOKLM_STORAGE_STATE env var
    2. Default directory (local/cookies/storage_state.json)

    Returns:
        Path to storage state file or None if not found.
    """
    # Priority 1: env var
    storage_state = os.getenv("NOTEBOOKLM_STORAGE_STATE")
    if storage_state and Path(storage_state).exists():
        logger.info(f"Using storage state from env: {storage_state}")
        return storage_state

    # Priority 2: default directory
    default_file = get_storage_state_path()
    if default_file.exists():
        logger.info(f"Using storage state from default location: {default_file}")
        return str(default_file)

    return None


def load_storage_state() -> Optional[Dict[str, Any]]:
    """
    Load storage state from JSON file.

    Returns:
        Storage state dict or None if not found/invalid.
    """
    storage_path = find_storage_state()
    if not storage_path:
        return None

    try:
        with open(storage_path, "r", encoding="utf-8") as f:
            state = json.load(f)
            cookie_count = len(state.get("cookies", []))
            origin_count = len(state.get("origins", []))
            logger.info(
                f"Loaded storage state: {cookie_count} cookies, "
                f"{origin_count} origins"
            )
            return state
    except Exception as e:
        logger.warning(f"Failed to load storage state: {e}")
        return None


def save_storage_state(state: Dict[str, Any], path: Optional[str] = None) -> bool:
    """
    Save storage state to JSON file.

    Args:
        state: Storage state dict from context.storage_state()
        path: Optional path to save to (defaults to local/cookies/storage_state.json)

    Returns:
        True if saved successfully, False otherwise.
    """
    if path is None:
        save_path = get_storage_state_path()
    else:
        save_path = Path(path)

    try:
        # Ensure directory exists
        save_path.parent.mkdir(parents=True, exist_ok=True)

        with open(save_path, "w", encoding="utf-8") as f:
            json.dump(state, f, indent=2)

        cookie_count = len(state.get("cookies", []))
        logger.info(f"Saved storage state ({cookie_count} cookies) to {save_path}")
        return True
    except Exception as e:
        logger.error(f"Failed to save storage state: {e}")
        return False


def cookies_to_storage_state(cookies: List[Dict[str, Any]]) -> Dict[str, Any]:
    """
    Convert cookies list to storage state format.

    Args:
        cookies: List of Playwright-compatible cookies

    Returns:
        Storage state dict with cookies and empty origins
    """
    return {
        "cookies": cookies,
        "origins": []
    }


def get_auth_state() -> Optional[Union[str, Dict[str, Any]]]:
    """
    Get authentication state with priority:
    1. Storage state JSON file (includes localStorage)
    2. CookieCloud JSON file (cookie.json)
    3. Cookies.txt (Netscape format)
    4. None (manual login required)

    Returns:
        Path to storage state file, storage state dict, or None.
    """
    # Priority 1: existing storage state file
    storage_path = find_storage_state()
    if storage_path:
        logger.info(f"Auth source: storage_state.json ({storage_path})")
        return storage_path

    # Priority 2: CookieCloud JSON file
    cookies = get_cookies_from_cookiecloud()
    if cookies:
        logger.info(f"Auth source: cookie.json (CookieCloud) - {len(cookies)} cookies")
        return cookies_to_storage_state(cookies)

    # Priority 3: convert cookies.txt to storage state
    cookies = get_cookies_from_env()
    if cookies:
        logger.info(f"Auth source: cookies.txt - {len(cookies)} cookies")
        return cookies_to_storage_state(cookies)

    logger.warning("No auth source found (storage_state.json, cookie.json, or cookies.txt)")
    return None
