"""Expert mode routes — project workspace for vibecoded apps."""

import logging

from fastapi import APIRouter, Depends, HTTPException, Request
from fastapi.responses import JSONResponse, RedirectResponse

from .. import config
from ..database import store
from ..deps import get_current_user, templates

logger = logging.getLogger(__name__)

router = APIRouter()


def _check_expert_enabled():
    if not config.EXPERT_MODE_ENABLED:
        raise HTTPException(status_code=404)


def _get_expert_sidebar_data(user_email: str):
    projects = store.list_projects(user_id=user_email)
    return {"projects": projects, "user_email": user_email}


def _project_to_public_dict(project):
    return {
        "id": project.id,
        "name": project.name,
        "slug": project.slug,
        "status": project.status,
        "description": project.description,
        "workflow_phase": project.workflow_phase,
        "created_at": project.created_at.isoformat() if project.created_at else None,
        "updated_at": project.updated_at.isoformat() if project.updated_at else None,
    }


# =============================================================================
# HTML routes
# =============================================================================


@router.get("/expert")
def expert_home(request: Request, user_email: str = Depends(get_current_user)):
    _check_expert_enabled()
    projects = store.list_projects(user_id=user_email)
    sidebar = _get_expert_sidebar_data(user_email)
    return templates.TemplateResponse(
        request,
        "expert/home.html",
        {
            "section": "expert",
            "current_conv": None,
            "projects": projects,
            **sidebar,
        },
    )


@router.get("/expert/nouveau")
def expert_new(request: Request, user_email: str = Depends(get_current_user)):
    """Create a new project and redirect to its workspace."""
    _check_expert_enabled()
    project = store.create_project(name="Nouvelle app", user_id=user_email)
    conv = store.create_conversation(user_id=user_email, conv_type="expert", project_id=project.id)
    return RedirectResponse(f"/expert/{project.slug}/{conv.id}", status_code=302)


@router.get("/expert/{slug}")
def expert_project(slug: str, request: Request, user_email: str = Depends(get_current_user)):
    """Redirect to latest conversation for this project."""
    _check_expert_enabled()
    project = store.get_project_by_slug(slug)
    if not project:
        raise HTTPException(status_code=404)

    conversations = store.list_project_conversations(project.id)
    if conversations:
        return RedirectResponse(f"/expert/{slug}/{conversations[0].id}", status_code=302)

    conv = store.create_conversation(user_id=user_email, conv_type="expert", project_id=project.id)
    return RedirectResponse(f"/expert/{slug}/{conv.id}", status_code=302)


@router.get("/expert/{slug}/{conv_id}")
def expert_conversation(
    slug: str,
    conv_id: str,
    request: Request,
    user_email: str = Depends(get_current_user),
):
    """Render expert workspace with spec panel + chat."""
    _check_expert_enabled()
    project = store.get_project_by_slug(slug)
    if not project:
        raise HTTPException(status_code=404)

    current_conv = store.get_conversation(conv_id, include_messages=False)
    if not current_conv or current_conv.project_id != project.id:
        return RedirectResponse(f"/expert/{slug}", status_code=302)

    project_conversations = store.list_project_conversations(project.id)
    sidebar = _get_expert_sidebar_data(user_email)

    return templates.TemplateResponse(
        request,
        "expert/workspace.html",
        {
            "section": "expert",
            "project": project,
            "current_conv": current_conv,
            "project_conversations": project_conversations,
            **sidebar,
        },
    )


# =============================================================================
# API routes
# =============================================================================


@router.post("/api/expert/projects")
async def api_create_project(request: Request, user_email: str = Depends(get_current_user)):
    _check_expert_enabled()
    data = await request.json()
    name = (data.get("name") or "").strip() or "Nouvelle app"
    description = (data.get("description") or "").strip() or None

    project = store.create_project(name=name, user_id=user_email, description=description)
    conv = store.create_conversation(user_id=user_email, conv_type="expert", project_id=project.id)

    # Try to initialize .specify/ if the skill exists
    try:
        from skills.speckit_init.scripts.init_project import init_specify
        init_specify(str(config.PROJECTS_DIR / project.slug))
    except ImportError:
        logger.debug("speckit_init skill not available, skipping .specify/ init")
    except Exception:
        logger.warning("Failed to init .specify/ for project %s", project.id, exc_info=True)

    return JSONResponse(
        {
            "project": _project_to_public_dict(project),
            "conversation_id": conv.id,
            "redirect": f"/expert/{project.slug}/{conv.id}",
        },
        status_code=201,
    )


@router.patch("/api/expert/projects/{project_id}")
async def api_update_project(project_id: str, request: Request, user_email: str = Depends(get_current_user)):
    _check_expert_enabled()
    project = store.get_project(project_id)
    if not project:
        return JSONResponse({"error": "Project not found"}, status_code=404)

    data = await request.json()
    updates = {}
    for field in ("name", "description", "spec", "status"):
        if field in data:
            updates[field] = data[field]

    if not updates:
        return JSONResponse({"error": "No valid fields to update"}, status_code=400)

    store.update_project(project_id, **updates)
    updated = store.get_project(project_id)
    return JSONResponse({"project": _project_to_public_dict(updated)})


@router.post("/api/expert/projects/{project_id}/conversations")
def api_new_conversation(project_id: str, user_email: str = Depends(get_current_user)):
    _check_expert_enabled()
    project = store.get_project(project_id)
    if not project:
        return JSONResponse({"error": "Project not found"}, status_code=404)

    conv = store.create_conversation(user_id=user_email, conv_type="expert", project_id=project.id)
    return JSONResponse({
        "id": conv.id,
        "redirect": f"/expert/{project.slug}/{conv.id}",
    })


@router.get("/api/expert/projects/{project_id}/spec-files")
def api_spec_files(project_id: str, user_email: str = Depends(get_current_user)):
    _check_expert_enabled()
    project = store.get_project(project_id)
    if not project:
        return JSONResponse({"error": "Project not found"}, status_code=404)

    project_dir = config.PROJECTS_DIR / project.slug
    specs_dir = project_dir / ".specify" / "specs"

    result = {"spec": None, "plan": None, "tasks": None, "checklist": None}

    if not specs_dir.exists():
        return JSONResponse(result)

    # Find latest version directory
    version_dirs = sorted(
        [d for d in specs_dir.iterdir() if d.is_dir()],
        key=lambda d: d.name,
        reverse=True,
    )
    if not version_dirs:
        return JSONResponse(result)

    latest = version_dirs[0]
    for artifact in result:
        filepath = latest / f"{artifact}.md"
        if filepath.exists():
            result[artifact] = filepath.read_text()

    return JSONResponse(result)
