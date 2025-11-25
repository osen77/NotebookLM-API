# NotebookLM Podcast Automator

[![Python 3.9+](https://img.shields.io/badge/python-3.9%2B-blue.svg)](https://www.python.org/downloads/)
[![FastAPI](https://img.shields.io/badge/FastAPI-0.109%2B-009688.svg)](https://fastapi.tiangolo.com)
[![Playwright](https://img.shields.io/badge/Playwright-1.40%2B-2EAD33.svg)](https://playwright.dev/python/)
[![License: MIT](https://img.shields.io/badge/License-MIT-yellow.svg)](LICENSE)

Automate Google NotebookLM through a REST API. Upload sources (URLs, YouTube videos, text) and generate AI-powered Audio Overviews (podcasts) programmatically—no manual clicking required.

---

## ✨ Features

- **Source Management** — Upload URLs, YouTube videos, and text content to your notebook via API
- **Audio Generation** — Trigger Audio Overview creation with custom styles and prompts
- **Multiple Styles** — Choose from Deep Dive, Summary, Critique, or Debate formats
- **Status Tracking** — Monitor generation progress and retrieve download URLs
- **Multi-language UI** — Supports English and Hebrew NotebookLM interfaces automatically
- **Auto Chrome Launch** — Optionally spawns and manages Chrome with remote debugging
- **Comprehensive Tests** — Unit, API, UI, and E2E test suites included

---

## 📋 Prerequisites

| Requirement            | Notes                                      |
| ---------------------- | ------------------------------------------ |
| **Python 3.9+**        | Tested on 3.9, 3.10, 3.11                  |
| **Google Chrome**      | Or Chromium; used via remote debugging     |
| **NotebookLM Account** | You need an existing notebook URL          |
| **uv** _(optional)_    | Recommended for fast dependency management |

---

## 🚀 Quick Start

### 1. Clone & Install

```bash
git clone https://github.com/your-username/notebooklm-podcast-automator.git
cd notebooklm-podcast-automator

# Using uv (recommended)
uv sync
uv run playwright install chromium

# Or using pip
pip install -e ".[test]"
playwright install chromium
```

### 2. First-Time Setup

On the first run, the automator launches Chrome with a dedicated profile (`~/.notebooklm-chrome`). **Log in to your Google account** in that browser window so the session persists for future API calls.

### 3. Start the Server

```bash
# Set your notebook URL and run
export NOTEBOOKLM_URL="https://notebooklm.google.com/notebook/YOUR_NOTEBOOK_ID"
uv run run-server

# Or pass the URL directly
uv run run-server --notebook-url "https://notebooklm.google.com/notebook/..."
```

The API is now live at **http://localhost:8000** with interactive docs at **/docs**.

---

## 🔧 Configuration

All settings can be controlled via environment variables or a `.env` file:

| Variable                          | Default                | Description                                          |
| --------------------------------- | ---------------------- | ---------------------------------------------------- |
| `NOTEBOOKLM_URL`                  | —                      | **(Required)** Full URL to your NotebookLM notebook  |
| `NOTEBOOKLM_AUTO_LAUNCH_CHROME`   | `1`                    | Set to `0` to use an already-running Chrome instance |
| `NOTEBOOKLM_CHROME_PATH`          | auto-detect            | Path to Chrome/Chromium executable                   |
| `NOTEBOOKLM_CHROME_USER_DATA_DIR` | `~/.notebooklm-chrome` | Chrome profile directory for persistent login        |
| `NOTEBOOKLM_CHROME_PORT`          | `9222`                 | Remote debugging port                                |
| `NOTEBOOKLM_CHROME_HOST`          | `127.0.0.1`            | Host interface for CDP connection                    |

### Manual Chrome Launch

If you prefer to manage Chrome yourself:

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

Then set `NOTEBOOKLM_AUTO_LAUNCH_CHROME=0` before starting the API.

---

## 📡 API Reference

### Health Check

```http
GET /health
```

Returns `{"status": "ok"}` when the server is running.

---

### Upload Sources

```http
POST /sources/upload
Content-Type: application/json

{
  "sources": [
    {"type": "url", "content": "https://example.com/article"},
    {"type": "youtube", "content": "https://www.youtube.com/watch?v=dQw4w9WgXcQ"},
    {"type": "text", "content": "Your custom text content here..."}
  ]
}
```

**Source Types:**

- `url` — Web page URL
- `youtube` — YouTube video URL
- `text` — Raw text content

---

### Clear Sources

```http
POST /sources/clear
```

Removes all sources from the notebook.

---

### Generate Audio

```http
POST /audio/generate
Content-Type: application/json

{
  "style": "deep_dive",
  "prompt": "Focus on the technical implementation details",
  "language": "English"
}
```

**Available Styles:**
| Style | Description |
|-------|-------------|
| `deep_dive` | In-depth conversational exploration (default) |
| `summary` | Concise overview of key points |
| `criticism` | Critical analysis perspective |
| `debate` | Multiple viewpoints discussion |

**Returns:** `{"job_id": "...", "status": "started"}`

---

### Check Audio Status

```http
GET /audio/status/{job_id}
```

**Response:**

```json
{
  "job_id": "01HXYZ...",
  "status": "completed",
  "download_url": "https://..."
}
```

**Status Values:** `generating`, `completed`, `failed`, `unknown`

---

### Get Download URL

```http
GET /audio/file/{job_id}
```

Returns the direct download URL for completed audio.

---

### Clear Studio

```http
POST /studio/clear
```

Deletes all generated audio items from the Studio panel.

---

### Run Tests

```http
POST /run-tests?test_type=all&verbose=false
```

**Test Types:** `unit`, `api`, `ui`, `e2e`, `all`

---

## 🧪 Testing

```bash
# Run all tests
uv run pytest

# Run specific test suites
uv run pytest tests/unit/          # Unit tests (fast, no browser)
uv run pytest tests/api/           # API route tests
uv run pytest tests/ui/            # UI automation tests
uv run pytest tests/e2e/           # End-to-end tests (requires NOTEBOOKLM_URL)

# With coverage
uv run pytest --cov=src/notebooklm_automator --cov-report=html

# Or use the test runner script
uv run python run_tests.py --type all --verbose
```

---

## 📁 Project Structure

```
notebooklm-podcast-automator/
├── src/notebooklm_automator/
│   ├── api/
│   │   ├── app.py          # FastAPI application
│   │   ├── routes.py       # API endpoints
│   │   └── models.py       # Pydantic schemas
│   ├── core/
│   │   ├── automator.py    # Main orchestrator
│   │   ├── browser.py      # Chrome/CDP management
│   │   ├── sources.py      # Source upload logic
│   │   ├── audio.py        # Audio generation logic
│   │   └── selectors.py    # Localized UI selectors
│   └── main.py             # CLI entry point
├── tests/
│   ├── unit/               # Unit tests
│   ├── api/                # API integration tests
│   ├── ui/                 # UI automation tests
│   └── e2e/                # End-to-end tests
├── pyproject.toml          # Project configuration
└── README.md
```

---

## 🤝 Contributing

Contributions are welcome! Please:

1. Fork the repository
2. Create a feature branch (`git checkout -b feature/amazing-feature`)
3. Run tests (`uv run pytest`)
4. Commit your changes (`git commit -m 'Add amazing feature'`)
5. Push to the branch (`git push origin feature/amazing-feature`)
6. Open a Pull Request

---

## ⚠️ Disclaimer

This project automates interactions with Google NotebookLM through browser automation. It is not affiliated with, endorsed by, or officially supported by Google. Use responsibly and in accordance with Google's Terms of Service.

---

## 📄 License

This project is licensed under the MIT License — see the [LICENSE](LICENSE) file for details.
