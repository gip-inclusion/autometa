"""API routes for Claude authentication status."""

from pathlib import Path

from fastapi import APIRouter

from web import config

router = APIRouter(prefix="/api/auth")

CREDENTIALS_FILE = Path.home() / ".claude" / ".credentials.json"

# FIXME(vperron): I am not sure why this is useful ?
# FIXME(vperron): But the selftest should absolutely have a check for the knowledge bases it knows.


@router.get("/status")
def status():
    """Check whether the agent backend is authenticated."""
    if not config.USES_CLAUDE_CLI:
        return {"backend": config.AGENT_BACKEND, "auth_required": False, "authenticated": True}

    has_token = bool(config.CLAUDE_CODE_OAUTH_TOKEN)
    has_creds = CREDENTIALS_FILE.exists()

    authenticated = has_token or has_creds or config.SKIP_CLI_AUTH_CHECK

    return {
        "backend": config.AGENT_BACKEND,
        "auth_required": True,
        "authenticated": authenticated,
    }
