# NotebookLM Podcast Automator API

A FastAPI application to automate Google NotebookLM, allowing you to programmatically upload sources (URLs, YouTube, Text) and generate Audio Overviews (Podcasts).

## Features

- **Automated Source Management**: Upload URLs, YouTube videos, and text content directly to your notebook.
- **Audio Generation**: Trigger "Audio Overview" generation programmatically with custom prompts.
- **Status Monitoring**: Check generation status and retrieve download URLs.
- **Production Ready**: Built with FastAPI, Pydantic, and Playwright.
- **Language Support**: Automatically detects and supports English and Hebrew NotebookLM interfaces.

## Prerequisites

1.  **Google Chrome**: Must be installed and running with remote debugging enabled.
2.  **NotebookLM Notebook**: You need an existing notebook URL.
3.  **Python 3.10+**: Recommended.

## Installation

1.  Clone the repository:

    ```bash
    git clone <repository-url>
    cd notebooklm-podcast-automator
    ```

2.  Install dependencies:
    ```bash
    pip install -r requirements.txt
    playwright install chromium
    ```

## Usage

### 1. Chrome With Remote Debugging

The API now attempts to launch Chrome automatically with remote debugging enabled (default port `9222`). The first run creates a profile under `~/.notebooklm-chrome`; open the spawned browser window once and log in to Google NotebookLM so the session persists in that profile.

If you prefer to manage Chrome yourself (for example, to reuse an existing profile), set `NOTEBOOKLM_AUTO_LAUNCH_CHROME=0` and start Chrome manually with a debugging port:

**Mac:**

```bash
/Applications/Google\ Chrome.app/Contents/MacOS/Google\ Chrome --remote-debugging-port=9222 --user-data-dir=./chrome-data
```

**Windows:**

```powershell
& "C:\Program Files\Google\Chrome\Application\chrome.exe" --remote-debugging-port=9222 --user-data-dir="C:\selenium\ChromeProfile"
```

_Regardless of who launches Chrome, ensure you're logged into NotebookLM in that window before calling the API._

### 2. Start the API Server

Set your NotebookLM URL and start the server:

```bash
# Option 1: Environment Variable
export NOTEBOOKLM_URL="https://notebooklm.google.com/notebook/..."
uv run src/notebooklm_automator/main.py

# Option 2: Command Line Argument
uv run src/notebooklm_automator/main.py --notebook-url "https://notebooklm.google.com/notebook/..."
```

The API will be available at `http://localhost:8000`.
Docs are available at `http://localhost:8000/docs`.

### Chrome Launch Configuration

The following environment variables adjust how the browser is launched:

- `NOTEBOOKLM_AUTO_LAUNCH_CHROME` (default `1`): set to `0`/`false` to skip auto-launch and reuse an already-running Chrome instance.
- `NOTEBOOKLM_CHROME_PATH`: absolute path to the Chrome/Chromium executable if it is not on `PATH` or installed in a standard location.
- `NOTEBOOKLM_CHROME_USER_DATA_DIR` (default `~/.notebooklm-chrome`): directory used for the persistent Chrome profile that stores your Google login.
- `NOTEBOOKLM_CHROME_PORT` (default `9222`): remote debugging port used by the automator. Must match the `--remote-debugging-port` value if you launch Chrome yourself.
- `NOTEBOOKLM_CHROME_HOST` (default `127.0.0.1`): host interface for the debugging endpoint; useful if Chrome listens on a different interface.

## API Endpoints

### Upload Sources

`POST /sources/upload`

```json
{
  "sources": [
    { "type": "url", "content": "https://example.com" },
    { "type": "youtube", "content": "https://youtu.be/..." },
    { "type": "text", "content": "Paste your text here..." }
  ]
}
```

### Generate Audio

`POST /audio/generate`

```json
{
  "style": "deep_dive",
  "prompt": "Focus on the technical details."
}
```

### Check Status

`GET /audio/status/{job_id}`

### Download Audio

`GET /audio/download/{job_id}`

### Clear Sources

`POST /sources/clear`

## Testing

Run the automated tests:

```bash
uv run pytest tests/test_api.py
```
