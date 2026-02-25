#!/usr/bin/env python3
"""Run an end-to-end expert mode flow locally and collect evidence."""

from __future__ import annotations

import json
import subprocess
import sys
import time
from dataclasses import dataclass
from pathlib import Path

import requests


ROOT = Path(__file__).resolve().parents[1]
BASE_URL = "http://127.0.0.1:5002"
GITEA_BASE_URL = "http://127.0.0.1:3300"
ENV_FILE = ROOT / ".env"


class E2EError(RuntimeError):
    """Raised when an E2E assertion fails."""


@dataclass
class FlowContext:
    project_id: str
    project_slug: str
    project_key: str
    staging_branch: str
    production_branch: str


def load_env(path: Path) -> dict[str, str]:
    env: dict[str, str] = {}
    if not path.exists():
        return env
    for raw_line in path.read_text().splitlines():
        line = raw_line.strip()
        if not line or line.startswith("#") or "=" not in line:
            continue
        key, value = line.split("=", 1)
        env[key.strip()] = value.strip()
    return env


def run_cmd(cmd: list[str]) -> str:
    proc = subprocess.run(cmd, cwd=ROOT, check=True, capture_output=True, text=True)
    return proc.stdout.strip()


def docker_git(project_id: str, *args: str) -> str:
    cmd = [
        "docker",
        "compose",
        "exec",
        "-T",
        "matometa",
        "git",
        "-C",
        f"/app/data/projects/{project_id}",
        *args,
    ]
    return run_cmd(cmd)


def wait_http_ok(url: str, timeout_s: int = 120) -> None:
    started = time.time()
    while time.time() - started < timeout_s:
        try:
            response = requests.get(url, timeout=10)
            if response.status_code == 200:
                return
        except requests.RequestException:
            pass
        time.sleep(2)
    raise E2EError(f"Timed out waiting for {url} to return HTTP 200")


def poll_deploy_status(project_id: str, environment: str, timeout_s: int = 900) -> dict:
    started = time.time()
    last_payload: dict | None = None
    while time.time() - started < timeout_s:
        response = requests.get(f"{BASE_URL}/api/expert/projects/{project_id}/deploy-status", timeout=20)
        response.raise_for_status()
        payload = response.json()
        env_state = payload.get(environment, {})
        status = (env_state.get("status") or "").lower()
        last_payload = payload
        if status.startswith("running"):
            return payload
        time.sleep(5)
    raise E2EError(
        f"Timed out waiting for {environment} to be running. Last payload: {json.dumps(last_payload, ensure_ascii=False)}"
    )


def wait_preview_contains(url: str, text: str, timeout_s: int = 900) -> str:
    started = time.time()
    while time.time() - started < timeout_s:
        try:
            response = requests.get(url, timeout=20)
            if response.status_code == 200 and text in response.text:
                return response.text
        except requests.RequestException:
            pass
        time.sleep(5)
    raise E2EError(f"Timed out waiting for preview {url} to contain '{text}'.")


def update_index_file(project_id: str, marker: str) -> str:
    container_path = f"/app/data/projects/{project_id}/index.html"
    run_cmd(
        [
            "docker",
            "compose",
            "exec",
            "-T",
            "matometa",
            "python",
            "-c",
            (
                "from pathlib import Path; import sys; "
                "target=Path(sys.argv[1]); marker=sys.argv[2]; "
                "target.write_text("  # noqa: E501
                "'<!doctype html>\\n'"
                "'<html lang=\\\"fr\\\">\\n'"
                "'<head><meta charset=\\\"utf-8\\\"><meta name=\\\"viewport\\\" content=\\\"width=device-width,initial-scale=1\\\">'"
                "'<title>Expert E2E</title></head>\\n'"
                "'<body style=\\\"font-family:sans-serif;margin:2rem;\\\">\\n'"
                "f'<h1>{marker}</h1>\\n'"
                "f'<p>{marker}</p>\\n'"
                "'</body></html>\\n'"
                ")"
            ),
            container_path,
            marker,
        ]
    )
    return container_path


def commit_and_push_marker(ctx: FlowContext, marker: str, message: str) -> str:
    update_index_file(ctx.project_id, marker)

    docker_git(ctx.project_id, "fetch", "origin")
    try:
        docker_git(ctx.project_id, "checkout", ctx.staging_branch)
    except subprocess.CalledProcessError:
        docker_git(
            ctx.project_id,
            "checkout",
            "-b",
            ctx.staging_branch,
            "--track",
            f"origin/{ctx.staging_branch}",
        )

    docker_git(ctx.project_id, "config", "user.email", "e2e@matometa.local")
    docker_git(ctx.project_id, "config", "user.name", "Matometa E2E")
    docker_git(ctx.project_id, "add", "index.html")
    staged = docker_git(ctx.project_id, "diff", "--cached", "--name-only")
    if "index.html" not in staged:
        raise E2EError("Expected index.html to be staged before commit")
    docker_git(ctx.project_id, "commit", "-m", message)
    sha = docker_git(ctx.project_id, "rev-parse", "HEAD")
    docker_git(ctx.project_id, "push", "origin", ctx.staging_branch)
    return sha


def run_flow() -> dict:
    wait_http_ok(f"{BASE_URL}/expert")

    env = load_env(ENV_FILE)
    gitea_token = env.get("GITEA_API_TOKEN", "")
    gitea_org = env.get("GITEA_ORG", "apps")
    if not gitea_token:
        raise E2EError("GITEA_API_TOKEN missing in .env")

    session = requests.Session()
    session.headers.update({"Content-Type": "application/json"})

    run_id = int(time.time())
    project_name = f"E2E Expert {run_id}"
    create_response = session.post(
        f"{BASE_URL}/api/expert/projects",
        json={"name": project_name, "description": "Automated expert E2E flow", "stack_profile": "web_only"},
        timeout=30,
    )
    create_response.raise_for_status()
    create_payload = create_response.json()
    project = create_payload["project"]

    ctx = FlowContext(
        project_id=project["id"],
        project_slug=project["slug"],
        project_key=project["project_key"],
        staging_branch=project.get("staging_branch") or "stagging",
        production_branch=project.get("production_branch") or "prod",
    )

    repo_response = requests.get(
        f"{GITEA_BASE_URL}/api/v1/repos/{gitea_org}/{ctx.project_key}",
        headers={"Authorization": f"token {gitea_token}"},
        timeout=20,
    )
    repo_response.raise_for_status()
    repo_payload = repo_response.json()

    local_clone = ROOT / "data" / "projects" / ctx.project_id / ".git"
    if not local_clone.exists():
        raise E2EError(f"Local clone missing at {local_clone}")

    deploy_staging_response = session.post(
        f"{BASE_URL}/api/expert/projects/{ctx.project_id}/deploy-staging",
        json={},
        timeout=120,
    )
    deploy_staging_response.raise_for_status()
    deploy_staging_payload = deploy_staging_response.json()

    status_after_staging = poll_deploy_status(ctx.project_id, "staging")
    staging_preview_url = f"{BASE_URL}/expert/{ctx.project_slug}/preview/staging/"
    baseline_preview = requests.get(staging_preview_url, timeout=30)
    baseline_preview.raise_for_status()

    hooks_response = requests.get(
        f"{GITEA_BASE_URL}/api/v1/repos/{gitea_org}/{ctx.project_key}/hooks",
        headers={"Authorization": f"token {gitea_token}"},
        timeout=20,
    )
    hooks_response.raise_for_status()
    hooks = hooks_response.json()
    matching_hooks = [
        hook
        for hook in hooks
        if "webhooks/source/gitea/events/manual" in ((hook.get("config") or {}).get("url") or "")
    ]
    if not matching_hooks:
        raise E2EError("No Gitea webhook found for Coolify manual source endpoint")

    marker_v1 = f"E2E-STAGING-V1-{run_id}"
    sha_v1 = commit_and_push_marker(ctx, marker_v1, f"test: staging marker v1 {run_id}")
    wait_preview_contains(staging_preview_url, marker_v1)

    deploy_prod_response = session.post(
        f"{BASE_URL}/api/expert/projects/{ctx.project_id}/deploy",
        json={},
        timeout=120,
    )
    deploy_prod_response.raise_for_status()
    deploy_prod_payload = deploy_prod_response.json()

    status_after_production = poll_deploy_status(ctx.project_id, "production")
    production_preview_url = f"{BASE_URL}/expert/{ctx.project_slug}/preview/production/"
    production_preview_v1 = wait_preview_contains(production_preview_url, marker_v1)

    marker_v2 = f"E2E-STAGING-V2-{run_id}"
    sha_v2 = commit_and_push_marker(ctx, marker_v2, f"test: staging marker v2 {run_id}")
    wait_preview_contains(staging_preview_url, marker_v2)

    production_after_v2 = requests.get(production_preview_url, timeout=30)
    production_after_v2.raise_for_status()
    production_after_v2_body = production_after_v2.text
    if marker_v2 in production_after_v2_body:
        raise E2EError("Production preview changed after staging-only update")
    if marker_v1 not in production_after_v2_body:
        raise E2EError("Production preview no longer contains expected promoted version marker")

    return {
        "run_id": run_id,
        "project": {
            "id": ctx.project_id,
            "slug": ctx.project_slug,
            "project_key": ctx.project_key,
            "staging_branch": ctx.staging_branch,
            "production_branch": ctx.production_branch,
            "local_clone": str(local_clone),
        },
        "repo": {
            "full_name": repo_payload.get("full_name"),
            "html_url": repo_payload.get("html_url"),
            "default_branch": repo_payload.get("default_branch"),
        },
        "staging": {
            "deploy_response": deploy_staging_payload,
            "status_payload": status_after_staging,
            "preview_url": staging_preview_url,
            "baseline_preview_has_h1": "<h1" in baseline_preview.text.lower(),
            "marker_v1": marker_v1,
            "marker_v2": marker_v2,
            "commit_v1": sha_v1,
            "commit_v2": sha_v2,
            "matching_webhooks": matching_hooks,
        },
        "production": {
            "deploy_response": deploy_prod_payload,
            "status_payload": status_after_production,
            "preview_url": production_preview_url,
            "contains_v1": marker_v1 in production_preview_v1,
            "contains_v2_after_staging_only_change": marker_v2 in production_after_v2_body,
        },
    }


def main() -> int:
    try:
        result = run_flow()
        print(json.dumps(result, indent=2, ensure_ascii=False))
        return 0
    except Exception as exc:
        print(f"E2E flow failed: {exc}", file=sys.stderr)
        return 1


if __name__ == "__main__":
    raise SystemExit(main())
