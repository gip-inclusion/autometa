"""Routes for Recettes — test features on existing PDI apps.

Agent handles deploy (via Expert conversation).
PR creation is a guarded pipeline: check -> rebase -> review -> create.
"""

import logging
import subprocess
import threading
from dataclasses import asdict

from fastapi import APIRouter, Depends, HTTPException, Request
from fastapi.responses import JSONResponse
from starlette.responses import Response

from .. import config
from ..database import store
from ..deps import get_current_user, templates

logger = logging.getLogger(__name__)

router = APIRouter()


def _require_recettes():
    if not config.RECETTES_ENABLED:
        raise HTTPException(404, "Recettes not enabled")


@router.get("/recettes")
def recettes_home(request: Request, user: str = Depends(get_current_user)):
    _require_recettes()
    return templates.TemplateResponse(request, "recettes/home.html", {
        "recettes": store.list_recettes(user_id=user),
        "section": "recettes",
    })


@router.get("/recettes/{recette_id}")
def recettes_detail(request: Request, recette_id: str, user: str = Depends(get_current_user)):
    _require_recettes()
    recette = store.get_recette(recette_id)
    if not recette:
        raise HTTPException(404)
    project = store.get_project(recette.project_id) if recette.project_id else None
    convs = store.list_project_conversations(project.id) if project else []
    return templates.TemplateResponse(request, "recettes/detail.html", {
        "recette": recette,
        "project": project,
        "conversations": convs,
        "section": "recettes",
    })


@router.post("/api/recettes")
async def api_create(request: Request, user: str = Depends(get_current_user)):
    _require_recettes()
    data = await request.json()
    github_repo = data.get("github_repo", "").strip()
    name = data.get("name", "") or github_repo.split("/")[-1]
    branch = data.get("branch", "main")

    if not github_repo or "/" not in github_repo:
        return JSONResponse({"error": "Format: owner/repo"}, status_code=400)
    if not config.GITHUB_TOKEN:
        return JSONResponse({"error": "GITHUB_TOKEN not configured"}, status_code=503)

    recette = store.create_recette(user_id=user, name=name, github_repo=github_repo)
    store.update_recette(recette.id, branch_a=branch)

    project = store.create_project(
        user_id=user, name=f"[Recette] {name}",
        description=f"Test features on {github_repo}",
    )
    store.update_recette(recette.id, project_id=project.id)

    conv = store.create_conversation(
        user_id=user, conv_type="project", project_id=project.id,
    )
    store.update_conversation(conv.id, title="Setup / Deploy (A)")

    def _clone():
        from lib import recettes as rec
        workdir = config.RECETTES_DIR / recette.id
        try:
            rec.clone_repo(github_repo, recette.slug, workdir)
            if branch != "main":
                rec.checkout_branch(workdir, branch)
            store.update_recette(recette.id, status="cloned")
        except Exception:
            store.update_recette(recette.id, status="error")
            logger.exception("Clone failed for %s", github_repo)

    threading.Thread(target=_clone, daemon=True).start()

    return JSONResponse({
        "recette": asdict(recette),
        "project_id": project.id,
        "conversation_id": conv.id,
        "redirect": f"/recettes/{recette.id}",
    }, status_code=202)


@router.post("/api/recettes/{recette_id}/branch-b")
async def api_set_branch_b(request: Request, recette_id: str):
    _require_recettes()
    data = await request.json()
    branch = data.get("branch", "").strip()
    if not branch:
        return JSONResponse({"error": "branch required"}, status_code=400)

    recette = store.get_recette(recette_id)
    if not recette:
        return JSONResponse({"error": "Not found"}, status_code=404)

    from lib import recettes as rec
    main_workdir = config.RECETTES_DIR / recette.id
    worktree_path = config.RECETTES_DIR / f"{recette.id}-b"

    if worktree_path.exists():
        rec.remove_worktree(main_workdir, worktree_path)

    try:
        rec.create_worktree(main_workdir, branch, worktree_path)
    except Exception as e:
        return JSONResponse({"error": f"Worktree failed: {e}"}, status_code=500)

    conv_b_id = None
    if recette.project_id:
        conv_b = store.create_conversation(
            user_id=recette.user_id, conv_type="project", project_id=recette.project_id,
        )
        store.update_conversation(conv_b.id, title=f"Feature (B) — {branch}")
        conv_b_id = conv_b.id

    store.update_recette(recette_id, branch_b=branch, pr_status=None, pr_url=None)
    return JSONResponse({"status": "ok", "branch_b": branch, "conversation_id": conv_b_id})


@router.delete("/api/recettes/{recette_id}/branch-b")
def api_remove_branch_b(recette_id: str):
    _require_recettes()
    recette = store.get_recette(recette_id)
    if not recette:
        return JSONResponse({"error": "Not found"}, status_code=404)

    from lib import recettes as rec
    rec.remove_worktree(config.RECETTES_DIR / recette.id,
                        config.RECETTES_DIR / f"{recette.id}-b")
    store.update_recette(recette_id, branch_b=None, port_b=None,
                         deploy_url_b=None, pr_status=None, pr_url=None)
    return JSONResponse({"status": "removed"})


@router.post("/api/recettes/{recette_id}/deploy/{side}")
def api_deploy(recette_id: str, side: str):
    """Stub -- the agent handles deploy via Expert conversation."""
    _require_recettes()
    if side not in ("a", "b"):
        return JSONResponse({"error": "side must be 'a' or 'b'"}, status_code=400)
    recette = store.get_recette(recette_id)
    if not recette:
        return JSONResponse({"error": "Not found"}, status_code=404)
    return JSONResponse({"status": recette.status, "side": side})


@router.get("/api/recettes/{recette_id}/logs/{side}")
def api_logs(recette_id: str, side: str):
    _require_recettes()
    recette = store.get_recette(recette_id)
    if not recette:
        return JSONResponse({"error": "Not found"}, status_code=404)

    project_name = f"recette-{recette.slug}-{side}"
    result = subprocess.run(
        ["docker", "compose", "-p", project_name, "logs", "--tail", "100", "--no-color"],
        capture_output=True, text=True, timeout=15,
    )
    return JSONResponse({"logs": result.stdout or result.stderr})


@router.post("/api/recettes/{recette_id}/pr/check")
def api_pr_check(recette_id: str):
    """Step 1: Run quality checks on branch B."""
    _require_recettes()
    recette = store.get_recette(recette_id)
    if not recette or not recette.branch_b:
        return JSONResponse({"error": "Set branch B first"}, status_code=400)

    store.update_recette(recette_id, pr_status="checking")

    from lib import recettes as rec
    workdir = config.RECETTES_DIR / f"{recette.id}-b"
    if not workdir.exists():
        workdir = config.RECETTES_DIR / recette.id

    result = rec.run_quality_checks(workdir)
    new_status = "checks_passed" if result["status"] == "passed" else "checks_failed"
    store.update_recette(recette_id, pr_status=new_status)
    return JSONResponse({"pr_status": new_status, "output": result["output"]})


@router.post("/api/recettes/{recette_id}/pr/rebase")
def api_pr_rebase(recette_id: str):
    """Step 2: Rebase branch B onto main."""
    _require_recettes()
    recette = store.get_recette(recette_id)
    if not recette or not recette.branch_b:
        return JSONResponse({"error": "Set branch B first"}, status_code=400)
    if recette.pr_status not in ("checks_passed", "checks_failed"):
        return JSONResponse({"error": "Run quality checks first"}, status_code=403)

    from lib import recettes as rec
    workdir = config.RECETTES_DIR / f"{recette.id}-b"
    if not workdir.exists():
        workdir = config.RECETTES_DIR / recette.id

    result = rec.rebase_on_main(workdir, recette.branch_b)
    new_status = "rebased" if result["status"] == "ok" else "checks_failed"
    store.update_recette(recette_id, pr_status=new_status)
    return JSONResponse({"pr_status": new_status, "output": result["output"]})


@router.get("/api/recettes/{recette_id}/pr/diff")
def api_pr_diff(recette_id: str):
    """Step 3: Show diff for review."""
    _require_recettes()
    recette = store.get_recette(recette_id)
    if not recette or not recette.branch_b:
        return JSONResponse({"error": "Set branch B first"}, status_code=400)

    from lib import recettes as rec
    workdir = config.RECETTES_DIR / f"{recette.id}-b"
    if not workdir.exists():
        workdir = config.RECETTES_DIR / recette.id

    result = rec.get_diff_summary(workdir, recette.branch_b)
    return JSONResponse(result)


@router.post("/api/recettes/{recette_id}/pr/create")
async def api_pr_create(request: Request, recette_id: str):
    """Step 4: Create PR on GitHub. REQUIRES pr_status == 'rebased'."""
    _require_recettes()
    recette = store.get_recette(recette_id)
    if not recette:
        return JSONResponse({"error": "Not found"}, status_code=404)

    if recette.pr_status != "rebased":
        return JSONResponse(
            {"error": f"Cannot create PR: status is '{recette.pr_status}'. "
                      "Run checks and rebase first."},
            status_code=403,
        )

    data = await request.json()
    title = data.get("title", f"feat: {recette.branch_b}")
    body = data.get("body", "")

    from lib import recettes as rec
    try:
        pr_url = rec.push_and_create_pr(recette, title=title, body=body)
    except (ValueError, Exception) as e:
        return JSONResponse({"error": str(e)}, status_code=500)

    store.update_recette(recette_id, pr_url=pr_url, pr_status="pr_created")
    return JSONResponse({"status": "created", "pr_url": pr_url})


@router.get("/recettes/{recette_id}/preview/{side}/{path:path}")
@router.get("/recettes/{recette_id}/preview/{side}/")
def recettes_preview(request: Request, recette_id: str, side: str, path: str = ""):
    _require_recettes()
    if side not in ("a", "b"):
        raise HTTPException(400, "side must be 'a' or 'b'")

    recette = store.get_recette(recette_id)
    if not recette:
        raise HTTPException(404)

    deploy_url = recette.deploy_url_a if side == "a" else recette.deploy_url_b
    if not deploy_url:
        raise HTTPException(503, f"Side {side} not deployed")

    import httpx
    upstream = f"{deploy_url}/{path}"
    if request.url.query:
        upstream += f"?{request.url.query}"

    try:
        resp = httpx.get(
            upstream,
            headers={k: v for k, v in request.headers.items()
                     if k.lower() not in ("host", "connection")},
            timeout=30,
            follow_redirects=False,
        )
    except httpx.HTTPError as e:
        raise HTTPException(502, f"Upstream error: {e}")

    excluded = {"transfer-encoding", "connection", "content-encoding"}
    headers = {k: v for k, v in resp.headers.items() if k.lower() not in excluded}
    return Response(content=resp.content, status_code=resp.status_code, headers=headers)
