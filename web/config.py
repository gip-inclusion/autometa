"""Configuration for the Matometa web application."""

import os
from pathlib import Path

# Base directory (Matometa project root)
BASE_DIR = Path(__file__).parent.parent.resolve()

# Agent backend: "cli" or "sdk"
AGENT_BACKEND = os.getenv("AGENT_BACKEND", "cli")

# Claude CLI path (uses system default if not set)
CLAUDE_CLI = os.getenv("CLAUDE_CLI", "claude")

# Auto-approve tool calls (for local development only!)
SKIP_PERMISSIONS = os.getenv("SKIP_PERMISSIONS", "true").lower() == "true"

# Web server settings
HOST = os.getenv("WEB_HOST", "127.0.0.1")
PORT = int(os.getenv("WEB_PORT", "5000"))
DEBUG = os.getenv("WEB_DEBUG", "true").lower() == "true"
