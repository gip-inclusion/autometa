"""Interactive Claude CLI authentication via pseudo-TTY.

Allows web UI to guide users through OAuth flow without direct terminal access.
"""

import logging
import os
import pty
import re
import select
import subprocess
import threading
import time
from dataclasses import dataclass
from typing import Optional

from . import config

logger = logging.getLogger(__name__)

# Regex to extract OAuth URL from Claude output
URL_PATTERN = re.compile(r'https://[^\s\x1b]+')

# Active auth sessions (simple in-memory store, only one at a time)
_active_session: Optional["AuthSession"] = None
_session_lock = threading.Lock()


@dataclass
class AuthSession:
    """Represents an ongoing authentication session."""
    master_fd: int  # PTY master file descriptor
    pid: int  # Child process PID
    oauth_url: Optional[str] = None
    status: str = "starting"  # starting, waiting_for_code, completing, done, error
    error: Optional[str] = None
    output_buffer: str = ""


def start_auth(force: bool = False) -> dict:
    """Start a new Claude authentication session.

    Args:
        force: If True, re-authenticate even if credentials exist

    Returns dict with:
        - status: "waiting_for_code", "already_authenticated", or "error"
        - oauth_url: URL to open in browser (if waiting_for_code)
        - error: Error message (if failed)
    """
    global _active_session

    # Check if already authenticated
    from . import claude_credentials
    if claude_credentials.credentials_exist() and not force:
        return {
            "status": "already_authenticated",
            "message": "Credentials already exist. Use force=true to re-authenticate."
        }

    with _session_lock:
        # Clean up any existing session
        if _active_session:
            _cleanup_session(_active_session)
            _active_session = None

        try:
            # Create pseudo-terminal
            master_fd, slave_fd = pty.openpty()

            # Spawn claude process
            pid = os.fork()

            if pid == 0:
                # Child process
                os.close(master_fd)
                os.setsid()
                os.dup2(slave_fd, 0)  # stdin
                os.dup2(slave_fd, 1)  # stdout
                os.dup2(slave_fd, 2)  # stderr
                os.close(slave_fd)

                # Clear existing credentials to force auth flow
                claude_dir = os.path.expanduser("~/.claude")
                creds_file = os.path.join(claude_dir, ".credentials.json")
                if os.path.exists(creds_file):
                    os.rename(creds_file, creds_file + ".backup")

                # Execute claude
                os.execvp("claude", ["claude"])

            # Parent process
            os.close(slave_fd)

            _active_session = AuthSession(
                master_fd=master_fd,
                pid=pid,
                status="starting"
            )

            # Wait for OAuth URL to appear in output
            oauth_url = _wait_for_oauth_url(_active_session, timeout=30)

            if oauth_url:
                _active_session.oauth_url = oauth_url
                _active_session.status = "waiting_for_code"
                return {
                    "status": "waiting_for_code",
                    "oauth_url": oauth_url
                }
            else:
                _active_session.status = "error"
                _active_session.error = "Timeout waiting for OAuth URL"
                return {
                    "status": "error",
                    "error": f"Timeout waiting for OAuth URL. Output: {_active_session.output_buffer[-500:]}"
                }

        except Exception as e:
            logger.exception("Failed to start auth session")
            return {
                "status": "error",
                "error": str(e)
            }


def complete_auth(code: str) -> dict:
    """Complete authentication by sending the code to Claude.

    Args:
        code: The authentication code from the OAuth flow

    Returns dict with:
        - status: "done" or "error"
        - error: Error message (if failed)
    """
    global _active_session

    with _session_lock:
        if not _active_session:
            return {"status": "error", "error": "No active auth session"}

        if _active_session.status != "waiting_for_code":
            return {"status": "error", "error": f"Invalid session status: {_active_session.status}"}

        try:
            _active_session.status = "completing"

            # Send the code to claude
            os.write(_active_session.master_fd, (code + "\n").encode())

            # Wait for completion
            success = _wait_for_completion(_active_session, timeout=30)

            if success:
                _active_session.status = "done"

                # Backup credentials to S3
                from . import claude_credentials
                claude_credentials.backup_credentials_to_s3()

                return {"status": "done"}
            else:
                _active_session.status = "error"
                return {
                    "status": "error",
                    "error": f"Auth may have failed. Output: {_active_session.output_buffer[-500:]}"
                }

        except Exception as e:
            logger.exception("Failed to complete auth")
            _active_session.status = "error"
            return {"status": "error", "error": str(e)}

        finally:
            _cleanup_session(_active_session)
            _active_session = None


def get_auth_status() -> dict:
    """Get current auth session status."""
    with _session_lock:
        if not _active_session:
            return {"status": "no_session"}
        return {
            "status": _active_session.status,
            "oauth_url": _active_session.oauth_url,
            "error": _active_session.error
        }


def cancel_auth() -> dict:
    """Cancel any active auth session."""
    global _active_session

    with _session_lock:
        if _active_session:
            _cleanup_session(_active_session)
            _active_session = None
            return {"status": "cancelled"}
        return {"status": "no_session"}


def _wait_for_oauth_url(session: AuthSession, timeout: float) -> Optional[str]:
    """Wait for OAuth URL to appear in Claude output."""
    start_time = time.time()

    while time.time() - start_time < timeout:
        # Check if there's data to read
        readable, _, _ = select.select([session.master_fd], [], [], 0.5)

        if readable:
            try:
                data = os.read(session.master_fd, 4096)
                if data:
                    text = data.decode("utf-8", errors="replace")
                    session.output_buffer += text
                    logger.debug(f"Claude output: {text[:200]}")

                    # Look for OAuth URL
                    urls = URL_PATTERN.findall(session.output_buffer)
                    for url in urls:
                        if "claude.ai" in url or "anthropic.com" in url:
                            return url.rstrip('.,;:')
            except OSError:
                break

    return None


def _wait_for_completion(session: AuthSession, timeout: float) -> bool:
    """Wait for auth to complete after sending code."""
    start_time = time.time()

    while time.time() - start_time < timeout:
        readable, _, _ = select.select([session.master_fd], [], [], 0.5)

        if readable:
            try:
                data = os.read(session.master_fd, 4096)
                if data:
                    text = data.decode("utf-8", errors="replace")
                    session.output_buffer += text
                    logger.debug(f"Claude output: {text[:200]}")

                    # Check for success indicators
                    if "successfully" in text.lower() or "authenticated" in text.lower():
                        return True
                    # Check for error indicators
                    if "error" in text.lower() or "failed" in text.lower():
                        return False
            except OSError:
                break

        # Check if process has exited
        pid, status = os.waitpid(session.pid, os.WNOHANG)
        if pid != 0:
            # Process exited - check if credentials exist
            from . import claude_credentials
            return claude_credentials.credentials_exist()

    return False


def _cleanup_session(session: AuthSession):
    """Clean up an auth session."""
    try:
        os.close(session.master_fd)
    except OSError:
        pass

    try:
        os.kill(session.pid, 9)
        os.waitpid(session.pid, 0)
    except OSError:
        pass

    # Restore credentials backup if it exists
    claude_dir = os.path.expanduser("~/.claude")
    creds_backup = os.path.join(claude_dir, ".credentials.json.backup")
    creds_file = os.path.join(claude_dir, ".credentials.json")
    if os.path.exists(creds_backup) and not os.path.exists(creds_file):
        os.rename(creds_backup, creds_file)
