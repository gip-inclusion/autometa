#!/usr/bin/env python3
"""Run a conversation-driven expert-mode E2E flow and collect hard evidence."""

from __future__ import annotations

import json
import time
from dataclasses import dataclass
from pathlib import Path

import requests


ROOT = Path(__file__).resolve().parents[1]
BASE_URL = "http://127.0.0.1:5002"
GITEA_URL = "http://127.0.0.1:3300"


class E2EError(RuntimeError):
    """Raised for any E2E verification failure."""


@dataclass
class ProjectCtx:
    project_id: str
    slug: str
    project_key: str
    conversation_id: str
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


def wait_http_ok(url: str, timeout_s: int = 120) -> None:
    start = time.time()
    while time.time() - start < timeout_s:
        try:
            response = requests.get(url, timeout=10)
            if response.status_code == 200:
                return
        except requests.RequestException:
            pass
        time.sleep(2)
    raise E2EError(f"Timed out waiting for {url}")


def parse_sse(response: requests.Response) -> list[dict]:
    events: list[dict] = []
    current_event = "message"
    current_data: list[str] = []

    for raw_line in response.iter_lines(decode_unicode=True):
        if raw_line is None:
            continue
        line = raw_line.strip("\r")

        if line == "":
            if current_data:
                payload_raw = "\n".join(current_data)
                try:
                    payload = json.loads(payload_raw)
                except json.JSONDecodeError:
                    payload = {"raw": payload_raw}
                events.append({"event": current_event, "data": payload})
                if current_event == "done":
                    break
            current_event = "message"
            current_data = []
            continue

        if line.startswith("event: "):
            current_event = line[len("event: "):]
        elif line.startswith("data: "):
            current_data.append(line[len("data: "):])

    return events


def get_conversation(conv_id: str) -> dict:
    response = requests.get(f"{BASE_URL}/api/conversations/{conv_id}", timeout=30)
    response.raise_for_status()
    return response.json()


def extract_last_assistant(conv_id: str) -> str:
    conv = get_conversation(conv_id)
    messages = conv.get("messages", [])
    assistant = [m for m in messages if m.get("type") == "assistant"]
    if not assistant:
        raise E2EError(f"No assistant messages found for conversation {conv_id}")
    return assistant[-1].get("content", "")


def send_message_and_wait(conv_id: str, content: str, timeout_s: int = 1200) -> dict:
    send_response = requests.post(
        f"{BASE_URL}/api/conversations/{conv_id}/messages",
        json={"content": content},
        timeout=30,
    )
    send_response.raise_for_status()
    send_payload = send_response.json()
    after_id = send_payload.get("after_id", 0)

    stream_url = f"{BASE_URL}/api/conversations/{conv_id}/stream"
    stream_response = requests.get(
        stream_url,
        params={"after": after_id},
        timeout=(30, timeout_s),
        stream=True,
    )
    stream_response.raise_for_status()
    events = parse_sse(stream_response)

    errors = [e for e in events if e["event"] == "error"]
    if errors:
        raise E2EError(f"Conversation {conv_id} streamed error: {errors[-1]['data']}")

    auto_commit_events = [
        e
        for e in events
        if e["event"] == "system"
        and isinstance(e.get("data"), dict)
        and isinstance(e["data"].get("content"), dict)
        and e["data"]["content"].get("subtype") == "auto_commit"
    ]

    assistant_text = extract_last_assistant(conv_id)
    return {
        "send": send_payload,
        "events": events,
        "assistant": assistant_text,
        "auto_commit": auto_commit_events[-1]["data"]["content"] if auto_commit_events else None,
    }


def get_repo(gitea_org: str, project_key: str, token: str) -> dict:
    response = requests.get(
        f"{GITEA_URL}/api/v1/repos/{gitea_org}/{project_key}",
        headers={"Authorization": f"token {token}"},
        timeout=20,
    )
    response.raise_for_status()
    return response.json()


def get_branch_sha(gitea_org: str, project_key: str, branch: str, token: str) -> str:
    response = requests.get(
        f"{GITEA_URL}/api/v1/repos/{gitea_org}/{project_key}/branches/{branch}",
        headers={"Authorization": f"token {token}"},
        timeout=20,
    )
    response.raise_for_status()
    return response.json().get("commit", {}).get("id", "")


def get_hooks(gitea_org: str, project_key: str, token: str) -> list[dict]:
    response = requests.get(
        f"{GITEA_URL}/api/v1/repos/{gitea_org}/{project_key}/hooks",
        headers={"Authorization": f"token {token}"},
        timeout=20,
    )
    response.raise_for_status()
    return response.json()


def poll_preview(url: str, must_contain: str, must_not_contain: str | None = None, timeout_s: int = 900) -> str:
    start = time.time()
    last_text = ""
    while time.time() - start < timeout_s:
        try:
            response = requests.get(url, timeout=20)
            if response.status_code == 200:
                last_text = response.text
                if must_contain in response.text:
                    if must_not_contain and must_not_contain in response.text:
                        time.sleep(5)
                        continue
                    return response.text
        except requests.RequestException:
            pass
        time.sleep(5)
    raise E2EError(f"Preview {url} did not converge to expected content")


def poll_deploy_status(project_id: str, environment: str, timeout_s: int = 900) -> dict:
    start = time.time()
    last_payload: dict | None = None
    while time.time() - start < timeout_s:
        response = requests.get(f"{BASE_URL}/api/expert/projects/{project_id}/deploy-status", timeout=20)
        response.raise_for_status()
        payload = response.json()
        status = str((payload.get(environment) or {}).get("status") or "")
        last_payload = payload
        if status.startswith("running"):
            return payload
        time.sleep(5)
    raise E2EError(f"Deploy status timeout for {environment}: {json.dumps(last_payload, ensure_ascii=False)}")


def run_e2e() -> dict:
    wait_http_ok(f"{BASE_URL}/expert")

    env = load_env(ROOT / ".env")
    gitea_token = env.get("GITEA_API_TOKEN", "")
    gitea_org = env.get("GITEA_ORG", "apps")
    if not gitea_token:
        raise E2EError("GITEA_API_TOKEN missing in .env")

    run_id = int(time.time())
    marker_v1 = f"E2E-AGENT-V1-{run_id}"
    marker_v2 = f"E2E-AGENT-V2-{run_id}"

    create_response = requests.post(
        f"{BASE_URL}/api/expert/projects",
        json={
            "name": f"E2E Agent {run_id}",
            "description": "Conversation-driven expert E2E",
            "stack_profile": "web_only",
        },
        timeout=30,
    )
    create_response.raise_for_status()
    create_payload = create_response.json()
    project = create_payload.get("project", {})

    ctx = ProjectCtx(
        project_id=project["id"],
        slug=project["slug"],
        project_key=project["project_key"],
        conversation_id=create_payload["conversation_id"],
        staging_branch=project.get("staging_branch") or "stagging",
        production_branch=project.get("production_branch") or "prod",
    )

    repo = get_repo(gitea_org, ctx.project_key, gitea_token)
    local_clone = ROOT / "data" / "projects" / ctx.project_id / ".git"
    if not local_clone.exists():
        raise E2EError(f"Local clone missing at {local_clone}")

    hooks = get_hooks(gitea_org, ctx.project_key, gitea_token)

    planning = send_message_and_wait(
        ctx.conversation_id,
        (
            "Passez en mode plan et proposez une specification detaillee pour une app web minimale. "
            "Objectif: page index avec un titre principal."
        ),
    )
    if not planning["assistant"].strip():
        raise E2EError("Planning response is empty")

    plan_draft_response = requests.put(
        f"{BASE_URL}/api/expert/projects/{ctx.project_id}/plan-draft",
        json={"content": planning["assistant"]},
        timeout=30,
    )
    plan_draft_response.raise_for_status()
    plan_draft = plan_draft_response.json()
    if plan_draft.get("workflow_phase") != "awaiting_approval":
        raise E2EError(f"Unexpected phase after plan draft: {plan_draft.get('workflow_phase')}")

    approve_response = requests.post(
        f"{BASE_URL}/api/expert/projects/{ctx.project_id}/plan-approve",
        json={"conversation_id": ctx.conversation_id},
        timeout=30,
    )
    approve_response.raise_for_status()
    approved = approve_response.json()
    if approved.get("workflow_phase") != "implementing":
        raise E2EError(f"Unexpected phase after approve: {approved.get('workflow_phase')}")

    implement_v1 = send_message_and_wait(
        ctx.conversation_id,
        (
            "Implementez maintenant l'application. "
            "Dans index.html, affichez exactement ce texte dans un h1: "
            f"{marker_v1}."
        ),
        timeout_s=1800,
    )
    if not implement_v1.get("auto_commit"):
        raise E2EError("No auto_commit event detected after first implementation message")

    auto_commit_v1 = implement_v1["auto_commit"]
    if auto_commit_v1.get("branch") != ctx.staging_branch:
        raise E2EError(f"Auto commit branch mismatch: {auto_commit_v1}")

    staging_sha_v1 = get_branch_sha(gitea_org, ctx.project_key, ctx.staging_branch, gitea_token)
    if not staging_sha_v1.startswith(auto_commit_v1.get("commit", "")):
        raise E2EError("Staging branch head does not match auto-commit hash for v1")

    staging_preview_url = f"{BASE_URL}/expert/{ctx.slug}/preview/staging/"
    staging_preview_v1 = poll_preview(staging_preview_url, marker_v1, timeout_s=900)

    deploy_prod_response = requests.post(
        f"{BASE_URL}/api/expert/projects/{ctx.project_id}/deploy",
        json={},
        timeout=120,
    )
    deploy_prod_response.raise_for_status()
    deploy_prod = deploy_prod_response.json()

    status_prod_ready = poll_deploy_status(ctx.project_id, "production", timeout_s=900)
    production_preview_url = f"{BASE_URL}/expert/{ctx.slug}/preview/production/"
    production_preview_v1 = poll_preview(production_preview_url, marker_v1, timeout_s=900)

    production_sha_v1 = get_branch_sha(gitea_org, ctx.project_key, ctx.production_branch, gitea_token)

    implement_v2 = send_message_and_wait(
        ctx.conversation_id,
        (
            "Faites une nouvelle modification: remplacez le texte du h1 dans index.html. "
            f"Le nouveau texte exact doit etre {marker_v2}."
        ),
        timeout_s=1800,
    )
    if not implement_v2.get("auto_commit"):
        raise E2EError("No auto_commit event detected after second implementation message")

    auto_commit_v2 = implement_v2["auto_commit"]
    if auto_commit_v2.get("branch") != ctx.staging_branch:
        raise E2EError(f"Second auto commit branch mismatch: {auto_commit_v2}")

    staging_sha_v2 = get_branch_sha(gitea_org, ctx.project_key, ctx.staging_branch, gitea_token)
    if not staging_sha_v2.startswith(auto_commit_v2.get("commit", "")):
        raise E2EError("Staging branch head does not match auto-commit hash for v2")

    staging_preview_v2 = poll_preview(staging_preview_url, marker_v2, timeout_s=900)

    # Production must remain at v1 after staging-only second change.
    production_after_v2 = requests.get(production_preview_url, timeout=20)
    production_after_v2.raise_for_status()
    production_after_v2_body = production_after_v2.text
    if marker_v2 in production_after_v2_body:
        raise E2EError("Production preview was updated by staging-only second change")
    if marker_v1 not in production_after_v2_body:
        raise E2EError("Production preview lost v1 marker unexpectedly")

    production_sha_after_v2 = get_branch_sha(gitea_org, ctx.project_key, ctx.production_branch, gitea_token)
    if production_sha_after_v2 != production_sha_v1:
        raise E2EError("Production branch moved after staging-only second change")

    status_after_v2 = poll_deploy_status(ctx.project_id, "staging", timeout_s=120)

    return {
        "run_id": run_id,
        "project": {
            "id": ctx.project_id,
            "slug": ctx.slug,
            "project_key": ctx.project_key,
            "conversation_id": ctx.conversation_id,
            "staging_branch": ctx.staging_branch,
            "production_branch": ctx.production_branch,
            "local_clone": str(local_clone),
        },
        "repo": {
            "full_name": repo.get("full_name"),
            "html_url": repo.get("html_url"),
            "default_branch": repo.get("default_branch"),
            "hooks": [
                {
                    "id": h.get("id"),
                    "branch_filter": h.get("branch_filter"),
                    "url": (h.get("config") or {}).get("url"),
                }
                for h in hooks
                if "webhooks/source/gitea/events/manual" in ((h.get("config") or {}).get("url") or "")
            ],
        },
        "planning": {
            "assistant_excerpt": planning["assistant"][:600],
            "workflow_after_approve": approved.get("workflow_phase"),
        },
        "implementation_v1": {
            "marker": marker_v1,
            "auto_commit": auto_commit_v1,
            "staging_branch_sha": staging_sha_v1,
            "staging_preview_contains_marker": marker_v1 in staging_preview_v1,
        },
        "production": {
            "deploy_response": deploy_prod,
            "status_after_promote": status_prod_ready,
            "production_sha_after_promote": production_sha_v1,
            "preview_contains_v1": marker_v1 in production_preview_v1,
        },
        "implementation_v2": {
            "marker": marker_v2,
            "auto_commit": auto_commit_v2,
            "staging_branch_sha": staging_sha_v2,
            "staging_preview_contains_v2": marker_v2 in staging_preview_v2,
            "staging_status_after_v2": status_after_v2,
        },
        "production_after_v2": {
            "production_sha": production_sha_after_v2,
            "contains_v1": marker_v1 in production_after_v2_body,
            "contains_v2": marker_v2 in production_after_v2_body,
        },
    }


def main() -> int:
    try:
        result = run_e2e()
        print(json.dumps(result, indent=2, ensure_ascii=False))
        return 0
    except Exception as exc:
        print(f"Conversation E2E failed: {exc}")
        return 1


if __name__ == "__main__":
    raise SystemExit(main())

