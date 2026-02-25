"""Tests for expert-mode projects (database CRUD, API endpoints, context injection)."""

import pytest


@pytest.fixture
def project(app):
    """Create a test project."""
    from web.storage import store
    with app.test_request_context():
        return store.create_project(name="Test App", user_id="dev@example.com", description="A test app")


@pytest.fixture
def project_with_spec(app, project):
    """Create a test project with a spec."""
    from web.storage import store
    with app.test_request_context():
        store.update_project(project.id, spec="# Test Spec\n\nA Flask app.", status="active")
        return store.get_project(project.id)


class TestProjectCRUD:
    """Test project database operations."""

    def test_create_project(self, app, project):
        assert project.id
        assert project.name == "Test App"
        assert project.slug == "test-app"
        assert project.status == "draft"
        assert project.user_id == "dev@example.com"

    def test_create_project_slug_uniqueness(self, app):
        from web.storage import store
        with app.test_request_context():
            p1 = store.create_project(name="Mon App", user_id="a@b.com")
            p2 = store.create_project(name="Mon App", user_id="a@b.com")
            assert p1.slug == "mon-app"
            assert p2.slug == "mon-app-1"
            assert p1.id != p2.id

    def test_create_project_french_chars(self, app):
        from web.storage import store
        with app.test_request_context():
            p = store.create_project(name="Résumé des données", user_id="a@b.com")
            assert p.slug == "resume-des-donnees"

    def test_get_project(self, app, project):
        from web.storage import store
        with app.test_request_context():
            fetched = store.get_project(project.id)
            assert fetched is not None
            assert fetched.name == "Test App"

    def test_get_project_by_slug(self, app, project):
        from web.storage import store
        with app.test_request_context():
            fetched = store.get_project_by_slug("test-app")
            assert fetched is not None
            assert fetched.id == project.id

    def test_get_project_not_found(self, app):
        from web.storage import store
        with app.test_request_context():
            assert store.get_project("nonexistent") is None
            assert store.get_project_by_slug("nonexistent") is None

    def test_update_project(self, app, project):
        from web.storage import store
        with app.test_request_context():
            store.update_project(project.id, name="Renamed", spec="# Spec", status="active")
            updated = store.get_project(project.id)
            assert updated.name == "Renamed"
            assert updated.spec == "# Spec"
            assert updated.status == "active"

    def test_update_project_tech_stack(self, app, project):
        from web.storage import store
        with app.test_request_context():
            store.update_project(project.id, tech_stack={"backend": "flask", "db": "postgres"})
            updated = store.get_project(project.id)
            assert updated.tech_stack == {"backend": "flask", "db": "postgres"}

    def test_update_project_rejects_invalid_fields(self, app, project):
        from web.storage import store
        with app.test_request_context():
            result = store.update_project(project.id, invalid_field="bad")
            assert result is False

    def test_list_projects(self, app):
        from web.storage import store
        with app.test_request_context():
            store.create_project(name="App 1", user_id="dev@example.com")
            store.create_project(name="App 2", user_id="dev@example.com")
            store.create_project(name="App 3", user_id="other@example.com")

            all_projects = store.list_projects()
            assert len(all_projects) == 3

            user_projects = store.list_projects(user_id="dev@example.com")
            assert len(user_projects) == 2

    def test_project_to_dict(self, app, project):
        d = project.to_dict()
        assert d["id"] == project.id
        assert d["name"] == "Test App"
        assert d["slug"] == "test-app"
        assert "created_at" in d
        assert "updated_at" in d


class TestProjectConversationLink:
    """Test linking conversations to projects."""

    def test_create_conversation_with_project(self, app, project):
        from web.storage import store
        with app.test_request_context():
            conv = store.create_conversation(
                conv_type="project", project_id=project.id, user_id="dev@example.com"
            )
            assert conv.project_id == project.id
            assert conv.conv_type == "project"

    def test_get_conversation_includes_project_id(self, app, project):
        from web.storage import store
        with app.test_request_context():
            conv = store.create_conversation(
                conv_type="project", project_id=project.id, user_id="dev@example.com"
            )
            fetched = store.get_conversation(conv.id)
            assert fetched.project_id == project.id

    def test_list_project_conversations(self, app, project):
        from web.storage import store
        with app.test_request_context():
            store.create_conversation(conv_type="project", project_id=project.id, user_id="dev@example.com")
            store.create_conversation(conv_type="project", project_id=project.id, user_id="dev@example.com")
            store.create_conversation(conv_type="exploration", user_id="dev@example.com")

            convs = store.list_project_conversations(project.id)
            assert len(convs) == 2
            assert all(c.project_id == project.id for c in convs)

    def test_conversation_to_dict_includes_project_id(self, app, project):
        from web.storage import store
        with app.test_request_context():
            conv = store.create_conversation(
                conv_type="project", project_id=project.id, user_id="dev@example.com"
            )
            d = conv.to_dict()
            assert d["project_id"] == project.id


class TestExpertAPI:
    """Test expert mode API endpoints."""

    def test_create_project_api(self, client):
        from web import config
        original = config.EXPERT_MODE_ENABLED
        config.EXPERT_MODE_ENABLED = True
        try:
            resp = client.post(
                "/api/expert/projects",
                json={"name": "New App", "description": "Test"},
                headers={"X-Forwarded-Email": "dev@example.com"},
            )
            assert resp.status_code == 201
            data = resp.get_json()
            assert data["project"]["name"] == "New App"
            assert data["conversation_id"]
            assert "/expert/" in data["redirect"]
        finally:
            config.EXPERT_MODE_ENABLED = original

    def test_update_project_api(self, app, client, project):
        from web import config
        original = config.EXPERT_MODE_ENABLED
        config.EXPERT_MODE_ENABLED = True
        try:
            resp = client.patch(
                f"/api/expert/projects/{project.id}",
                json={"name": "Updated Name", "status": "active"},
                headers={"X-Forwarded-Email": "dev@example.com"},
            )
            assert resp.status_code == 200
            data = resp.get_json()
            assert data["name"] == "Updated Name"
            assert data["status"] == "active"
        finally:
            config.EXPERT_MODE_ENABLED = original

    def test_new_conversation_api(self, app, client, project):
        from web import config
        original = config.EXPERT_MODE_ENABLED
        config.EXPERT_MODE_ENABLED = True
        try:
            resp = client.post(
                f"/api/expert/projects/{project.id}/conversations",
                headers={"X-Forwarded-Email": "dev@example.com"},
            )
            assert resp.status_code == 201
            data = resp.get_json()
            assert data["conversation_id"]
            assert f"/expert/{project.slug}/" in data["redirect"]
        finally:
            config.EXPERT_MODE_ENABLED = original

    def test_api_disabled_when_expert_mode_off(self, client):
        from web import config
        original = config.EXPERT_MODE_ENABLED
        config.EXPERT_MODE_ENABLED = False
        try:
            resp = client.post("/api/expert/projects", json={"name": "X"})
            assert resp.status_code == 403
        finally:
            config.EXPERT_MODE_ENABLED = original

    def test_expert_home_page(self, client):
        from web import config
        original = config.EXPERT_MODE_ENABLED
        config.EXPERT_MODE_ENABLED = True
        try:
            resp = client.get("/expert")
            assert resp.status_code == 200
            assert b"Expert" in resp.data or b"expert" in resp.data
        finally:
            config.EXPERT_MODE_ENABLED = original

    def test_expert_home_404_when_disabled(self, client):
        from web import config
        original = config.EXPERT_MODE_ENABLED
        config.EXPERT_MODE_ENABLED = False
        try:
            resp = client.get("/expert")
            assert resp.status_code == 404
        finally:
            config.EXPERT_MODE_ENABLED = original

    def test_expert_nav_visible_on_non_landing_pages(self, app, client, project):
        from web import config
        from web.storage import store

        conv = store.create_conversation(
            conv_type="project",
            project_id=project.id,
            user_id="dev@example.com",
        )

        original = config.EXPERT_MODE_ENABLED
        config.EXPERT_MODE_ENABLED = True
        try:
            for path in (
                "/rechercher",
                f"/expert/{project.slug}",
                f"/expert/{project.slug}/{conv.id}",
            ):
                resp = client.get(path, headers={"X-Forwarded-Email": "dev@example.com"})
                assert resp.status_code == 200
                assert b'href="/expert"' in resp.data
        finally:
            config.EXPERT_MODE_ENABLED = original

    def test_expert_nav_hidden_on_landing_page(self, client):
        from web import config

        original = config.EXPERT_MODE_ENABLED
        config.EXPERT_MODE_ENABLED = True
        try:
            resp = client.get("/")
            assert resp.status_code == 200
            assert b'href="/expert"' not in resp.data
        finally:
            config.EXPERT_MODE_ENABLED = original

    def test_project_welcome_endpoint_is_idempotent(self, app, client, project):
        from web import config
        from web.storage import store

        conv = store.create_conversation(
            conv_type="project",
            project_id=project.id,
            user_id="dev@example.com",
        )

        original = config.EXPERT_MODE_ENABLED
        config.EXPERT_MODE_ENABLED = True
        try:
            first = client.post(
                f"/api/conversations/{conv.id}/welcome",
                headers={"X-Forwarded-Email": "dev@example.com"},
            )
            assert first.status_code == 202

            pending = [
                cmd
                for cmd in store.get_pending_pm_commands()
                if cmd["conversation_id"] == conv.id and cmd["command"] == "run"
            ]
            assert len(pending) == 1
            payload = pending[0]["payload"]
            assert payload["project_workdir"] == str(config.PROJECTS_DIR / project.id)
            assert "MODE EXPERT - plan mode" in payload["prompt"]

            # Simulate completion: assistant has responded and run is finished.
            store.add_message(conv.id, "assistant", "Bienvenue, on peut commencer le plan.")
            store.update_conversation(conv.id, needs_response=False)

            second = client.post(
                f"/api/conversations/{conv.id}/welcome",
                headers={"X-Forwarded-Email": "dev@example.com"},
            )
            assert second.status_code == 409
            assert second.get_json()["status"] == "already_initialized"

            pending_after = [
                cmd
                for cmd in store.get_pending_pm_commands()
                if cmd["conversation_id"] == conv.id and cmd["command"] == "run"
            ]
            assert len(pending_after) == 1
        finally:
            config.EXPERT_MODE_ENABLED = original

    def test_project_preview_route_proxies_staging(self, app, client, project, monkeypatch):
        from web import config
        from web.storage import store

        class FakeResponse:
            status_code = 200
            headers = {"Content-Type": "text/html; charset=utf-8"}
            content = b'<html><head></head><body><a href="/asset">ok</a></body></html>'
            encoding = "utf-8"

        original_enabled = config.EXPERT_MODE_ENABLED
        config.EXPERT_MODE_ENABLED = True
        try:
            store.update_project(project.id, staging_deploy_url="http://localhost:18080")
            monkeypatch.setattr("web.routes.expert.requests.request", lambda **kwargs: FakeResponse())

            resp = client.get(
                f"/expert/{project.slug}/preview/staging/",
                headers={"X-Forwarded-Email": "dev@example.com"},
            )
            assert resp.status_code == 200
            assert f'/expert/{project.slug}/preview/staging/asset'.encode() in resp.data
        finally:
            config.EXPERT_MODE_ENABLED = original_enabled

    def test_project_preview_rejects_absolute_target(self, app, client, project, monkeypatch):
        from web import config
        from web.storage import store

        calls = {"count": 0}

        def _unexpected_request(**kwargs):
            calls["count"] += 1
            raise AssertionError("requests.request should not be called for rejected targets")

        original_enabled = config.EXPERT_MODE_ENABLED
        config.EXPERT_MODE_ENABLED = True
        try:
            store.update_project(project.id, staging_deploy_url="http://localhost:18080")
            monkeypatch.setattr("web.routes.expert.requests.request", _unexpected_request)

            resp = client.get(
                f"/expert/{project.slug}/preview/staging/https:%2F%2Fevil.example%2F",
                headers={"X-Forwarded-Email": "dev@example.com"},
            )
            assert resp.status_code == 400
            assert calls["count"] == 0
        finally:
            config.EXPERT_MODE_ENABLED = original_enabled

    def test_project_preview_strips_sensitive_headers(self, app, client, project, monkeypatch):
        from web import config
        from web.storage import store

        captured = {}

        class FakeResponse:
            status_code = 200
            headers = {"Content-Type": "text/plain; charset=utf-8"}
            content = b"ok"
            encoding = "utf-8"

        def _fake_request(**kwargs):
            captured["headers"] = kwargs.get("headers", {})
            return FakeResponse()

        original_enabled = config.EXPERT_MODE_ENABLED
        config.EXPERT_MODE_ENABLED = True
        try:
            store.update_project(project.id, staging_deploy_url="http://localhost:18080")
            monkeypatch.setattr("web.routes.expert.requests.request", _fake_request)

            resp = client.get(
                f"/expert/{project.slug}/preview/staging/",
                headers={
                    "X-Forwarded-Email": "dev@example.com",
                    "Authorization": "Bearer secret-token",
                    "Cookie": "session=top-secret",
                    "X-Correlation-ID": "abc-123",
                },
            )
            assert resp.status_code == 200

            forwarded = {k.lower(): v for k, v in captured["headers"].items()}
            assert "authorization" not in forwarded
            assert "cookie" not in forwarded
            assert "x-forwarded-email" not in forwarded
            assert forwarded.get("x-correlation-id") == "abc-123"
        finally:
            config.EXPERT_MODE_ENABLED = original_enabled

    def test_fastapi_templates_receive_config(self, client):
        from web import config

        original = config.EXPERT_MODE_ENABLED
        config.EXPERT_MODE_ENABLED = True
        try:
            resp = client.get("/rechercher")
            assert resp.status_code == 200
            assert b'href="/expert"' in resp.data
        finally:
            config.EXPERT_MODE_ENABLED = original

    def test_expert_nav_visible_on_expert_pages(self, app, client, project):
        from web import config
        from web.storage import store

        conv = store.create_conversation(
            conv_type="project",
            project_id=project.id,
            user_id="dev@example.com",
        )

        original = config.EXPERT_MODE_ENABLED
        config.EXPERT_MODE_ENABLED = True
        try:
            for path in (
                "/expert",
                f"/expert/{project.slug}",
                f"/expert/{project.slug}/{conv.id}",
            ):
                resp = client.get(path, headers={"X-Forwarded-Email": "dev@example.com"})
                assert resp.status_code == 200
                assert b'href="/expert"' in resp.data
        finally:
            config.EXPERT_MODE_ENABLED = original

    def test_project_welcome_endpoint_is_idempotent(self, app, client, project):
        from web import config
        from web.storage import store

        conv = store.create_conversation(
            conv_type="project",
            project_id=project.id,
            user_id="dev@example.com",
        )

        original = config.EXPERT_MODE_ENABLED
        config.EXPERT_MODE_ENABLED = True
        try:
            first = client.post(
                f"/api/conversations/{conv.id}/welcome",
                headers={"X-Forwarded-Email": "dev@example.com"},
            )
            assert first.status_code == 202

            pending = [
                cmd
                for cmd in store.get_pending_pm_commands()
                if cmd["conversation_id"] == conv.id and cmd["command"] == "run"
            ]
            assert len(pending) == 1
            payload = pending[0]["payload"]
            assert payload["project_workdir"] == str(config.PROJECTS_DIR / project.id)
            assert "MODE EXPERT - plan mode" in payload["prompt"]

            # Simulate completion of the welcome response.
            store.add_message(conv.id, "assistant", "Bienvenue, on peut commencer le plan.")
            store.update_conversation(conv.id, needs_response=False)

            second = client.post(
                f"/api/conversations/{conv.id}/welcome",
                headers={"X-Forwarded-Email": "dev@example.com"},
            )
            assert second.status_code == 409
            assert second.get_json()["status"] == "already_initialized"

            pending_after = [
                cmd
                for cmd in store.get_pending_pm_commands()
                if cmd["conversation_id"] == conv.id and cmd["command"] == "run"
            ]
            assert len(pending_after) == 1
        finally:
            config.EXPERT_MODE_ENABLED = original

    def test_project_message_enqueues_project_workdir(self, app, client, project):
        from web import config
        from web.storage import store

        conv = store.create_conversation(
            conv_type="project",
            project_id=project.id,
            user_id="dev@example.com",
        )

        resp = client.post(
            f"/api/conversations/{conv.id}/messages",
            json={"content": "Ajoute une page d'accueil"},
            headers={"X-Forwarded-Email": "dev@example.com"},
        )
        assert resp.status_code == 200

        pending = store.get_pending_pm_commands()
        run_cmd = next(
            c for c in pending
            if c["conversation_id"] == conv.id and c["command"] == "run"
        )
        assert run_cmd["payload"]["project_workdir"] == str(config.PROJECTS_DIR / project.id)

    def test_deploy_project_api_promotes_and_deploys_production(self, app, client, project, monkeypatch):
        from web import config
        from web.storage import store

        created_apps = []

        class FakeCoolify:
            def list_servers(self):
                return [{"uuid": "srv-1"}]

            def create_project(self, name, description=""):
                return {"uuid": "coolify-proj-1"}

            def get_deploy_key_uuid(self, name_contains="gitea"):
                return "key-1"

            def create_application(self, **kwargs):
                assert kwargs["git_repo_url"] == "git@matometa-gitea:apps/test-app.git"
                created_apps.append(kwargs)
                return {
                    "uuid": f"{kwargs['name']}-uuid",
                    "domains": [f"{kwargs['name']}.example.test"],
                }

            def deploy(self, app_uuid):
                return {"ok": True, "app_uuid": app_uuid}

            def get_webhook_secret(self, app_uuid):
                return "secret"

            def set_webhook_secret(self, app_uuid, secret):
                return {"ok": True}

            def create_postgres_database(self, **kwargs):
                return {"uuid": f"{kwargs['name']}-db-uuid"}

            def get_database_status(self, db_uuid):
                return {"internal_db_url": "postgresql://app:pass@db:5432/app"}

            def get_database_connection_url(self, db_uuid):
                return "postgresql://app:pass@db:5432/app"

            def set_environment_variable(self, app_uuid, key, value, is_preview=False):
                return {"ok": True}

        original_enabled = config.EXPERT_MODE_ENABLED
        original_coolify = config.COOLIFY_API_TOKEN
        config.EXPERT_MODE_ENABLED = True
        config.COOLIFY_API_TOKEN = "test-token"

        try:
            store.update_project(project.id, gitea_url="http://localhost:3300/apps/test-app")

            monkeypatch.setattr("lib.coolify.CoolifyClient", FakeCoolify)
            monkeypatch.setattr("web.routes.expert._setup_gitea_webhook", lambda *args, **kwargs: None)
            monkeypatch.setattr("web.routes.expert._use_local_direct_port_mode", lambda: False)
            monkeypatch.setattr("web.routes.expert._ensure_local_git_repo", lambda project: True)
            monkeypatch.setattr("web.routes.expert.ensure_project_branches", lambda project: None)
            monkeypatch.setattr("web.routes.expert._ensure_deployable_repo", lambda project: False)
            monkeypatch.setattr("web.routes.expert.commit_and_push_staging_if_changed", lambda *args, **kwargs: None)
            monkeypatch.setattr(
                "web.routes.expert.promote_staging_to_production",
                lambda *args, **kwargs: {
                    "production_branch": "prod",
                    "source_branch": "stagging",
                    "commit": "abc1234",
                },
            )

            resp = client.post(
                f"/api/expert/projects/{project.id}/deploy",
                headers={"X-Forwarded-Email": "dev@example.com"},
            )
            assert resp.status_code == 200

            data = resp.get_json()
            assert data["status"] == "production_deploying"
            assert data["promotion"]["commit"] == "abc1234"
            # App names now use project_key instead of slug
            pkey = data["project"]["project_key"]
            assert data["project"]["staging_coolify_app_uuid"] == f"{pkey}-staging-uuid"
            assert data["project"]["production_coolify_app_uuid"] == f"{pkey}-prod-uuid"
            assert data["project"]["production_deploy_url"] == f"http://{pkey}-prod.example.test"
            assert data["project"]["coolify_app_uuid"] == f"{pkey}-prod-uuid"
            assert data["project"]["deploy_url"] == f"http://{pkey}-prod.example.test"
            assert data["project"]["status"] == "deployed"
            assert len(created_apps) == 2
            assert {entry["git_branch"] for entry in created_apps} == {"stagging", "prod"}
        finally:
            config.EXPERT_MODE_ENABLED = original_enabled
            config.COOLIFY_API_TOKEN = original_coolify

    def test_deploy_status_returns_preview_urls(self, app, client, project, monkeypatch):
        from web import config
        from web.storage import store

        class FakeCoolify:
            def get_status(self, app_uuid):
                return {"status": "running:unknown"}

        original_enabled = config.EXPERT_MODE_ENABLED
        original_coolify = config.COOLIFY_API_TOKEN
        config.EXPERT_MODE_ENABLED = True
        config.COOLIFY_API_TOKEN = "test-token"
        try:
            store.update_project(
                project.id,
                slug="demo-proj",
                staging_coolify_app_uuid="stg-1",
                staging_deploy_url="http://localhost:18084",
                production_coolify_app_uuid="prd-1",
                production_deploy_url="http://localhost:28084",
            )
            monkeypatch.setattr("lib.coolify.CoolifyClient", FakeCoolify)

            resp = client.get(
                f"/api/expert/projects/{project.id}/deploy-status",
                headers={"X-Forwarded-Email": "dev@example.com"},
            )
            assert resp.status_code == 200
            data = resp.get_json()
            assert data["staging"]["deploy_url"] == "/expert/demo-proj/preview/staging/"
            assert data["production"]["deploy_url"] == "/expert/demo-proj/preview/production/"
            assert data["staging"]["technical_deploy_url"] == "http://localhost:18084"
            assert data["production"]["technical_deploy_url"] == "http://localhost:28084"
        finally:
            config.EXPERT_MODE_ENABLED = original_enabled
            config.COOLIFY_API_TOKEN = original_coolify


class TestExpertHelpers:
    def test_extract_owner_repo_from_url(self):
        from web.routes.expert import _extract_owner_repo_from_url

        assert _extract_owner_repo_from_url("http://localhost:3300/apps/my-app") == ("apps", "my-app")
        assert _extract_owner_repo_from_url("https://gitea.example.com/a/b.git") == ("a", "b")

    def test_normalize_deploy_url(self):
        from web.routes.expert import _normalize_deploy_url

        assert _normalize_deploy_url(["demo.example.test"]) == "http://demo.example.test"
        assert _normalize_deploy_url("https://demo.example.test") == "https://demo.example.test"
        assert _normalize_deploy_url([]) is None

    def test_publicize_deploy_url_with_request_host(self, app, monkeypatch):
        from web import config
        from web.routes.expert import _publicize_deploy_url

        monkeypatch.setattr(config, "EXPERT_DEPLOY_PUBLIC_HOST", "")
        with app.test_request_context(base_url="http://matometa.local:5002"):
            public = _publicize_deploy_url("http://localhost:18084")
        assert public == "http://matometa.local:18084"

    def test_project_to_public_dict_includes_preview_urls(self, app):
        from web.database import Project
        from web.routes.expert import _project_to_public_dict

        project = Project(id="p1", name="Demo", slug="demo", staging_deploy_url="http://localhost:18084")
        with app.test_request_context(base_url="http://127.0.0.1:5002"):
            payload = _project_to_public_dict(project)
        assert payload["staging_preview_url"] == "/expert/demo/preview/staging/"
        assert payload["production_preview_url"] == "/expert/demo/preview/production/"

    def test_extract_host_port_mapping(self):
        from web.routes.expert import _extract_host_port_mapping

        assert _extract_host_port_mapping("18080:5000") == 18080
        assert _extract_host_port_mapping("18081:5000,18082:5001") == 18081
        assert _extract_host_port_mapping(None) is None
        assert _extract_host_port_mapping("invalid") is None

    def test_reserved_local_deploy_ports(self, monkeypatch):
        from web.routes.expert import _reserved_local_deploy_ports

        class P:
            def __init__(self, pid, deploy_url):
                self.id = pid
                self.deploy_url = deploy_url
                self.staging_deploy_url = None
                self.production_deploy_url = None

        projects = [
            P("a", "http://localhost:18080"),
            P("b", "http://localhost:18081"),
            P("c", "http://example.test"),
        ]
        monkeypatch.setattr("web.routes.expert.store.list_projects", lambda limit=2000: projects)

        ports = _reserved_local_deploy_ports(exclude_project_id="a")
        assert ports == {18081}

    def test_ensure_deployable_repo_bootstraps_files(self, monkeypatch, tmp_path):
        from web import config
        from web.routes.expert import _ensure_deployable_repo

        project_id = "proj-1"
        workdir = tmp_path / project_id
        (workdir / ".git").mkdir(parents=True)

        class P:
            id = project_id
            name = "Demo"
            slug = "demo"

        calls = []

        def fake_run_git(cwd, *args, **kwargs):
            calls.append(args)
            if args[:3] == ("diff", "--cached", "--name-only"):
                return "Dockerfile\nindex.html"
            return ""

        monkeypatch.setattr(config, "PROJECTS_DIR", tmp_path)
        monkeypatch.setattr("web.routes.expert._run_git", fake_run_git)

        changed = _ensure_deployable_repo(P())
        assert changed is True
        assert (workdir / "Dockerfile").exists()
        assert (workdir / "index.html").exists()
        assert any(c[:2] == ("commit", "-m") for c in calls)
        assert any(c[:3] == ("push", "origin", "main") for c in calls)

    def test_ensure_deployable_repo_noop_when_dockerfile_exists(self, monkeypatch, tmp_path):
        from web import config
        from web.routes.expert import _ensure_deployable_repo

        project_id = "proj-2"
        workdir = tmp_path / project_id
        (workdir / ".git").mkdir(parents=True)
        (workdir / "Dockerfile").write_text("FROM scratch\n")

        class P:
            id = project_id
            name = "Demo"
            slug = "demo"

        monkeypatch.setattr(config, "PROJECTS_DIR", tmp_path)
        changed = _ensure_deployable_repo(P())
        assert changed is False


class TestMigrationV21:
    """Test v21 migration: project_key, plan lifecycle, stack_profile."""

    def test_migration_v21_adds_new_columns(self, app):
        from web.database import get_db, _get_table_columns
        with app.test_request_context():
            with get_db() as conn:
                columns = _get_table_columns(conn, "projects")
            expected = {
                "project_key", "workflow_phase", "plan_draft", "plan_approved",
                "plan_version", "plan_approved_at", "plan_approved_by",
                "plan_source_conversation_id", "stack_profile",
                "staging_postgres_uuid", "production_postgres_uuid",
            }
            for col in expected:
                assert col in columns, f"Column {col} missing from projects table"

    def test_new_project_gets_project_key(self, app, project):
        """Every new project should have a unique project_key."""
        assert project.project_key is not None
        assert "-" in project.project_key  # adjective-noun format

    def test_project_key_unique_across_projects(self, app):
        from web.storage import store
        with app.test_request_context():
            p1 = store.create_project(name="App A", user_id="a@b.com")
            p2 = store.create_project(name="App B", user_id="a@b.com")
            assert p1.project_key != p2.project_key

    def test_migration_v21_backfills_plan_from_spec(self, app, project):
        """Projects with spec should have plan_approved backfilled by migration."""
        from web.database import get_db, _migrate_to_v21
        from web.storage import store
        with app.test_request_context():
            # Set spec and clear plan fields to simulate pre-v21 state
            store.update_project(project.id, spec="# Test Spec\n\nA Flask app.", plan_approved=None, workflow_phase="")

            # Re-run migration
            with get_db() as conn:
                _migrate_to_v21(conn)

            updated = store.get_project(project.id)
            assert updated.plan_approved == "# Test Spec\n\nA Flask app."
            assert updated.plan_version == 1
            assert updated.workflow_phase == "implementing"

    def test_migration_v21_idempotent(self, app):
        """Running migration v21 twice doesn't break anything."""
        from web.database import get_db, _migrate_to_v21
        with app.test_request_context():
            with get_db() as conn:
                _migrate_to_v21(conn)
                _migrate_to_v21(conn)  # second run should be safe

    def test_new_project_default_stack_profile(self, app, project):
        assert project.stack_profile == "web_postgres"

    def test_create_project_custom_stack_profile(self, app):
        from web.storage import store
        with app.test_request_context():
            p = store.create_project(name="Simple", user_id="a@b.com", stack_profile="web_only")
            assert p.stack_profile == "web_only"


class TestPlanLifecycleAPI:
    """Test plan lifecycle endpoints."""

    def test_save_plan_draft(self, app, client, project):
        from web import config
        original = config.EXPERT_MODE_ENABLED
        config.EXPERT_MODE_ENABLED = True
        try:
            resp = client.put(
                f"/api/expert/projects/{project.id}/plan-draft",
                json={"content": "# My Plan\n\nA web app."},
                headers={"X-Forwarded-Email": "dev@example.com"},
            )
            assert resp.status_code == 200
            data = resp.get_json()
            assert data["plan_draft"] == "# My Plan\n\nA web app."
            assert data["workflow_phase"] == "awaiting_approval"
        finally:
            config.EXPERT_MODE_ENABLED = original

    def test_approve_plan(self, app, client, project):
        from web import config
        from web.storage import store
        original = config.EXPERT_MODE_ENABLED
        config.EXPERT_MODE_ENABLED = True
        try:
            # Set up plan draft first
            with app.test_request_context():
                store.update_project(project.id, plan_draft="# Plan", workflow_phase="awaiting_approval")

            resp = client.post(
                f"/api/expert/projects/{project.id}/plan-approve",
                json={},
                headers={"X-Forwarded-Email": "dev@example.com"},
            )
            assert resp.status_code == 200
            data = resp.get_json()
            assert data["plan_approved"] == "# Plan"
            assert data["plan_version"] == 1
            assert data["workflow_phase"] == "implementing"
            assert data["plan_approved_by"] == "dev@example.com"
            assert data["spec"] == "# Plan"  # backwards compat
        finally:
            config.EXPERT_MODE_ENABLED = original

    def test_return_to_planning(self, app, client, project):
        from web import config
        from web.storage import store
        original = config.EXPERT_MODE_ENABLED
        config.EXPERT_MODE_ENABLED = True
        try:
            with app.test_request_context():
                store.update_project(project.id, workflow_phase="implementing", plan_approved="# Plan")

            resp = client.post(
                f"/api/expert/projects/{project.id}/return-to-planning",
                json={},
                headers={"X-Forwarded-Email": "dev@example.com"},
            )
            assert resp.status_code == 200
            data = resp.get_json()
            assert data["workflow_phase"] == "planning"
            assert data["plan_draft"] is None
        finally:
            config.EXPERT_MODE_ENABLED = original

    def test_invalid_transition_returns_409(self, app, client, project):
        """Cannot approve plan from 'planning' (no draft saved)."""
        from web import config
        original = config.EXPERT_MODE_ENABLED
        config.EXPERT_MODE_ENABLED = True
        try:
            resp = client.post(
                f"/api/expert/projects/{project.id}/plan-approve",
                json={},
                headers={"X-Forwarded-Email": "dev@example.com"},
            )
            assert resp.status_code == 409
        finally:
            config.EXPERT_MODE_ENABLED = original

    def test_return_to_planning_from_planning_returns_409(self, app, client, project):
        """Cannot return to planning when already in planning."""
        from web import config
        original = config.EXPERT_MODE_ENABLED
        config.EXPERT_MODE_ENABLED = True
        try:
            resp = client.post(
                f"/api/expert/projects/{project.id}/return-to-planning",
                json={},
                headers={"X-Forwarded-Email": "dev@example.com"},
            )
            assert resp.status_code == 409
        finally:
            config.EXPERT_MODE_ENABLED = original

    def test_project_key_immutable_via_patch(self, app, client, project):
        """PATCH with project_key should be rejected."""
        from web import config
        original = config.EXPERT_MODE_ENABLED
        config.EXPERT_MODE_ENABLED = True
        try:
            resp = client.patch(
                f"/api/expert/projects/{project.id}",
                json={"project_key": "hacked-key"},
                headers={"X-Forwarded-Email": "dev@example.com"},
            )
            assert resp.status_code == 400
            assert "immutable" in resp.get_json()["error"]
        finally:
            config.EXPERT_MODE_ENABLED = original

    def test_rename_project_keeps_key(self, app, client, project):
        """Renaming a project doesn't change its project_key."""
        from web import config
        from web.storage import store
        original = config.EXPERT_MODE_ENABLED
        config.EXPERT_MODE_ENABLED = True
        try:
            original_key = project.project_key
            resp = client.patch(
                f"/api/expert/projects/{project.id}",
                json={"name": "Renamed App"},
                headers={"X-Forwarded-Email": "dev@example.com"},
            )
            assert resp.status_code == 200
            data = resp.get_json()
            assert data["name"] == "Renamed App"
            assert data["project_key"] == original_key
        finally:
            config.EXPERT_MODE_ENABLED = original

    def test_stack_profile_via_patch(self, app, client, project):
        """stack_profile can be updated via PATCH."""
        from web import config
        original = config.EXPERT_MODE_ENABLED
        config.EXPERT_MODE_ENABLED = True
        try:
            resp = client.patch(
                f"/api/expert/projects/{project.id}",
                json={"stack_profile": "web_only"},
                headers={"X-Forwarded-Email": "dev@example.com"},
            )
            assert resp.status_code == 200
            assert resp.get_json()["stack_profile"] == "web_only"
        finally:
            config.EXPERT_MODE_ENABLED = original

    def test_full_plan_lifecycle(self, app, client, project):
        """Test the full planning → awaiting_approval → implementing → planning cycle."""
        from web import config
        original = config.EXPERT_MODE_ENABLED
        config.EXPERT_MODE_ENABLED = True
        try:
            # 1. Save draft → transitions to awaiting_approval
            resp = client.put(
                f"/api/expert/projects/{project.id}/plan-draft",
                json={"content": "# V1 Plan"},
                headers={"X-Forwarded-Email": "dev@example.com"},
            )
            assert resp.status_code == 200
            assert resp.get_json()["workflow_phase"] == "awaiting_approval"

            # 2. Approve → transitions to implementing
            resp = client.post(
                f"/api/expert/projects/{project.id}/plan-approve",
                json={},
                headers={"X-Forwarded-Email": "dev@example.com"},
            )
            assert resp.status_code == 200
            data = resp.get_json()
            assert data["workflow_phase"] == "implementing"
            assert data["plan_version"] == 1

            # 3. Return to planning
            resp = client.post(
                f"/api/expert/projects/{project.id}/return-to-planning",
                json={},
                headers={"X-Forwarded-Email": "dev@example.com"},
            )
            assert resp.status_code == 200
            assert resp.get_json()["workflow_phase"] == "planning"

            # 4. Save new draft and approve again → version bumps
            resp = client.put(
                f"/api/expert/projects/{project.id}/plan-draft",
                json={"content": "# V2 Plan"},
                headers={"X-Forwarded-Email": "dev@example.com"},
            )
            assert resp.status_code == 200

            resp = client.post(
                f"/api/expert/projects/{project.id}/plan-approve",
                json={},
                headers={"X-Forwarded-Email": "dev@example.com"},
            )
            assert resp.status_code == 200
            data = resp.get_json()
            assert data["plan_version"] == 2
            assert data["plan_approved"] == "# V2 Plan"
        finally:
            config.EXPERT_MODE_ENABLED = original


class TestGitAttribution:
    """Test git attribution to connected user."""

    def test_run_git_as_user_sets_env_vars(self, tmp_path):
        """Verify run_git_as_user passes env vars for author identity."""
        from lib.expert_git import run_git_as_user
        import subprocess

        # Create a minimal git repo
        subprocess.run(["git", "init", str(tmp_path)], check=True, capture_output=True)
        subprocess.run(["git", "config", "user.email", "fallback@test.com"], cwd=tmp_path, check=True, capture_output=True)
        subprocess.run(["git", "config", "user.name", "Fallback"], cwd=tmp_path, check=True, capture_output=True)

        (tmp_path / "test.txt").write_text("hello")
        subprocess.run(["git", "add", "test.txt"], cwd=tmp_path, check=True, capture_output=True)

        # Commit with custom identity
        run_git_as_user(
            tmp_path, "commit", "-m", "test commit",
            author_name="Alice Dupont",
            author_email="alice@example.com",
        )

        # Verify the commit author
        log = subprocess.run(
            ["git", "log", "-1", "--format=%an <%ae>"],
            cwd=tmp_path, capture_output=True, text=True, check=True,
        ).stdout.strip()
        assert log == "Alice Dupont <alice@example.com>"

    def test_commit_and_push_uses_identity_when_provided(self, tmp_path, monkeypatch):
        """Verify commit_and_push_staging_if_changed uses author params."""
        from web import config

        calls = []

        def mock_run_git(workdir, *args, timeout=40):
            calls.append(("run_git", args))
            if args == ("rev-parse", "--abbrev-ref", "HEAD"):
                return "stagging"
            if args == ("diff", "--cached", "--name-only"):
                return "file.txt"
            if args == ("rev-parse", "--short", "HEAD"):
                return "abc1234"
            return ""

        def mock_run_git_as_user(workdir, *args, author_name=None, author_email=None, timeout=40):
            calls.append(("run_git_as_user", args, author_name, author_email))
            return ""

        monkeypatch.setattr("lib.expert_git.run_git", mock_run_git)
        monkeypatch.setattr("lib.expert_git.run_git_as_user", mock_run_git_as_user)
        monkeypatch.setattr(config, "PROJECTS_DIR", tmp_path)

        project_id = "test-proj"
        workdir = tmp_path / project_id
        (workdir / ".git").mkdir(parents=True)

        class FakeProject:
            id = project_id
            staging_branch = "stagging"

        from lib.expert_git import commit_and_push_staging_if_changed
        result = commit_and_push_staging_if_changed(
            FakeProject(), "conv-123",
            author_name="Bob Martin", author_email="bob@example.com",
        )

        assert result is not None
        # Verify run_git_as_user was called with the commit
        user_calls = [c for c in calls if c[0] == "run_git_as_user"]
        assert len(user_calls) == 1
        assert user_calls[0][2] == "Bob Martin"
        assert user_calls[0][3] == "bob@example.com"
