"""Build and push project images to Scaleway Container Registry."""

import logging
import subprocess
from pathlib import Path

from web import config

logger = logging.getLogger(__name__)


def available() -> bool:
    """True if Scaleway registry is configured."""
    return bool(config.SCW_SECRET_KEY and config.SCW_REGISTRY_ENDPOINT)


def image_uri(slug: str) -> str:
    """Full image URI for a project."""
    return f"{config.SCW_REGISTRY_ENDPOINT}/{slug}:latest"


def build_and_push(project_id: str) -> dict:
    """Build Docker image from production workdir, tag, and push to SCW registry.

    Returns {"status": "ok", "image": "rg.fr-par.scw.cloud/..."}
         or {"status": "error", "error": "...", "step": "build|login|push"}
    """
    from web.database import ConversationStore
    store = ConversationStore()
    project = store.get_project(project_id)
    if not project:
        return {"status": "error", "error": "Project not found", "step": "build"}

    workdir = config.PROJECTS_DIR / project_id
    if not (workdir / "Dockerfile").exists():
        return {"status": "error", "error": "No Dockerfile found", "step": "build"}

    tag = image_uri(project.slug)

    # Build
    result = subprocess.run(
        ["docker", "build", "-t", tag, "."],
        capture_output=True, text=True, timeout=300,
        cwd=str(workdir),
    )
    if result.returncode != 0:
        return {"status": "error", "error": result.stderr[-500:], "step": "build"}

    # Login (idempotent)
    login_result = subprocess.run(
        ["docker", "login", f"rg.{config.SCW_REGION}.scw.cloud",
         "-u", "nologin", "--password-stdin"],
        input=config.SCW_SECRET_KEY,
        capture_output=True, text=True, timeout=30,
    )
    if login_result.returncode != 0:
        return {"status": "error", "error": login_result.stderr[-500:], "step": "login"}

    # Push
    push_result = subprocess.run(
        ["docker", "push", tag],
        capture_output=True, text=True, timeout=300,
    )
    if push_result.returncode != 0:
        return {"status": "error", "error": push_result.stderr[-500:], "step": "push"}

    logger.info("Pushed %s for project %s", tag, project.slug)
    return {"status": "ok", "image": tag}
