"""API routes for Claude authentication status."""

import os
from pathlib import Path

from fastapi import APIRouter

from .. import config

router = APIRouter(prefix="/api/auth")

CREDENTIALS_FILE = Path.home() / ".claude" / ".credentials.json"


@router.get("/status")
def status():
    """Check whether the agent backend is authenticated.

    Returns auth_required=True + authenticated=False when the CLI backend
    has neither a credentials file nor a CLAUDE_CODE_OAUTH_TOKEN env var,
    so the frontend can show an informational banner.
    """
    if not config.USES_CLAUDE_CLI:
        return {"backend": config.AGENT_BACKEND, "auth_required": False, "authenticated": True}

    has_token = bool(os.getenv("CLAUDE_CODE_OAUTH_TOKEN"))
    has_creds = CREDENTIALS_FILE.exists()
    skip_check = os.getenv("SKIP_CLI_AUTH_CHECK", "").lower() == "true"

    authenticated = has_token or has_creds or skip_check

    return {
        "backend": config.AGENT_BACKEND,
        "auth_required": True,
        "authenticated": authenticated,
    }
