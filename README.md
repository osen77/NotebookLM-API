# NotebookLM Podcast Automator

Automate Google NotebookLM with a small FastAPI service and Playwright. Upload sources (URLs, YouTube videos, or raw text), generate Audio Overviews, and retrieve the finished files programmatically—no manual clicking through the UI.

---

## Key Features
- Upload multiple source types (URL, YouTube, text) into a notebook via REST.
- Trigger Audio Overview generation with optional style and prompt overrides.
- Track generation status and fetch download URLs or the binary audio file.
- Handles English and Hebrew NotebookLM interfaces automatically.
- Can auto-launch Chrome with a dedicated profile or attach to an existing debug session.

---

## Architecture At A Glance
- **FastAPI app** (`notebooklm_automator.api.app`) exposes REST endpoints in `api/routes.py`.
- **NotebookLMAutomator** (`core/automator.py`) orchestrates Playwright, manages language detection, and delegates to feature managers.
- **Browser control** (`core/browser.py`) handles Chrome remote-debugging and profile management.
- **Sources & audio managers** (`core/sources.py`, `core/audio.py`) interact with the NotebookLM UI to add sources, generate audio, and fetch downloads.
- **Selectors** (`core/selectors.py`) provide localized UI selectors for supported languages.

---

## Prerequisites
- Python 3.9+
- Google Chrome or Chromium with remote debugging enabled
- A NotebookLM account and an existing notebook URL
- `uv` (optional but recommended for reproducible installs)

---

## Installation
From the repository root:

### Using uv (recommended)
```bash
uv sync
uv run playwright install chromium
```

### Using pip
```bash
pip install -e .
playwright install chromium
```

---

## Running Locally
1. Create a `.env` file or export the notebook URL:
   - `NOTEBOOKLM_URL="https://notebooklm.google.com/notebook/<YOUR_ID>"`
2. First run: the service will open a Chrome profile at `~/.notebooklm-chrome`. Log in to your Google account in that window so the session persists.
3. Start the API:
   ```bash
   uv run run-server
   # or override via CLI
   uv run run-server --notebook-url "https://notebooklm.google.com/notebook/<YOUR_ID>"
   ```

The API serves at `http://localhost:8000` with Swagger UI at `/docs`.

### Docker
```bash
docker build -t notebooklm-podcast-automator .
docker run -p 8080:8080 -e NOTEBOOKLM_URL="https://notebooklm.google.com/notebook/<YOUR_ID>" notebooklm-podcast-automator
```

---

## Configuration
All values can come from environment variables or `.env`:

| Variable | Default | Purpose |
| --- | --- | --- |
| `NOTEBOOKLM_URL` | _(required)_ | NotebookLM notebook URL the automator should open. |
| `NOTEBOOKLM_AUTO_LAUNCH_CHROME` | `1` | Set to `0` to attach to an already running Chrome with remote debugging. |
| `NOTEBOOKLM_CHROME_PATH` | auto-detect | Path to Chrome/Chromium binary. |
| `NOTEBOOKLM_CHROME_USER_DATA_DIR` | `~/.notebooklm-chrome` | Profile used to persist your NotebookLM login. |
| `NOTEBOOKLM_CHROME_PORT` | `9222` | Remote debugging port. |
| `NOTEBOOKLM_CHROME_HOST` | `127.0.0.1` | Host interface for CDP connection. |

Manual Chrome launch (if you set `NOTEBOOKLM_AUTO_LAUNCH_CHROME=0`):
```bash
# macOS
/Applications/Google\ Chrome.app/Contents/MacOS/Google\ Chrome \
  --remote-debugging-port=9222 \
  --user-data-dir="$HOME/.notebooklm-chrome"

# Windows (PowerShell)
& "C:\Program Files\Google\Chrome\Application\chrome.exe" `
  --remote-debugging-port=9222 `
  --user-data-dir="$env:USERPROFILE\.notebooklm-chrome"

# Linux
google-chrome --remote-debugging-port=9222 --user-data-dir="$HOME/.notebooklm-chrome"
```

---

## Common Pitfalls & Troubleshooting
- **Not logged in:** Ensure the Chrome profile (`NOTEBOOKLM_CHROME_USER_DATA_DIR`) is signed into your Google account before calling the API.
- **Port already in use:** Change `NOTEBOOKLM_CHROME_PORT` (and matching manual Chrome launch) if another process is using 9222.
- **Download failures:** The API sanitizes filenames, but Chrome still needs download permission in the profile directory. Clear blocked downloads and retry.
- **Tests endpoint:** The `/run-tests` route expects local test files. This repository snapshot does not include the test suite; add your own tests before invoking it.

---

## Future Improvements
- Re-introduce and publish the automated test suite with CI coverage.
- Add health checks for Chrome connectivity and clearer API error payloads.
- Ship a published container image for easier deployment.

---

## License
MIT license. See `LICENSE` for details.
