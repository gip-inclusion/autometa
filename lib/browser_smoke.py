"""Browser smoke test for deployed projects using agent-browser CLI.

Runs headless Chromium via 'agent-browser' to validate that a deployed app
actually renders (not just returns HTTP 200). Detects blank pages, 500 errors,
missing assets, and JS crashes.

Requires: agent-browser installed (npm install -g agent-browser && agent-browser install)
Either on host or in the 'browser' sidecar container.
"""

import json
import logging
import subprocess
import time
from pathlib import Path

logger = logging.getLogger(__name__)

# Try sidecar first, then host, then skip
SIDECAR_CONTAINER = "matometa-browser"
RESULTS_DIR = Path("/app/data/smoke-results")


def _run_browser_cmd(*args, timeout: int = 30) -> subprocess.CompletedProcess:
    """Run an agent-browser command, trying sidecar container first, then local."""
    # Try sidecar container
    cmd = ["docker", "exec", SIDECAR_CONTAINER, "npx", "agent-browser", *args]
    try:
        result = subprocess.run(cmd, capture_output=True, text=True, timeout=timeout)
        if result.returncode == 0 or "Error" not in result.stderr:
            return result
    except (FileNotFoundError, subprocess.TimeoutExpired):
        pass

    # Fallback: try local agent-browser
    cmd = ["npx", "agent-browser", *args]
    return subprocess.run(cmd, capture_output=True, text=True, timeout=timeout)


def browser_available() -> bool:
    """Check if agent-browser is available (sidecar or local)."""
    try:
        result = _run_browser_cmd("--version", timeout=10)
        return result.returncode == 0
    except (FileNotFoundError, subprocess.TimeoutExpired):
        return False


def smoke_test(deploy_url: str, project_id: str, timeout: int = 30) -> dict:
    """Run a browser smoke test on a deployed project.

    Opens the URL in headless Chromium, checks for errors, takes a screenshot.

    Returns dict with:
        status: "pass" | "fail" | "skipped"
        title: page title (if available)
        errors: list of error strings
        screenshot: path to screenshot file (if available)
        duration_ms: test duration
    """
    if not browser_available():
        return {"status": "skipped", "reason": "agent-browser not available"}

    start = time.time()
    errors = []
    title = None
    screenshot_path = None

    # Ensure results directory exists
    project_dir = RESULTS_DIR / project_id
    project_dir.mkdir(parents=True, exist_ok=True)

    try:
        # Step 1: Open URL
        result = _run_browser_cmd("open", deploy_url, timeout=timeout)
        if result.returncode != 0:
            return {
                "status": "fail",
                "errors": [f"Failed to open {deploy_url}: {result.stderr[:500]}"],
                "duration_ms": int((time.time() - start) * 1000),
            }

        # Step 2: Wait for page load
        _run_browser_cmd("wait", "--load", "networkidle", timeout=15)

        # Step 3: Get page title
        title_result = _run_browser_cmd("get", "title", timeout=5)
        if title_result.returncode == 0:
            title = title_result.stdout.strip()

        # Step 4: Check for error indicators in page
        snapshot_result = _run_browser_cmd("snapshot", timeout=10)
        if snapshot_result.returncode == 0:
            page_text = snapshot_result.stdout.lower()

            # Check for common error patterns
            error_patterns = [
                ("500 internal server error", "Server returned 500 error"),
                ("502 bad gateway", "Server returned 502 error"),
                ("503 service unavailable", "Server returned 503 error"),
                ("application error", "Application error detected"),
                ("traceback (most recent call last)", "Python traceback detected"),
                ("error: cannot find module", "Node.js module not found"),
                ("ECONNREFUSED", "Connection refused"),  # case-sensitive deliberate
            ]
            for pattern, msg in error_patterns:
                if pattern.lower() in page_text:
                    errors.append(msg)

            # Check for blank page (very little content)
            if len(page_text.strip()) < 50:
                errors.append("Page appears blank (< 50 chars of content)")

        # Step 5: Check for JS console errors
        console_result = _run_browser_cmd("errors", timeout=5)
        if console_result.returncode == 0 and console_result.stdout.strip():
            js_errors = console_result.stdout.strip().splitlines()
            if js_errors:
                errors.append(f"{len(js_errors)} JS error(s): {js_errors[0][:200]}")

        # Step 6: Take screenshot
        screenshot_file = str(project_dir / "latest.png")
        ss_result = _run_browser_cmd("screenshot", screenshot_file, timeout=10)
        if ss_result.returncode == 0:
            screenshot_path = screenshot_file

        # Step 7: Close browser session
        _run_browser_cmd("close", timeout=5)

    except subprocess.TimeoutExpired:
        errors.append(f"Browser test timed out after {timeout}s")
    except Exception as e:
        errors.append(f"Browser test error: {e}")

    duration_ms = int((time.time() - start) * 1000)

    status = "fail" if errors else "pass"
    result = {
        "status": status,
        "title": title,
        "errors": errors,
        "duration_ms": duration_ms,
    }
    if screenshot_path:
        result["screenshot"] = screenshot_path

    level = logging.WARNING if errors else logging.INFO
    logger.log(level, "Smoke test %s for %s (%dms): %s",
               status, deploy_url, duration_ms, errors or "OK")

    return result
