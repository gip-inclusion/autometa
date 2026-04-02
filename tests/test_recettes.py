"""Tests for Recette CRUD."""

from web.database import store


class TestRecetteCRUD:
    def test_create_recette(self, client):
        recette = store.create_recette(user_id="u@test.com", name="Les Emplois", github_repo="gip-inclusion/les-emplois")
        assert recette.id
        assert recette.user_id == "u@test.com"
        assert recette.name == "Les Emplois"
        assert recette.slug == "les-emplois"
        assert recette.github_repo == "gip-inclusion/les-emplois"
        assert recette.status == "cloned"
        assert recette.created_at
        assert recette.updated_at

    def test_create_recette_duplicate_slug(self, client):
        r1 = store.create_recette(user_id="u@test.com", name="R1", github_repo="org/my-app")
        r2 = store.create_recette(user_id="u@test.com", name="R2", github_repo="org/my-app")
        assert r1.slug != r2.slug

    def test_get_recette(self, client):
        created = store.create_recette(user_id="u@test.com", name="Get Me", github_repo="org/get-me")
        fetched = store.get_recette(created.id)
        assert fetched is not None
        assert fetched.id == created.id
        assert fetched.name == "Get Me"

    def test_get_recette_not_found(self, client):
        assert store.get_recette("nonexistent") is None

    def test_list_recettes(self, client):
        store.create_recette(user_id="u@test.com", name="R1", github_repo="org/repo-a")
        store.create_recette(user_id="u@test.com", name="R2", github_repo="org/repo-b")
        store.create_recette(user_id="other@test.com", name="R3", github_repo="org/repo-c")

        all_recettes = store.list_recettes()
        assert len(all_recettes) == 3

        user_recettes = store.list_recettes(user_id="u@test.com")
        assert len(user_recettes) == 2

    def test_update_recette(self, client):
        recette = store.create_recette(user_id="u@test.com", name="Before", github_repo="org/upd")
        result = store.update_recette(recette.id, status="deployed", branch_b="feat/test")
        assert result is True

        updated = store.get_recette(recette.id)
        assert updated.status == "deployed"
        assert updated.branch_b == "feat/test"

    def test_update_recette_no_valid_fields(self, client):
        recette = store.create_recette(user_id="u@test.com", name="X", github_repo="org/x")
        result = store.update_recette(recette.id, invalid_field="nope")
        assert result is False

    def test_update_recette_not_found(self, client):
        result = store.update_recette("nonexistent", status="deployed")
        assert result is False
