"""Tests for Project CRUD, conversation-project linking, and expert API routes."""

import pytest

from web.database import store


class TestProjectCRUD:
    def test_create_project(self, client):
        project = store.create_project(name="Mon App", user_id="user@test.com", description="A desc")
        assert project.id
        assert project.name == "Mon App"
        assert project.user_id == "user@test.com"
        assert project.slug
        assert project.description == "A desc"
        assert project.status == "draft"
        assert project.workflow_phase == "planning"
        assert project.created_at
        assert project.updated_at

    def test_create_project_slug_uniqueness(self, client):
        p1 = store.create_project(name="App A", user_id="u@test.com")
        p2 = store.create_project(name="App B", user_id="u@test.com")
        assert p1.slug != p2.slug

    def test_get_project(self, client):
        created = store.create_project(name="Fetch Me", user_id="u@test.com")
        fetched = store.get_project(created.id)
        assert fetched is not None
        assert fetched.id == created.id
        assert fetched.name == "Fetch Me"

    def test_get_project_by_slug(self, client):
        created = store.create_project(name="Slug Test", user_id="u@test.com")
        fetched = store.get_project_by_slug(created.slug)
        assert fetched is not None
        assert fetched.id == created.id

    def test_get_project_not_found(self, client):
        assert store.get_project("nonexistent-id") is None

    def test_list_projects(self, client):
        store.create_project(name="P1", user_id="u@test.com")
        store.create_project(name="P2", user_id="u@test.com")
        store.create_project(name="P3", user_id="other@test.com")

        all_projects = store.list_projects()
        assert len(all_projects) == 3

        user_projects = store.list_projects(user_id="u@test.com")
        assert len(user_projects) == 2

    def test_update_project(self, client):
        project = store.create_project(name="Old Name", user_id="u@test.com")
        result = store.update_project(project.id, name="New Name", status="active")
        assert result is True

        updated = store.get_project(project.id)
        assert updated.name == "New Name"
        assert updated.status == "active"

    def test_update_project_no_valid_fields(self, client):
        project = store.create_project(name="X", user_id="u@test.com")
        result = store.update_project(project.id, invalid_field="nope")
        assert result is False

    def test_update_project_not_found(self, client):
        result = store.update_project("nonexistent", name="X")
        assert result is False


class TestConversationWithProject:
    def test_create_conversation_with_project(self, client):
        project = store.create_project(name="Linked", user_id="u@test.com")
        conv = store.create_conversation(user_id="u@test.com", conv_type="expert", project_id=project.id)
        assert conv.project_id == project.id

    def test_get_conversation_includes_project_id(self, client):
        project = store.create_project(name="Get Conv", user_id="u@test.com")
        conv = store.create_conversation(user_id="u@test.com", project_id=project.id)
        fetched = store.get_conversation(conv.id, include_messages=False)
        assert fetched.project_id == project.id

    def test_list_project_conversations(self, client):
        project = store.create_project(name="List Conv", user_id="u@test.com")
        store.create_conversation(user_id="u@test.com", project_id=project.id)
        store.create_conversation(user_id="u@test.com", project_id=project.id)
        store.create_conversation(user_id="u@test.com")

        convs = store.list_project_conversations(project.id)
        assert len(convs) == 2
        assert all(c.project_id == project.id for c in convs)


class TestExpertAPI:
    def test_expert_home_returns_404_when_disabled(self, client, mocker):
        mocker.patch("web.routes.expert.config.EXPERT_MODE_ENABLED", False)
        response = client.get("/expert")
        assert response.status_code == 404

    def test_expert_home_returns_200_when_enabled(self, client, mocker):
        mocker.patch("web.routes.expert.config.EXPERT_MODE_ENABLED", True)
        response = client.get("/expert")
        assert response.status_code == 200

    def test_create_project_api(self, client, mocker):
        mocker.patch("web.routes.expert.config.EXPERT_MODE_ENABLED", True)
        response = client.post("/api/expert/projects", json={"name": "API Project", "description": "From API"})
        assert response.status_code == 201
        data = response.json()
        assert data["project"]["name"] == "API Project"
        assert data["conversation_id"]
        assert data["redirect"]

    def test_update_project_api(self, client, mocker):
        mocker.patch("web.routes.expert.config.EXPERT_MODE_ENABLED", True)
        project = store.create_project(name="To Update", user_id="anonymous")
        response = client.patch(
            f"/api/expert/projects/{project.id}",
            json={"name": "Updated Via API", "status": "active"},
        )
        assert response.status_code == 200
        data = response.json()
        assert data["project"]["name"] == "Updated Via API"
        assert data["project"]["status"] == "active"

    def test_update_project_api_not_found(self, client, mocker):
        mocker.patch("web.routes.expert.config.EXPERT_MODE_ENABLED", True)
        response = client.patch("/api/expert/projects/nonexistent", json={"name": "X"})
        assert response.status_code == 404

    def test_update_project_api_no_valid_fields(self, client, mocker):
        mocker.patch("web.routes.expert.config.EXPERT_MODE_ENABLED", True)
        project = store.create_project(name="No Fields", user_id="anonymous")
        response = client.patch(f"/api/expert/projects/{project.id}", json={"bad_field": "X"})
        assert response.status_code == 400
