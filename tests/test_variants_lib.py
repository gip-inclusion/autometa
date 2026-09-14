"""Tests for lib/variants — déclinaisons d'un tableau de bord (clé, libellé, jeton)."""

import re
import shutil
from datetime import datetime, timezone

import pytest
from sqlalchemy import select
from sqlalchemy.orm import Session

from lib.dashboards import DashboardNotFound, update_dashboard
from lib.variants import add_variant, exposed_tokens, folder_files, list_variants, remove_variant
from web.db import get_db
from web.db import test_transaction as _test_tx
from web.models import Dashboard, DashboardPublication, DashboardVariant

UUID_RE = re.compile(r"^[0-9a-f]{8}-[0-9a-f]{4}-4[0-9a-f]{3}-[89ab][0-9a-f]{3}-[0-9a-f]{12}$")


@pytest.fixture
def isolated(tmp_path, monkeypatch):
    import web.config as cfg

    interactive_dir = tmp_path / "interactive"
    interactive_dir.mkdir()
    monkeypatch.setattr(cfg, "INTERACTIVE_DIR", interactive_dir)
    with _test_tx():
        yield interactive_dir
    shutil.rmtree(interactive_dir, ignore_errors=True)


def _make_dashboard(slug):
    now = datetime.now(timezone.utc)
    with get_db() as session:
        session.add(
            Dashboard(
                slug=slug,
                title=slug,
                description="d",
                website="dora",
                category="c",
                first_author_email="alice@x",
                is_archived=False,
                has_api_access=False,
                has_cron=True,
                has_persistence=False,
                created_at=now,
                updated_at=now,
            )
        )


@pytest.mark.integration
@pytest.mark.usefixtures("_db", "isolated")
class TestDeclaration:
    def test_dod_4_token_is_generated_and_stable(self):
        _make_dashboard("multi")
        variant = add_variant("multi", "67", "Bas-Rhin")
        assert UUID_RE.match(variant["token"])
        assert variant["path"] == f"data/{variant['token']}.json"
        assert list_variants("multi")[0]["token"] == variant["token"]

    def test_dod_4_unknown_dashboard_is_refused(self):
        with pytest.raises(DashboardNotFound):
            add_variant("nope", "67", "Bas-Rhin")

    def test_dod_7_duplicate_key_is_refused_without_creating_a_double(self):
        _make_dashboard("multi")
        first = add_variant("multi", "67", "Bas-Rhin")
        with pytest.raises(ValueError, match="67"):
            add_variant("multi", "67", "Bas-Rhin bis")
        variants = list_variants("multi")
        assert [v["token"] for v in variants] == [first["token"]]

    def test_dod_7_remove_deletes_row_and_internal_data_file(self, isolated, mocker):
        _make_dashboard("multi")
        token = add_variant("multi", "67", "Bas-Rhin")["token"]
        data_dir = isolated / "multi" / "data"
        data_dir.mkdir(parents=True)
        (data_dir / f"{token}.json").write_text("{}")
        s3_delete = mocker.patch("web.s3.interactive.delete")

        assert remove_variant("multi", "67") is True

        assert list_variants("multi") == []
        assert not (data_dir / f"{token}.json").exists()
        s3_delete.assert_called_once_with(f"multi/data/{token}.json")
        assert remove_variant("multi", "67") is False

    def test_dod_7_remove_also_drops_the_copy_in_every_active_publication_snapshot(self, mocker):
        _make_dashboard("multi")
        token = add_variant("multi", "67", "Bas-Rhin")["token"]
        now = datetime.now(timezone.utc)
        with get_db() as session:
            for pid, unpublished in (("live01", None), ("old001", now)):
                session.add(
                    DashboardPublication(
                        dashboard_slug="multi",
                        publication_id=pid,
                        environment="staging",
                        published_by="bob@x",
                        published_at=now,
                        unpublished_at=unpublished,
                    )
                )
        mocker.patch("web.s3.interactive.delete", return_value=True)
        snapshot_delete = mocker.patch("web.s3.publications.delete", return_value=True)

        assert remove_variant("multi", "67") is True

        snapshot_delete.assert_called_once_with(f"multi/live01/data/{token}.json")

    def test_dod_7_remove_keeps_the_declaration_when_the_file_cannot_be_deleted(self, mocker):
        _make_dashboard("multi")
        add_variant("multi", "67", "Bas-Rhin")
        mocker.patch("web.s3.interactive.delete", return_value=False)

        with pytest.raises(ValueError, match="S3"):
            remove_variant("multi", "67")

        assert [v["key"] for v in list_variants("multi")] == ["67"]

    def test_dod_7_a_concurrent_declaration_gets_the_same_refusal(self, mocker):
        _make_dashboard("multi")
        add_variant("multi", "67", "Bas-Rhin")
        # Why: simule la fenêtre de course — le SELECT ne voit rien, la contrainte d'unicité tranche.
        real_scalar = Session.scalar
        mocker.patch.object(
            Session,
            "scalar",
            side_effect=lambda self, stmt, *a, **k: (
                None if "dashboard_variants" in str(stmt) else real_scalar(self, stmt, *a, **k)
            ),
            autospec=True,
        )

        with pytest.raises(ValueError, match="déjà déclarée : 67"):
            add_variant("multi", "67", "Bas-Rhin bis")

    @pytest.mark.parametrize(
        ("key", "label", "field"),
        [
            ("", "Bas-Rhin", "clé"),
            ("bas rhin", "Bas-Rhin", "clé"),
            ("bas_rhin", "Bas-Rhin", "clé"),
            ("Bas-Rhin", "Bas-Rhin", "clé"),
            ("a" * 65, "Bas-Rhin", "clé"),
            ("67", "", "libellé"),
            ("67", "   ", "libellé"),
        ],
        ids=["empty-key", "space", "underscore", "uppercase", "too-long", "empty-label", "blank-label"],
    )
    def test_dod_12_invalid_key_or_label_is_refused_naming_the_field(self, key, label, field):
        _make_dashboard("multi")
        with pytest.raises(ValueError, match=field):
            add_variant("multi", key, label)
        assert list_variants("multi") == []

    def test_dod_12_two_variants_may_share_a_label(self):
        _make_dashboard("multi")
        add_variant("multi", "saint-denis-93", "Saint-Denis")
        add_variant("multi", "saint-denis-974", "Saint-Denis")
        assert [v["key"] for v in list_variants("multi")] == ["saint-denis-93", "saint-denis-974"]

    def test_dod_17_archiving_keeps_variants_and_tokens(self):
        _make_dashboard("multi")
        token = add_variant("multi", "67", "Bas-Rhin")["token"]
        update_dashboard(slug="multi", updater_email="bob@x", is_archived=True)
        update_dashboard(slug="multi", updater_email="bob@x", is_archived=False)
        assert [v["token"] for v in list_variants("multi")] == [token]

    def test_dod_17_deleting_the_dashboard_cascades(self):
        _make_dashboard("multi")
        add_variant("multi", "67", "Bas-Rhin")
        with get_db() as session:
            session.delete(session.scalar(select(Dashboard).where(Dashboard.slug == "multi")))
            session.flush()
            assert session.scalars(select(DashboardVariant)).all() == []


def test_dod_20_exposed_tokens_reports_content_not_file_names(tmp_path):
    token = "00000000-0000-4000-8000-000000000067"
    (tmp_path / "data").mkdir()
    (tmp_path / "data" / f"{token}.json").write_text('{"metadata": {"key": "67"}}')
    (tmp_path / "app.js").write_text(f"const MAP = {{'67': '{token}'}};")
    (tmp_path / "index.html").write_text("<html></html>")

    assert exposed_tokens(folder_files(tmp_path), [{"key": "67", "token": token}]) == ["app.js expose le jeton de 67"]


def test_dod_20_exposed_tokens_is_empty_when_only_file_names_carry_tokens(tmp_path):
    token = "00000000-0000-4000-8000-000000000067"
    (tmp_path / "data").mkdir()
    (tmp_path / "data" / f"{token}.json").write_bytes(b'{"metadata": {"key": "67"}}')

    assert exposed_tokens(folder_files(tmp_path), [{"key": "67", "token": token}]) == []
