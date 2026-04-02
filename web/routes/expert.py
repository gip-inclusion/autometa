"""Expert mode routes — project workspace for vibecoded apps."""

import asyncio
import logging
import subprocess
import threading
from urllib.parse import urljoin, urlsplit, urlunsplit

import httpx
from fastapi import APIRouter, Depends, HTTPException, Request, Response
from fastapi.responses import HTMLResponse, JSONResponse, RedirectResponse

from .. import config
from ..database import store
from ..deps import get_current_user, templates
from lib.expert_git import (
    authenticated_clone_url,
    commit_and_push_staging_if_changed,
    ensure_local_git_repo as ensure_project_local_git_repo,
    ensure_project_branches,
    extract_owner_repo_from_url,
    promote_staging_to_production,
    run_git as _run_git,
)

logger = logging.getLogger(__name__)

router = APIRouter()


def _check_expert_enabled():
    if not config.EXPERT_MODE_ENABLED:
        raise HTTPException(status_code=404)


def _get_expert_sidebar_data(user_email: str):
    projects = store.list_projects(user_id=user_email)
    return {"projects": projects, "user_email": user_email}


def _normalize_deploy_url(raw_domains) -> str | None:
    if isinstance(raw_domains, list):
        domain = next((d for d in raw_domains if d), None)
    else:
        domain = raw_domains

    if not domain:
        return None

    domain = str(domain).strip()
    if not domain:
        return None

    if domain.startswith("http://") or domain.startswith("https://"):
        return domain

    return f"http://{domain}"


def _publicize_deploy_url(url: str | None, request: Request | None = None) -> str | None:
    """Return a browser-reachable URL for the current requester."""
    if not url:
        return url

    parsed = urlsplit(url)
    host = (parsed.hostname or "").lower()
    if host not in {"localhost", "127.0.0.1"}:
        return url

    target_host = config.EXPERT_DEPLOY_PUBLIC_HOST or ""
    if not target_host and request is not None:
        req_host = (request.headers.get("host") or "").split(":", 1)[0].strip()
        if req_host and req_host not in {"localhost", "127.0.0.1", "testserver"}:
            target_host = req_host

    if not target_host:
        return url

    netloc = f"{target_host}:{parsed.port}" if parsed.port else target_host
    scheme = parsed.scheme or "http"
    return urlunsplit((scheme, netloc, parsed.path, parsed.query, parsed.fragment))


def _project_to_public_dict(project, request: Request | None = None):
    d = {
        "id": project.id,
        "name": project.name,
        "slug": project.slug,
        "status": project.status,
        "description": project.description,
        "workflow_phase": project.workflow_phase,
        "gitea_url": project.gitea_url,
        "staging_deploy_url": _publicize_deploy_url(project.staging_deploy_url, request),
        "production_deploy_url": _publicize_deploy_url(project.production_deploy_url, request),
        "staging_preview_url": _preview_url(project.slug, "staging"),
        "production_preview_url": _preview_url(project.slug, "production"),
        "created_at": project.created_at.isoformat() if project.created_at else None,
        "updated_at": project.updated_at.isoformat() if project.updated_at else None,
    }
    return d


def _preview_base_path(slug: str, environment: str) -> str:
    return f"/expert/{slug}/preview/{environment}"


def _preview_url(slug: str, environment: str) -> str:
    return f"{_preview_base_path(slug, environment)}/"


def _environment_deploy_url(project, environment: str) -> str | None:
    if environment == "staging":
        return project.staging_deploy_url
    if environment == "production":
        return project.production_deploy_url
    return None


def _internal_proxy_url(url: str) -> str:
    """Rewrite localhost URLs for container-side proxy access."""
    parsed = urlsplit(url)
    host = (parsed.hostname or "").lower()
    if host not in {"localhost", "127.0.0.1"}:
        return url

    netloc = "host.docker.internal"
    if parsed.port:
        netloc = f"{netloc}:{parsed.port}"
    return urlunsplit((parsed.scheme or "http", netloc, parsed.path, parsed.query, parsed.fragment))


def _rewrite_proxy_html(content: str, slug: str, environment: str) -> str:
    """Rewrite root-relative links in proxied HTML to stay under preview path."""
    base = _preview_base_path(slug, environment)
    content = content.replace('href="/', f'href="{base}/')
    content = content.replace("href='/", f"href='{base}/")
    content = content.replace('src="/', f'src="{base}/')
    content = content.replace("src='/", f"src='{base}/")
    content = content.replace('action="/', f'action="{base}/')
    content = content.replace("action='/", f"action='{base}/")
    if "<head" in content and "<base " not in content:
        head_close = content.find(">", content.find("<head"))
        if head_close != -1:
            injection = f'<base href="{_preview_url(slug, environment)}">'
            content = content[: head_close + 1] + injection + content[head_close + 1 :]
    if "</body>" in content:
        patch_script = (
            f'<script>(function(){{'
            f'var B="{base}";'
            f'var _fetch=window.fetch;'
            f'window.fetch=function(u,o){{'
            f'if(typeof u==="string"&&u.startsWith("/")&&!u.startsWith(B))u=B+u;'
            f'return _fetch.call(this,u,o)}};'
            f'var _open=XMLHttpRequest.prototype.open;'
            f'XMLHttpRequest.prototype.open=function(m,u){{'
            f'if(typeof u==="string"&&u.startsWith("/")&&!u.startsWith(B))u=B+u;'
            f'return _open.apply(this,arguments)}};'
            f'var _set=Object.getOwnPropertyDescriptor(HTMLFormElement.prototype,"action").set;'
            f'Object.defineProperty(HTMLFormElement.prototype,"action",{{'
            f'set:function(v){{if(typeof v==="string"&&v.startsWith("/")&&!v.startsWith(B))v=B+v;_set.call(this,v)}},'
            f'get:function(){{return this.getAttribute("action")||""}}}})'
            f'}})();</script>'
        )
        content = content.replace("</body>", patch_script + "</body>")
    return content


def _detect_exposed_port(workdir) -> int:
    """Read EXPOSE from Dockerfile to determine the container port."""
    import re
    dockerfile = workdir / "Dockerfile"
    if dockerfile.exists():
        for line in dockerfile.read_text().splitlines():
            m = re.match(r"^\s*EXPOSE\s+(\d+)", line, re.IGNORECASE)
            if m:
                return int(m.group(1))
    return 5000


def _pick_host_port(start: int = 18080, end: int = 19999, reserved_ports: set[int] | None = None) -> int:
    """Pick a free host port for direct app exposure."""
    reserved = reserved_ports or set()
    for port in range(start, end + 1):
        if port in reserved:
            continue
        return port
    raise RuntimeError("No free host port available")


def _reserved_local_deploy_ports(exclude_project_id: str | None = None) -> set[int]:
    """Collect host ports already assigned in project deploy URLs."""
    used = set()
    for project in store.list_projects(limit=2000):
        if exclude_project_id and project.id == exclude_project_id:
            continue
        for candidate in (
            project.staging_deploy_url,
            project.production_deploy_url,
        ):
            if not candidate:
                continue
            parsed = urlsplit(candidate)
            if parsed.hostname != "localhost" or not parsed.port:
                continue
            used.add(parsed.port)
    return used


def _ensure_deployable_repo(project):
    """Ensure repo contains Dockerfile + docker-compose.yml for deployment."""
    workdir = config.PROJECTS_DIR / project.id
    if not (workdir / ".git").exists():
        return False

    dockerfile = workdir / "Dockerfile"
    compose_file = workdir / "docker-compose.yml"

    if dockerfile.exists() and compose_file.exists():
        return False

    created_files = []

    if not dockerfile.exists():
        dockerfile.write_text(
            "FROM python:3.12-slim\n"
            "WORKDIR /app\n"
            "COPY . /app\n"
            "EXPOSE 5000\n"
            'CMD ["python", "-m", "http.server", "5000", "--bind", "0.0.0.0"]\n'
        )
        created_files.append("Dockerfile")

    if not compose_file.exists():
        container_port = _detect_exposed_port(workdir)
        compose_file.write_text(
            "services:\n"
            "  app:\n"
            "    build: .\n"
            "    ports:\n"
            f'      - "${{HOST_PORT:-{container_port}}}:{container_port}"\n'
            "    healthcheck:\n"
            f'      test: ["CMD", "curl", "-f", "http://localhost:{container_port}/"]\n'
            "      interval: 10s\n"
            "      timeout: 5s\n"
            "      retries: 3\n"
            "    restart: unless-stopped\n"
        )
        created_files.append("docker-compose.yml")

    gitignore = workdir / ".gitignore"
    if not gitignore.exists():
        gitignore.write_text(
            "__pycache__/\n*.pyc\n.env\n.venv/\nnode_modules/\n.DS_Store\n*.egg-info/\ndist/\nbuild/\n"
        )
        created_files.append(".gitignore")

    pyproject = workdir / "pyproject.toml"
    if not pyproject.exists():
        pyproject.write_text(
            '[tool.ruff]\ntarget-version = "py312"\nline-length = 120\n\n'
            "[tool.ruff.lint]\n"
            'select = ["E", "F", "W", "I", "UP", "S", "B"]\n'
            'ignore = ["S101"]\n'
        )
        created_files.append("pyproject.toml")

    index_html = workdir / "index.html"
    if not index_html.exists() and "Dockerfile" in created_files:
        safe_name = (project.name or project.slug or "Application").replace("<", "").replace(">", "")
        index_html.write_text(
            '<!doctype html>\n<html lang="fr">\n'
            '<head><meta charset="utf-8"><meta name="viewport" content="width=device-width,initial-scale=1">'
            f"<title>{safe_name}</title></head>\n"
            '<body style="font-family: sans-serif; margin: 2rem;">\n'
            f"<h1>{safe_name}</h1>\n"
            "<p>L'application est deployee.</p>\n"
            "</body></html>\n"
        )
        created_files.append("index.html")

    if not created_files:
        return False

    try:
        _run_git(workdir, "config", "user.email", "matometa@localhost")
        _run_git(workdir, "config", "user.name", "Matometa")
        _run_git(workdir, "add", *created_files)
        diff = _run_git(workdir, "diff", "--cached", "--name-only")
        if not diff:
            return False

        _run_git(workdir, "commit", "-m", "chore: add deployment bootstrap")
        current_branch = _run_git(workdir, "rev-parse", "--abbrev-ref", "HEAD") or "main"
        _run_git(workdir, "push", "origin", current_branch)
        logger.info("Bootstrapped deploy files for project %s: %s", project.id, created_files)
        return True
    except Exception:
        logger.exception("Failed to bootstrap deploy files for project %s", project.id)
        return False


def _ensure_local_git_repo(project):
    """Ensure project working directory is a valid local git clone."""
    return ensure_project_local_git_repo(project)


def _try_create_gitea_repo(project, raise_on_error: bool = False) -> bool:
    """Auto-create a Gitea repo and clone it into the project working directory."""
    if not config.GITEA_API_TOKEN:
        if raise_on_error:
            raise RuntimeError("GITEA_API_TOKEN not configured")
        return False
    try:
        from lib.gitea import GiteaClient

        gitea = GiteaClient()
        try:
            repo = gitea.create_repo(
                name=project.slug,
                description=project.description or "",
            )
        except httpx.HTTPStatusError as exc:
            if exc.response is not None and exc.response.status_code == 409:
                repo = gitea.get_repo(config.GITEA_ORG, project.slug)
            else:
                raise
        gitea_id = repo.get("id")
        gitea_url = repo.get("html_url", "")
        full_name = repo.get("full_name", "")

        workdir = config.PROJECTS_DIR / project.id
        if full_name and not (workdir / ".git").exists():
            clone_url = authenticated_clone_url(full_name)
            workdir.mkdir(parents=True, exist_ok=True)

            has_files = any(workdir.iterdir())
            if has_files:
                subprocess.run(["git", "init"], cwd=workdir, check=True, capture_output=True, timeout=10)
                subprocess.run(["git", "remote", "add", "origin", clone_url], cwd=workdir, check=True, capture_output=True, timeout=10)
            else:
                subprocess.run(
                    ["git", "clone", clone_url, str(workdir)],
                    check=True, capture_output=True, timeout=30,
                )

            subprocess.run(["git", "config", "user.email", "matometa@localhost"], cwd=workdir, check=True, capture_output=True)
            subprocess.run(["git", "config", "user.name", "Matometa"], cwd=workdir, check=True, capture_output=True)

            if has_files:
                subprocess.run(["git", "add", "-A"], cwd=workdir, check=True, capture_output=True, timeout=10)
                subprocess.run(["git", "commit", "-m", "chore: initial commit"], cwd=workdir, check=True, capture_output=True, timeout=10)
                subprocess.run(["git", "push", "-u", "origin", "main"], cwd=workdir, check=True, capture_output=True, timeout=30)

        ensure_project_branches(project)

        store.update_project(
            project.id,
            gitea_repo_id=gitea_id,
            gitea_url=gitea_url,
            staging_branch=project.staging_branch,
            production_branch=project.production_branch,
            status="active",
        )

        logger.info("Auto-created Gitea repo %s for project %s", gitea_url, project.id)
        return True
    except Exception:
        logger.exception("Failed to auto-create Gitea repo for project %s", project.id)
        if raise_on_error:
            raise
        return False


def _sync_legacy_deploy_fields(project_id: str, *, deploy_url: str | None):
    """Keep deploy fields populated after deploy operations."""
    if deploy_url is not None:
        store.update_project(project_id, staging_deploy_url=deploy_url)


def _use_docker_deploy() -> bool:
    """Use direct Docker deploy when Docker socket is available."""
    from lib.docker_deploy import docker_available
    return docker_available()


def _docker_deploy_staging(project_id: str, project, request: Request):
    """Deploy staging via direct Docker Compose."""
    from lib import docker_deploy

    _ensure_local_git_repo(project)
    ensure_project_branches(project)
    _ensure_deployable_repo(project)
    commit_and_push_staging_if_changed(project)

    result = docker_deploy.deploy(project_id, "staging")
    updated = store.get_project(project_id)
    return JSONResponse({
        "status": "staging_deploying" if result["status"] == "running" else result["status"],
        "staging": {
            "deploy_url": result.get("deploy_url"),
            "detail": result,
        },
        "project": _project_to_public_dict(updated or project, request),
    }, status_code=200 if result["status"] == "running" else 500)


def _docker_deploy_production(project_id: str, project, request: Request):
    """Deploy staging + production via direct Docker Compose."""
    from lib import docker_deploy

    _ensure_local_git_repo(project)
    ensure_project_branches(project)
    _ensure_deployable_repo(project)
    commit_and_push_staging_if_changed(project)

    staging_result = docker_deploy.deploy(project_id, "staging")
    refreshed = store.get_project(project_id) or project
    promotion = promote_staging_to_production(refreshed)
    prod_result = docker_deploy.deploy(project_id, "production")

    updated = store.get_project(project_id)
    return JSONResponse({
        "status": "production_deploying" if prod_result["status"] == "running" else prod_result["status"],
        "promotion": promotion,
        "staging": {
            "deploy_url": staging_result.get("deploy_url"),
            "detail": staging_result,
        },
        "production": {
            "deploy_url": prod_result.get("deploy_url"),
            "detail": prod_result,
        },
        "project": _project_to_public_dict(updated or refreshed, request),
    }, status_code=200 if prod_result["status"] == "running" else 500)


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

    try:
        from skills.speckit_init.scripts.init_project import init_specify
        init_specify(str(config.PROJECTS_DIR / project.slug))
    except ImportError:
        logger.debug("speckit_init skill not available, skipping .specify/ init")
    except Exception:
        logger.warning("Failed to init .specify/ for project %s", project.id, exc_info=True)

    def _background_setup():
        try:
            _try_create_gitea_repo(project)
        except Exception:
            logger.exception("Background Gitea setup failed for %s", project.id)
    threading.Thread(target=_background_setup, daemon=True).start()

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


@router.get("/expert/{slug}/settings")
def expert_settings(slug: str, request: Request, user_email: str = Depends(get_current_user)):
    """Project settings page."""
    _check_expert_enabled()
    project = store.get_project_by_slug(slug)
    if not project:
        return RedirectResponse("/expert", status_code=302)

    from lib import scaleway_publish
    return templates.TemplateResponse(request, "expert/settings.html", {
        "project": project,
        "section": "expert",
        "scaleway_available": scaleway_publish.available(),
    })


@router.api_route("/expert/{slug}/preview/{environment}/", methods=["GET", "HEAD", "POST", "PUT", "PATCH", "DELETE"])
@router.api_route("/expert/{slug}/preview/{environment}/{subpath:path}", methods=["GET", "HEAD", "POST", "PUT", "PATCH", "DELETE"])
async def expert_project_preview(slug: str, environment: str, request: Request, subpath: str = ""):
    """Proxy project preview through Matometa host."""
    _check_expert_enabled()
    if environment not in {"staging", "production"}:
        raise HTTPException(status_code=404)

    project = store.get_project_by_slug(slug)
    if not project:
        raise HTTPException(status_code=404)

    upstream_base = _environment_deploy_url(project, environment)
    if not upstream_base:
        return Response(content="Application non deployee pour cet environnement.", status_code=404)

    parsed_subpath = urlsplit(subpath)
    if parsed_subpath.scheme or parsed_subpath.netloc:
        raise HTTPException(status_code=400)

    safe_subpath = parsed_subpath.path.lstrip("/")
    target_url = urljoin(upstream_base.rstrip("/") + "/", safe_subpath)
    target_url = _internal_proxy_url(target_url)

    allowed_targets = {
        urlsplit(upstream_base).netloc,
        urlsplit(_internal_proxy_url(upstream_base)).netloc,
    }
    if urlsplit(target_url).netloc not in allowed_targets:
        raise HTTPException(status_code=400)

    hop_by_hop = {
        "connection", "keep-alive", "proxy-authenticate", "proxy-authorization",
        "te", "trailers", "transfer-encoding", "upgrade", "host",
    }
    upstream_headers = {
        key: value
        for key, value in request.headers.items()
        if key.lower() not in hop_by_hop
    }

    request_body = await request.body()
    request_method = request.method
    request_params = dict(request.query_params)

    try:
        upstream_resp = await asyncio.to_thread(
            lambda: httpx.request(
                method=request_method,
                url=target_url,
                params=request_params,
                headers=upstream_headers,
                content=request_body,
                follow_redirects=False,
                timeout=30,
            )
        )
    except httpx.RequestError as exc:
        logger.warning("Preview proxy error for %s/%s: %s", slug, environment, exc)

        container_status = "inconnu"
        if _use_docker_deploy():
            try:
                from lib import docker_deploy
                st = docker_deploy.status(project.id, environment)
                container_status = st.get("status", "unknown")
                if container_status in ("exited", "stopped", "error"):
                    docker_deploy.restart(project.id, environment)
                    container_status = "redemarrage..."
            except Exception:
                container_status = "erreur Docker"

        deploy_endpoint = (
            f"/api/expert/projects/{project.id}/deploy-staging"
            if environment == "staging"
            else f"/api/expert/projects/{project.id}/deploy"
        )

        return HTMLResponse(
            f'<!doctype html><html><head><meta charset="utf-8"><title>Preview indisponible</title>'
            f'<style>body{{font-family:system-ui;max-width:600px;margin:80px auto;text-align:center;color:#333}}'
            f'.status{{background:#f8d7da;padding:12px 20px;border-radius:8px;margin:20px 0;font-size:14px}}'
            f'.actions{{display:flex;gap:8px;justify-content:center;flex-wrap:wrap}}'
            f'button{{background:#0d6efd;color:#fff;border:none;padding:10px 24px;border-radius:6px;cursor:pointer;font-size:14px}}'
            f'button:hover{{background:#0b5ed7}}'
            f'.btn-secondary{{background:#6c757d}}'
            f'a{{color:#0d6efd}}</style></head>'
            f'<body><h2>Application indisponible</h2>'
            f'<p>L\'application <b>{slug}</b> ({environment}) ne repond pas.</p>'
            f'<div class="status">Statut conteneur : <b>{container_status}</b></div>'
            f'<div class="actions">'
            f'<button class="btn-secondary" onclick="fetch(\'/api/expert/projects/{project.id}/restart/{environment}\','
            f'{{method:\'POST\'}}).then(()=>setTimeout(()=>location.reload(),3000))">'
            f'Redemarrer</button>'
            f'<button onclick="fetch(\'{deploy_endpoint}\',{{method:\'POST\'}}).then(()=>setTimeout(()=>location.reload(),5000))">'
            f'Redeployer</button>'
            f'</div>'
            f'<p style="margin-top:20px"><a href="/expert/{slug}">Retour au projet</a></p></body></html>',
            status_code=502,
        )

    response_headers = {}
    location = upstream_resp.headers.get("Location")
    if location:
        parsed_loc = urlsplit(location)
        parsed_target = urlsplit(upstream_base)
        parsed_internal_target = urlsplit(_internal_proxy_url(upstream_base))
        if location.startswith("/"):
            rewritten = _preview_base_path(slug, environment) + location
            response_headers["Location"] = rewritten
        elif parsed_loc.netloc in {parsed_target.netloc, parsed_internal_target.netloc}:
            rewritten = _preview_base_path(slug, environment) + (parsed_loc.path or "/")
            if parsed_loc.query:
                rewritten = f"{rewritten}?{parsed_loc.query}"
            response_headers["Location"] = rewritten
        else:
            response_headers["Location"] = location

    for key, value in upstream_resp.headers.items():
        key_lower = key.lower()
        if key_lower in hop_by_hop or key_lower in {"content-length", "location"}:
            continue
        response_headers[key] = value

    body = upstream_resp.content
    content_type = (upstream_resp.headers.get("Content-Type") or "").lower()
    if "text/html" in content_type and body:
        charset = upstream_resp.encoding or "utf-8"
        try:
            html = body.decode(charset, errors="replace")
            body = _rewrite_proxy_html(html, slug, environment).encode(charset, errors="replace")
        except Exception:
            logger.exception("Failed to rewrite preview HTML for %s/%s", slug, environment)

    return Response(content=body, status_code=upstream_resp.status_code, headers=response_headers)


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

    try:
        from skills.speckit_init.scripts.init_project import init_specify
        init_specify(str(config.PROJECTS_DIR / project.slug))
    except ImportError:
        logger.debug("speckit_init skill not available, skipping .specify/ init")
    except Exception:
        logger.warning("Failed to init .specify/ for project %s", project.id, exc_info=True)

    def _background_setup():
        try:
            _try_create_gitea_repo(project)
        except Exception:
            logger.exception("Background Gitea setup failed for %s", project.id)
    threading.Thread(target=_background_setup, daemon=True).start()

    return JSONResponse(
        {
            "project": _project_to_public_dict(project, request),
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
    for field in ("name", "description", "spec", "status", "staging_branch", "production_branch"):
        if field in data:
            updates[field] = data[field]

    if not updates:
        return JSONResponse({"error": "No valid fields to update"}, status_code=400)

    store.update_project(project_id, **updates)
    updated = store.get_project(project_id)
    return JSONResponse({"project": _project_to_public_dict(updated, request)})


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


# =============================================================================
# Deploy API routes
# =============================================================================


@router.post("/api/expert/projects/{project_id}/deploy-staging")
def api_deploy_staging_project(project_id: str, request: Request):
    _check_expert_enabled()
    project = store.get_project(project_id)
    if not project:
        return JSONResponse({"error": "Project not found"}, status_code=404)

    if not project.gitea_url:
        try:
            _try_create_gitea_repo(project, raise_on_error=True)
            project = store.get_project(project_id) or project
        except Exception as e:
            logger.exception("Gitea repo creation failed for %s", project_id)
            return JSONResponse({"error": f"Gitea repo creation failed: {e}"}, status_code=500)

    try:
        if not _use_docker_deploy():
            return JSONResponse({"error": "Docker socket not available"}, status_code=503)
        return _docker_deploy_staging(project_id, project, request)
    except Exception as e:
        logger.exception("Staging deploy failed")
        return JSONResponse({"error": str(e)}, status_code=500)


@router.post("/api/expert/projects/{project_id}/deploy")
def api_deploy_project(project_id: str, request: Request):
    """Promote staging to production and deploy."""
    _check_expert_enabled()
    project = store.get_project(project_id)
    if not project:
        return JSONResponse({"error": "Project not found"}, status_code=404)

    if not project.gitea_url:
        try:
            _try_create_gitea_repo(project, raise_on_error=True)
            project = store.get_project(project_id) or project
        except Exception as e:
            logger.exception("Gitea repo creation failed for %s", project_id)
            return JSONResponse({"error": f"Gitea repo creation failed: {e}"}, status_code=500)

    try:
        if not _use_docker_deploy():
            return JSONResponse({"error": "Docker socket not available"}, status_code=503)
        return _docker_deploy_production(project_id, project, request)
    except Exception as e:
        logger.exception("Production deploy failed")
        return JSONResponse({"error": str(e)}, status_code=500)


@router.get("/api/expert/projects/{project_id}/deploy-status")
def api_deploy_status(project_id: str, request: Request):
    """Poll deployment status."""
    _check_expert_enabled()
    project = store.get_project(project_id)
    if not project:
        return JSONResponse({"error": "Project not found"}, status_code=404)

    staging_preview_url = _preview_url(project.slug, "staging") if project.staging_deploy_url else None
    production_preview_url = _preview_url(project.slug, "production") if project.production_deploy_url else None

    if _use_docker_deploy():
        from lib import docker_deploy
        staging_st = docker_deploy.status(project_id, "staging") if project.staging_deploy_url else {"status": "not_deployed"}
        prod_st = docker_deploy.status(project_id, "production") if project.production_deploy_url else {"status": "not_deployed"}

        overall = prod_st.get("status", "not_deployed")
        if overall == "not_deployed":
            overall = staging_st.get("status", "not_deployed")

        primary_url = production_preview_url or staging_preview_url
        return JSONResponse({
            "status": overall,
            "deploy_url": primary_url,
            "staging": {
                "status": staging_st.get("status", "not_deployed"),
                "deploy_url": staging_preview_url,
                "technical_deploy_url": _publicize_deploy_url(project.staging_deploy_url, request),
                "detail": staging_st,
            },
            "production": {
                "status": prod_st.get("status", "not_deployed"),
                "deploy_url": production_preview_url,
                "technical_deploy_url": _publicize_deploy_url(project.production_deploy_url, request),
                "detail": prod_st,
            },
        })

    return JSONResponse({"status": "not_deployed"})


@router.get("/api/expert/projects/{project_id}/logs/{environment}")
def api_project_logs(project_id: str, environment: str):
    """Get container logs for a project environment."""
    _check_expert_enabled()
    if environment not in ("staging", "production"):
        return JSONResponse({"error": "Invalid environment"}, status_code=400)
    if not _use_docker_deploy():
        return JSONResponse({"error": "Direct Docker not available"}, status_code=503)

    from lib import docker_deploy
    log_text = docker_deploy.logs(project_id, environment)
    return JSONResponse({"logs": log_text})


@router.post("/api/expert/projects/{project_id}/restart/{environment}")
def api_project_restart(project_id: str, environment: str):
    """Restart project containers without rebuild."""
    _check_expert_enabled()
    if environment not in ("staging", "production"):
        return JSONResponse({"error": "Invalid environment"}, status_code=400)
    if not _use_docker_deploy():
        return JSONResponse({"error": "Direct Docker not available"}, status_code=503)

    from lib import docker_deploy
    result = docker_deploy.restart(project_id, environment)
    status_code = 200 if result.get("status") == "running" else 500
    return JSONResponse(result, status_code=status_code)


@router.post("/api/expert/projects/{project_id}/stop/{environment}")
def api_project_stop(project_id: str, environment: str):
    """Stop project containers."""
    _check_expert_enabled()
    if environment not in ("staging", "production"):
        return JSONResponse({"error": "Invalid environment"}, status_code=400)
    if not _use_docker_deploy():
        return JSONResponse({"error": "Direct Docker not available"}, status_code=503)

    from lib import docker_deploy
    result = docker_deploy.stop(project_id, environment)
    return JSONResponse(result)


@router.post("/api/expert/projects/{project_id}/retry-gitea")
def api_retry_gitea(project_id: str):
    """Retry Gitea repo creation for a project that failed initial setup."""
    _check_expert_enabled()
    project = store.get_project(project_id)
    if not project:
        return JSONResponse({"error": "Project not found"}, status_code=404)

    if project.gitea_url:
        return JSONResponse({"status": "already_exists", "gitea_url": project.gitea_url})

    try:
        _try_create_gitea_repo(project, raise_on_error=True)
        updated = store.get_project(project_id)
        return JSONResponse({
            "status": "created",
            "gitea_url": updated.gitea_url if updated else None,
        })
    except Exception as e:
        return JSONResponse({"error": str(e)}, status_code=500)


@router.post("/api/expert/projects/{project_id}/publish-scaleway")
def api_publish_scaleway(project_id: str):
    """Publish production app to Scaleway Serverless Containers."""
    _check_expert_enabled()
    from lib import scaleway_publish
    if not scaleway_publish.available():
        return JSONResponse({"error": "Scaleway not configured"}, status_code=503)
    project = store.get_project(project_id)
    if not project:
        return JSONResponse({"error": "Project not found"}, status_code=404)
    result = scaleway_publish.publish(project_id)
    status_code = 200 if result["status"] in ("published", "published_unverified") else 500
    return JSONResponse(result, status_code=status_code)


@router.delete("/api/expert/projects/{project_id}/publish-scaleway")
def api_unpublish_scaleway(project_id: str):
    """Remove app from Scaleway (keeps database)."""
    _check_expert_enabled()
    from lib import scaleway_publish
    result = scaleway_publish.unpublish(project_id)
    return JSONResponse(result)


@router.get("/api/expert/projects/{project_id}/scaleway-status")
def api_scaleway_status(project_id: str):
    """Get Scaleway container status."""
    _check_expert_enabled()
    from lib import scaleway_publish
    result = scaleway_publish.status(project_id)
    return JSONResponse(result)
