"""Configuration for the Autometa web application."""

import os
from pathlib import Path

from dotenv import load_dotenv

# Base directory (Autometa project root)
BASE_DIR = Path(__file__).parent.parent.resolve()

load_dotenv(BASE_DIR / ".env")

# Data directory - can be overridden for local development with remote data
# Default: ./data (relative to BASE_DIR)
DATA_DIR = Path(os.getenv("DATA_DIR", BASE_DIR / "data")).resolve()

# Agent backend: "cli", "sdk", or "cli-ollama"
AGENT_BACKEND = os.getenv("AGENT_BACKEND", "cli").lower()

# LLM backend for short prompts (titles, tags). Defaults to AGENT_BACKEND.
LLM_BACKEND = os.getenv("LLM_BACKEND", "").strip().lower() or AGENT_BACKEND

# Claude CLI path (uses system default if not set)
CLAUDE_CLI = os.getenv("CLAUDE_CLI", "claude")

# Claude model (used by SDK and CLI helper)
CLAUDE_MODEL = os.getenv("CLAUDE_MODEL", "claude-sonnet-4-20250514")

# Allowed tools for the agent (CLI backend only - SDK ignores this)
# Bash patterns use glob wildcards (* matches anything)
# NOTE: Real security boundary is the container, not LLM tool restrictions
ALLOWED_TOOLS = os.getenv(
    "ALLOWED_TOOLS",
    "Read,Write,Edit,Glob,Grep,"
    "Bash(curl:*inclusion.gouv.fr*),Bash(curl:*inclusion.beta.gouv.fr*),"
    "Bash(curl:*github.com/gip-inclusion*),Bash(curl:*github.com/betagouv*),"
    "Bash(curl:*raw.githubusercontent.com/gip-inclusion*),Bash(curl:*raw.githubusercontent.com/betagouv*),"
    "Bash(curl:*api.github.com*),"
    "Bash(jq:*),"
    "Bash(python:*),Bash(python3:*),"
    "Bash(.venv/bin/python:*)",
)

# Ollama settings (used by cli-ollama backend and LLM short-prompt helper)
OLLAMA_BASE_URL = os.getenv("OLLAMA_BASE_URL", "http://localhost:11434")
OLLAMA_MODEL = os.getenv("OLLAMA_MODEL", "qwen3-coder-next")
OLLAMA_TITLE_MODEL = os.getenv("OLLAMA_TITLE_MODEL", OLLAMA_MODEL)
OLLAMA_TAG_MODEL = os.getenv("OLLAMA_TAG_MODEL", OLLAMA_MODEL)
OLLAMA_REQUEST_TIMEOUT = float(os.getenv("OLLAMA_REQUEST_TIMEOUT", "120"))

# Backend capability helpers
USES_CLAUDE_CLI = AGENT_BACKEND in ("cli", "sdk") or LLM_BACKEND in ("cli", "sdk")

# Display timezone (IANA name, e.g. "Europe/Paris")
DISPLAY_TIMEZONE = os.getenv("DISPLAY_TIMEZONE", "Europe/Paris")

# Web server settings
HOST = os.getenv("WEB_HOST", "127.0.0.1")
PORT = int(os.getenv("WEB_PORT", "5000"))
DEBUG = os.getenv("WEB_DEBUG", "false").lower() == "true"

# Base URL for generating absolute links
# Only needed when sharing links outside the app; prefer relative URLs otherwise.
BASE_URL = os.getenv("BASE_URL", "").rstrip("/")

# Default user for local development (when oauth-proxy not present)
DEFAULT_USER = os.getenv("DEFAULT_USER", "admin@localhost")

# Admin users who can see all conversations (comma-separated emails)
ADMIN_USERS = [
    email.strip()
    for email in os.getenv("ADMIN_USERS", "louisjean.teitelbaum@inclusion.gouv.fr,admin@localhost").split(",")
    if email.strip()
]

# Database: PostgreSQL via DATABASE_URL (required)
DATABASE_URL = (os.getenv("DATABASE_URL") or "").replace("postgres://", "postgresql://")

SSE_MESSAGE_WAIT_TIMEOUT = float(os.getenv("AUTOMETA_SSE_MESSAGE_WAIT_TIMEOUT", "3"))

# Agent-produced scripts directory
SCRIPTS_DIR = DATA_DIR / "scripts"

# Interactive files directory (agent-generated exports, dashboards)
# Used for local storage fallback when S3 is not configured
INTERACTIVE_DIR = DATA_DIR / "interactive"

# System cron tasks (checked into repo, always available)
CRON_DIR = BASE_DIR / "cron"

# Common shared assets (CSS/JS frameworks used by interactive apps)
# Always relative to BASE_DIR (framework code, not per-environment data)
COMMON_DIR = BASE_DIR / "data" / "common"

# Uploads directory for user-uploaded files in chat
UPLOADS_DIR = DATA_DIR / "uploads"

# Modified files directory (writable copies of uploaded files for agent modifications)
MODIFIED_DIR = DATA_DIR / "modified"

# File upload limits
MAX_UPLOAD_SIZE = int(os.getenv("MAX_UPLOAD_SIZE", 200 * 1024 * 1024))  # 200 MB default
# Text file size threshold for including content directly in conversation
TEXT_FILE_INLINE_LIMIT = int(os.getenv("TEXT_FILE_INLINE_LIMIT", 50 * 1024))  # 50 KB default

# S3-compatible object storage for interactive files
# If configured, files are stored in S3 instead of local filesystem
# Works with AWS S3, Scaleway Object Storage, MinIO, etc.
S3_BUCKET = os.getenv("S3_BUCKET")
S3_ENDPOINT = os.getenv("S3_ENDPOINT")  # e.g., https://s3.fr-par.scw.cloud
S3_ACCESS_KEY = os.getenv("S3_ACCESS_KEY")
S3_SECRET_KEY = os.getenv("S3_SECRET_KEY")
S3_REGION = os.getenv("S3_REGION", "fr-par")
S3_PREFIX = os.getenv("S3_PREFIX", "interactive/")  # Key prefix for all files


# Container environment flag (set in Docker — bypasses permission checks)
CONTAINER_ENV = bool(os.getenv("CONTAINER_ENV"))

# Claude Code OAuth token (injected by oauth-proxy or set manually)
CLAUDE_CODE_OAUTH_TOKEN = os.getenv("CLAUDE_CODE_OAUTH_TOKEN")

# Skip CLI auth check (local dev convenience)
SKIP_CLI_AUTH_CHECK = os.getenv("SKIP_CLI_AUTH_CHECK", "false").lower() == "true"

# Max concurrent agent processes
MAX_CONCURRENT_AGENTS = int(os.getenv("MAX_CONCURRENT_AGENTS", "2"))

# Notion integration
NOTION_TOKEN = os.getenv("NOTION_TOKEN")
NOTION_REPORTS_DB = os.getenv("NOTION_REPORTS_DB")
NOTION_WISHLIST_DB = os.getenv("NOTION_WISHLIST_DB")


# Slack notifications
SLACK_BOT_TOKEN = os.getenv("SLACK_BOT_TOKEN", "")
# FIXME: remove EMAIL_ANNAELLE fallback once prod env var is renamed to FAILURE_NOTIFY_EMAILS
_notify_raw = os.getenv("FAILURE_NOTIFY_EMAILS") or os.getenv("EMAIL_ANNAELLE", "")
FAILURE_NOTIFY_EMAILS = [email.strip() for email in _notify_raw.split(",") if email.strip()]

# Grist (webinaire data)
GRIST_API_KEY = os.getenv("GRIST_API_KEY")
GRIST_WEBINAIRES_DOC_ID = os.getenv("GRIST_WEBINAIRES_DOC_ID")

# Livestorm API
LIVESTORM_API_KEY = os.getenv("LIVESTORM_API_KEY")

# Redis (Scalingo provides SCALINGO_REDIS_URL)
REDIS_URL = os.getenv("REDIS_URL") or os.getenv("SCALINGO_REDIS_URL") or "redis://localhost:6379/0"

# Web server
WEB_WORKERS = int(os.getenv("WEB_WORKERS", os.cpu_count() or 1))

# Additional directories the agent can access (beyond working directory)
ADDITIONAL_DIRS = ["/tmp", str(DATA_DIR / "cache"), str(INTERACTIVE_DIR)]
