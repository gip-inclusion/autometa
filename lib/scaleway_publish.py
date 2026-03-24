"""Publish expert-mode apps to Scaleway Serverless Containers.

This is a one-shot publish action — Docker Compose remains the primary deploy backend.
Scaleway is additive: failure here never affects the running Docker production.
"""

import logging
import time
from typing import Callable, Optional

import requests

from web import config

logger = logging.getLogger(__name__)


def available() -> bool:
    """True if Scaleway publish is fully configured."""
    from lib import scaleway_registry, scaleway_rdb
    return scaleway_registry.available() and scaleway_rdb.available() and bool(config.SCW_CONTAINER_NAMESPACE_ID)


def publish(project_id: str, on_progress: Optional[Callable[[str, str], None]] = None) -> dict:
    """Publish a project's production app to Scaleway Serverless Containers.

    Steps:
    1. build   — Build Docker image from project workdir
    2. push    — Push to Scaleway Container Registry
    3. database — Provision PG database if needed
    4. deploy  — Create/update serverless container
    5. verify  — Wait for public URL to respond

    Returns {"status": "published", "url": "https://..."}
         or {"status": "error", "error": "...", "step": "..."}
    """
    from lib import scaleway_registry, scaleway_rdb
    from lib.docker_deploy import _llm_env_vars
    from web.database import ConversationStore
    from web.routes.expert import _detect_exposed_port

    def _progress(step: str, msg: str):
        logger.info("[publish %s] %s: %s", project_id[:8], step, msg)
        if on_progress:
            on_progress(step, msg)

    store = ConversationStore()
    project = store.get_project(project_id)
    if not project:
        return {"status": "error", "error": "Project not found", "step": "build"}

    workdir = config.PROJECTS_DIR / project_id

    # --- Step 1: Build ---
    _progress("build", "Building Docker image...")
    result = scaleway_registry.build_and_push(project_id)
    if result["status"] != "ok":
        return {"status": "error", "error": result["error"], "step": result["step"]}

    image = result["image"]
    _progress("push", f"Image pushed: {image}")

    # --- Step 3: Database ---
    database_url = project.scaleway_db_url
    if not database_url:
        _progress("database", "Provisioning PostgreSQL database...")
        db_result = scaleway_rdb.create_app_database(project.slug)
        if db_result["status"] != "ok":
            return {"status": "error", "error": db_result["error"], "step": f"database/{db_result['step']}"}
        database_url = db_result["database_url"]
        store.update_project(project_id, scaleway_db_url=database_url)
        _progress("database", f"Database ready: {db_result['db_name']}")
    else:
        _progress("database", "Database already provisioned, reusing")

    # --- Step 4: Deploy serverless container ---
    _progress("deploy", "Deploying to Scaleway Serverless...")

    # Detect port from Dockerfile
    port = _detect_exposed_port(workdir)

    # Build env vars
    env_vars = {"DATABASE_URL": database_url}
    env_vars.update(_llm_env_vars(project))
    # Remove HOST_PORT / COMPOSE_PROJECT_NAME — not needed for serverless
    env_vars.pop("HOST_PORT", None)
    env_vars.pop("COMPOSE_PROJECT_NAME", None)

    try:
        container_result = _deploy_container(
            project=project,
            image=image,
            port=port,
            env_vars=env_vars,
        )
    except Exception as e:
        return {"status": "error", "error": str(e), "step": "deploy"}

    if container_result.get("status") == "error":
        return container_result

    container_id = container_result["container_id"]
    public_url = container_result["url"]

    store.update_project(project_id,
                         scaleway_container_id=container_id,
                         scaleway_url=public_url)
    _progress("deploy", f"Container deployed: {public_url}")

    # --- Step 5: Verify ---
    _progress("verify", "Waiting for container to be ready...")
    verify_result = _verify_url(public_url, timeout=90)
    if not verify_result:
        return {
            "status": "published_unverified",
            "url": public_url,
            "warning": "Container deployed but not yet responding. It may need a few more seconds.",
        }

    _progress("verify", "Container is live!")
    return {"status": "published", "url": public_url}


def unpublish(project_id: str) -> dict:
    """Delete the serverless container. Keeps database for data preservation."""
    from web.database import ConversationStore
    store = ConversationStore()
    project = store.get_project(project_id)
    if not project:
        return {"status": "error", "error": "Project not found"}

    if not project.scaleway_container_id:
        return {"status": "error", "error": "Not published to Scaleway"}

    try:
        _delete_container(project.scaleway_container_id)
    except Exception as e:
        return {"status": "error", "error": str(e)}

    store.update_project(project_id, scaleway_container_id=None, scaleway_url=None)
    return {"status": "unpublished"}


def status(project_id: str) -> dict:
    """Query Scaleway container status. Always queries live, never cached."""
    from web.database import ConversationStore
    store = ConversationStore()
    project = store.get_project(project_id)
    if not project:
        return {"status": "not_published"}

    if not project.scaleway_container_id:
        return {"status": "not_published", "scaleway_url": project.scaleway_url}

    try:
        return _get_container_status(project.scaleway_container_id, project.scaleway_url)
    except Exception as e:
        return {"status": "error", "error": str(e)}


# ---------------------------------------------------------------------------
# Scaleway SDK helpers
# ---------------------------------------------------------------------------

def _scw_headers() -> dict:
    return {"X-Auth-Token": config.SCW_SECRET_KEY, "Content-Type": "application/json"}


def _scw_url(path: str) -> str:
    return f"https://api.scaleway.com/containers/v1beta1/regions/{config.SCW_REGION}/{path}"


def _deploy_container(project, image: str, port: int, env_vars: dict) -> dict:
    """Create or update a serverless container, then deploy it."""
    container_id = project.scaleway_container_id

    payload = {
        "namespace_id": config.SCW_CONTAINER_NAMESPACE_ID,
        "name": project.slug,
        "registry_image": image,
        "port": port,
        "min_scale": 1,
        "max_scale": 3,
        "memory_limit": 512,  # MB
        "cpu_limit": 500,     # millicores
        "timeout": "300s",
        "environment_variables": env_vars,
        "sandbox": "v2",
    }

    if container_id:
        # Update existing
        resp = requests.patch(
            _scw_url(f"containers/{container_id}"),
            json=payload,
            headers=_scw_headers(),
            timeout=30,
        )
    else:
        # Create new
        resp = requests.post(
            _scw_url("containers"),
            json=payload,
            headers=_scw_headers(),
            timeout=30,
        )

    if resp.status_code not in (200, 201):
        return {"status": "error", "error": f"Scaleway API {resp.status_code}: {resp.text[:500]}", "step": "deploy"}

    data = resp.json()
    container_id = data["id"]
    domain_name = data.get("domain_name", "")

    # Trigger deploy
    deploy_resp = requests.post(
        _scw_url(f"containers/{container_id}/deploy"),
        json={},
        headers=_scw_headers(),
        timeout=30,
    )
    if deploy_resp.status_code not in (200, 201):
        return {"status": "error", "error": f"Deploy trigger failed: {deploy_resp.text[:500]}", "step": "deploy"}

    public_url = f"https://{domain_name}" if domain_name else ""
    return {"container_id": container_id, "url": public_url}


def _delete_container(container_id: str):
    """Delete a serverless container."""
    resp = requests.delete(
        _scw_url(f"containers/{container_id}"),
        headers=_scw_headers(),
        timeout=30,
    )
    if resp.status_code not in (200, 204, 404):
        raise RuntimeError(f"Delete failed: {resp.status_code} {resp.text[:300]}")


def _get_container_status(container_id: str, url: str = None) -> dict:
    """Get live container status from Scaleway API."""
    resp = requests.get(
        _scw_url(f"containers/{container_id}"),
        headers=_scw_headers(),
        timeout=15,
    )
    if resp.status_code == 404:
        return {"status": "not_published"}
    if resp.status_code != 200:
        return {"status": "error", "error": f"API {resp.status_code}"}

    data = resp.json()
    scw_status = data.get("status", "unknown")
    domain = data.get("domain_name", "")

    return {
        "status": scw_status,
        "scaleway_url": f"https://{domain}" if domain else url,
        "container_id": container_id,
    }


def _verify_url(url: str, timeout: int = 90) -> bool:
    """Poll URL until it returns 200 or timeout."""
    if not url:
        return False
    deadline = time.time() + timeout
    while time.time() < deadline:
        try:
            r = requests.get(url, timeout=10, allow_redirects=True)
            if r.status_code < 500:
                return True
        except requests.RequestException:
            pass
        time.sleep(5)
    return False
