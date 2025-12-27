"""API routes for NotebookLM Automator."""

import os
import subprocess

from fastapi import APIRouter, Depends, HTTPException, Response

from notebooklm_automator.api.models import (
    AudioStatusResponse,
    ClearSourcesResponse,
    ClearStudioResponse,
    GenerateAudioRequest,
    GenerateAudioResponse,
    SourceResult,
    UploadResponse,
    UploadSourcesRequest,
)
from notebooklm_automator.core.automator import NotebookLMAutomator


router = APIRouter()

_automator_instance: NotebookLMAutomator = None


def get_automator() -> NotebookLMAutomator:
    """Get or create the automator instance."""
    global _automator_instance
    if not _automator_instance:
        url = os.getenv("NOTEBOOKLM_URL")
        if not url:
            raise HTTPException(
                status_code=500,
                detail="NOTEBOOKLM_URL environment variable not set",
            )
        port = int(os.getenv("NOTEBOOKLM_CHROME_PORT", "9222"))
        _automator_instance = NotebookLMAutomator(notebook_url=url, port=port)
        try:
            _automator_instance.connect()
        except Exception as e:
            raise HTTPException(
                status_code=500,
                detail=f"Failed to connect to NotebookLM: {str(e)}",
            )
    return _automator_instance


@router.get("/debug/status")
def debug_status(automator: NotebookLMAutomator = Depends(get_automator)):
    """Debug endpoint to check current page status."""
    try:
        automator.ensure_connected()
        page = automator.page
        url = page.url if page else "No page"
        title = page.title() if page else "No title"

        # Count audio items with detailed debug info
        audio_count = 0
        artifact_library_exists = False
        artifact_library_html = ""
        debug_info = {}

        try:
            # Debug: Check if Studio tab exists using different selectors
            studio_text = automator._get_text("studio_tab")
            debug_info["studio_tab_text"] = studio_text

            # Check various tab selectors
            mat_tab = page.locator(f".mat-mdc-tab:has-text('{studio_text}')").first
            role_tab = page.locator(f"[role='tab']:has-text('{studio_text}')").first
            text_match = page.get_by_text(studio_text, exact=True).first

            debug_info["studio_tab_selectors"] = {
                "mat_mdc_tab": mat_tab.count() > 0,
                "role_tab": role_tab.count() > 0,
                "text_match": text_match.count() > 0,
            }

            # Ensure we're on Studio tab before checking audio elements
            automator._audio_manager._ensure_studio_tab()

            # Check if artifact-library exists
            parent = page.locator("artifact-library")
            artifact_library_exists = parent.count() > 0

            if artifact_library_exists:
                children = parent.locator(":scope > *")
                audio_count = children.count()
                # Get first 500 chars of inner HTML for debugging
                try:
                    artifact_library_html = parent.inner_html()[:500]
                except Exception:
                    artifact_library_html = "Could not get HTML"

            # Try alternative selectors
            alt_selectors = {
                ".artifact-library-container": page.locator(".artifact-library-container").count(),
                "[class*='artifact']": page.locator("[class*='artifact']").count(),
                "[class*='audio']": page.locator("[class*='audio']").count(),
                "mat-icon:has-text('play_arrow')": page.locator("mat-icon:has-text('play_arrow')").count(),
                # Additional selectors for debugging
                "[class*='studio']": page.locator("[class*='studio']").count(),
                "[class*='overview']": page.locator("[class*='overview']").count(),
                "button": page.locator("button").count(),
            }
            debug_info["alternative_selectors"] = alt_selectors

            # Get body text snippet for context
            try:
                body_text = page.locator("body").inner_text()[:1000]
                debug_info["page_text_preview"] = body_text
            except Exception:
                pass

            # Get viewport size for debugging layout issues
            try:
                viewport = page.viewport_size
                debug_info["viewport"] = viewport
            except Exception:
                pass

        except Exception as e:
            debug_info["selector_error"] = str(e)

        return {
            "connected": True,
            "page_url": url,
            "page_title": title,
            "audio_items_count": audio_count,
            "artifact_library_exists": artifact_library_exists,
            "artifact_library_html_preview": artifact_library_html,
            "language": automator.lang,
            "debug_info": debug_info,
        }
    except Exception as e:
        return {
            "connected": False,
            "error": str(e),
        }


@router.get("/debug/screenshot")
def debug_screenshot(
    save: bool = False,
    automator: NotebookLMAutomator = Depends(get_automator),
):
    """Take a screenshot of current page for debugging.

    Args:
        save: If True, save to /app/local/cookies/screenshot.png (viewable on host)
    """
    try:
        automator.ensure_connected()
        screenshot = automator.page.screenshot(full_page=False)

        if save:
            # Save to mounted volume for viewing on host
            save_path = "/app/local/cookies/screenshot.png"
            with open(save_path, "wb") as f:
                f.write(screenshot)
            return {"saved": True, "path": save_path, "size": len(screenshot)}

        return Response(
            content=screenshot,
            media_type="image/png",
            headers={"Content-Disposition": "inline; filename=debug.png"},
        )
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/sources/upload", response_model=UploadResponse)
def upload_sources(
    request: UploadSourcesRequest,
    automator: NotebookLMAutomator = Depends(get_automator),
):
    """Upload one or more sources to the notebook."""
    sources_data = [s.model_dump() for s in request.sources]
    results_data = automator.add_sources(sources_data)

    results = [SourceResult(**r) for r in results_data]
    overall_success = all(r.success for r in results)
    return UploadResponse(overall_success=overall_success, results=results)


@router.post("/sources/clear", response_model=ClearSourcesResponse)
def clear_sources(automator: NotebookLMAutomator = Depends(get_automator)):
    """Clear all sources from the notebook."""
    result = automator.clear_sources()
    return ClearSourcesResponse(
        success=result.get("success", False),
        count=result.get("count", 0),
        message=result.get("message"),
    )


@router.post("/audio/generate", response_model=GenerateAudioResponse)
def generate_audio(
    request: GenerateAudioRequest,
    automator: NotebookLMAutomator = Depends(get_automator),
):
    """Trigger audio generation."""
    try:
        job_id = automator.generate_audio(
            style=request.style.value if request.style else None,
            language=request.language,
            prompt=request.prompt,
            duration=request.duration.value if request.duration else None,
        )
        return GenerateAudioResponse(job_id=job_id, status="started")
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/audio/status/{job_id}", response_model=AudioStatusResponse)
def check_audio_status(
    job_id: str,
    automator: NotebookLMAutomator = Depends(get_automator),
):
    """Check the status of audio generation."""
    status_data = automator.get_audio_status(job_id)

    download_url = None
    if status_data["status"] == "completed":
        download_url = automator.get_download_url(job_id)

    return AudioStatusResponse(
        job_id=job_id,
        status=status_data["status"],
        title=status_data.get("title"),
        download_url=download_url,
    )


@router.get("/audio/file/{job_id}")
def get_audio_download_url(
    job_id: str,
    automator: NotebookLMAutomator = Depends(get_automator),
):
    """Return the direct download URL for generated audio."""
    status_data = automator.get_audio_status(job_id)
    if status_data["status"] != "completed":
        raise HTTPException(
            status_code=400,
            detail="Audio generation not completed or failed",
        )

    url = automator.get_download_url(job_id)
    if not url:
        raise HTTPException(
            status_code=500,
            detail="Could not retrieve download URL",
        )

    return {"url": url}


@router.get("/audio/download/{job_id}")
def download_audio_file(
    job_id: str,
    automator: NotebookLMAutomator = Depends(get_automator),
):
    """Download audio file as binary data.

    Returns the actual audio file content as binary data.
    In browserless mode, downloads via HTTP from the captured URL.
    In CDP mode, uses filesystem-based download.
    """
    import requests
    from urllib.parse import quote

    status_data = automator.get_audio_status(job_id)

    if status_data["status"] != "completed":
        raise HTTPException(
            status_code=400,
            detail="Audio generation not completed or failed",
        )

    # Check if using browserless (WebSocket) mode
    ws_endpoint = os.getenv("BROWSER_WS_ENDPOINT")

    if ws_endpoint:
        # Browserless mode: download via HTTP from captured URL
        url = automator.get_download_url(job_id)
        if not url:
            raise HTTPException(
                status_code=500,
                detail="Could not retrieve download URL",
            )

        try:
            resp = requests.get(url, timeout=120)
            resp.raise_for_status()
            content = resp.content
            file_size = len(content)
            # Extract filename from URL or use default
            file_name = f"audio_{job_id}.mp4"
        except Exception as e:
            raise HTTPException(
                status_code=500,
                detail=f"Failed to download audio from URL: {str(e)}",
            )
    else:
        # CDP mode: download by clicking Download button in UI
        result = automator.download_audio_file(job_id)

        if not result:
            raise HTTPException(
                status_code=500,
                detail="Failed to download audio file",
            )

        content, file_name, file_size = result

    encoded_filename = quote(file_name, safe='')

    # Provide both ASCII fallback and UTF-8 encoded filename
    content_disposition = (
        f"attachment; filename=\"{encoded_filename}\"; "
        f"filename*=UTF-8''{encoded_filename}"
    )

    return Response(
        content=content,
        media_type="audio/mp4",
        headers={
            "Content-Disposition": content_disposition,
            "Content-Length": str(file_size),
        },
    )


@router.post("/studio/clear", response_model=ClearStudioResponse)
def clear_studio(automator: NotebookLMAutomator = Depends(get_automator)):
    """Delete all generated audio items."""
    result = automator.clear_studio()
    return ClearStudioResponse(
        success=result.get("success", False),
        count=result.get("count", 0),
        message=result.get("message"),
    )


# Test type to directory mapping
TEST_PATHS = {
    "unit": "tests/unit/",
    "api": "tests/api/",
    "ui": "tests/ui/",
    "e2e": "tests/e2e/",
    "all": "tests/",
}


@router.post("/run-tests")
def run_tests(test_type: str = "all", verbose: bool = False):
    """Trigger the test suite.

    Args:
        test_type: Type of tests to run (unit, api, ui, e2e, all). Default: all
        verbose: Enable verbose output. Default: False

    Returns:
        JSON with success status, output, errors, and test summary.
    """
    if test_type not in TEST_PATHS:
        raise HTTPException(
            status_code=400,
            detail=f"Invalid test_type. Must be one of: {', '.join(TEST_PATHS.keys())}",
        )

    test_path = TEST_PATHS[test_type]

    # Build pytest command
    cmd = ["python", "-m", "pytest", test_path]
    if verbose:
        cmd.append("-v")

    try:
        result = subprocess.run(
            cmd,
            capture_output=True,
            text=True,
            timeout=300,  # 5 minute timeout
        )

        # Parse test summary from output
        summary = _parse_test_summary(result.stdout)

        return {
            "success": result.returncode == 0,
            "test_type": test_type,
            "exit_code": result.returncode,
            "summary": summary,
            "output": result.stdout,
            "error": result.stderr if result.stderr else None,
        }
    except subprocess.TimeoutExpired:
        raise HTTPException(
            status_code=504,
            detail="Test execution timed out after 5 minutes",
        )
    except Exception as e:
        raise HTTPException(
            status_code=500,
            detail=f"Failed to run tests: {str(e)}",
        )


def _parse_test_summary(output: str) -> dict:
    """Parse pytest output to extract test summary.

    Args:
        output: Raw pytest stdout

    Returns:
        Dictionary with passed, failed, skipped counts
    """
    summary = {
        "passed": 0,
        "failed": 0,
        "skipped": 0,
        "errors": 0,
        "total": 0,
    }

    # Look for summary line like "5 passed, 2 failed, 1 skipped"
    lines = output.split("\n")
    for line in reversed(lines):
        line_lower = line.lower()
        if "passed" in line_lower or "failed" in line_lower:
            import re

            # Extract numbers
            passed = re.search(r"(\d+)\s*passed", line_lower)
            failed = re.search(r"(\d+)\s*failed", line_lower)
            skipped = re.search(r"(\d+)\s*skipped", line_lower)
            errors = re.search(r"(\d+)\s*error", line_lower)

            if passed:
                summary["passed"] = int(passed.group(1))
            if failed:
                summary["failed"] = int(failed.group(1))
            if skipped:
                summary["skipped"] = int(skipped.group(1))
            if errors:
                summary["errors"] = int(errors.group(1))

            summary["total"] = (
                summary["passed"]
                + summary["failed"]
                + summary["skipped"]
                + summary["errors"]
            )
            break

    return summary
