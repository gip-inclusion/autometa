"""Tags des pipelines de jobs : pose, retrait, création, filtre, tri, droits et rendu de /jobs."""

import importlib.util
from pathlib import Path

import httpx
import pytest
from alembic.migration import MigrationContext
from alembic.operations import Operations
from sqlalchemy import select

from lib.tag_sync import assigned_tag_ids
from web.db import get_db, get_engine
from web.models import JobTag, Tag
from web.routes.jobs import query_string, sort_pipelines
from web.stores.records import Tag as TagRecord

ALPHA = "11111111-1111-1111-1111-111111111111"
BETA = "22222222-2222-2222-2222-222222222222"
GAMMA = "33333333-3333-3333-3333-333333333333"


def pipeline(pid, name, created_at, tags=()):
    return {"id": pid, "name": name, "created_at": created_at, "tags": [TagRecord(name=t, label=t) for t in tags]}


@pytest.mark.parametrize(
    "sort,expected",
    [
        ("activite", ["zeta", "alpha", "beta"]),
        ("nom", ["alpha", "beta", "zeta"]),
        ("tag", ["alpha", "beta", "zeta"]),
    ],
)
def test_dod_5_sort_pipelines(sort, expected):
    pipelines = [
        pipeline(GAMMA, "zeta", "3"),
        pipeline(ALPHA, "alpha", "2", tags=["agent"]),
        pipeline(BETA, "beta", "1", tags=["veille"]),
    ]

    assert [p["name"] for p in sort_pipelines(pipelines, sort)] == expected


@pytest.mark.parametrize(
    "tags,sort,expected",
    [
        ([], "activite", ""),
        (["agent"], "activite", "?tag=agent"),
        (["agent", "veille"], "nom", "?tag=agent&tag=veille&tri=nom"),
    ],
)
def test_dod_4_query_string_carries_filter_and_sort(tags, sort, expected):
    assert query_string(tags, sort) == expected


def add_tag(name, facet="nature", label=None, active=True, pending=False):
    with get_db() as session:
        tag = Tag(name=name, type=facet, label=label or name.capitalize(), active=active, pending=pending)
        session.add(tag)
        session.flush()
        return tag.id


def tag_pipeline(pipeline_id, *names):
    with get_db() as session:
        for name in names:
            session.add(JobTag(pipeline_id=pipeline_id, tag_id=session.scalar(select(Tag.id).where(Tag.name == name))))


def tags_of(pipeline_id):
    with get_db() as session:
        return set(
            session.scalars(
                select(Tag.name).join(JobTag, JobTag.tag_id == Tag.id).where(JobTag.pipeline_id == pipeline_id)
            )
        )


def serve(mocker, runs=()):
    mocker.patch(
        "web.routes.jobs.jobs.list_pipelines",
        return_value=[
            {"id": ALPHA, "name": "alpha", "system_prompt": "PROMPT_ALPHA", "created_at": "2026-06-01T00:00:00+00:00"},
            {"id": BETA, "name": "beta", "system_prompt": "PROMPT_BETA", "created_at": "2026-06-02T00:00:00+00:00"},
            {"id": GAMMA, "name": "gamma", "system_prompt": "PROMPT_GAMMA", "created_at": "2026-06-03T00:00:00+00:00"},
        ],
    )
    mocker.patch("web.routes.jobs.jobs.list_runs", return_value=list(runs))


def listed(html):
    """Pipelines de la liste, dans l'ordre d'affichage."""
    spans = {name: f'<span class="tm-item-name">{name}</span>' for name in ("alpha", "beta", "gamma")}
    return sorted((name for name, span in spans.items() if span in html), key=lambda name: html.index(spans[name]))


@pytest.mark.integration
@pytest.mark.usefixtures("_db")
def test_dod_1_toggle_adds_tag_and_page_shows_it(client, mocker):
    serve(mocker)
    add_tag("agent")

    resp = client.post(f"/api/jobs/pipelines/{ALPHA}/tags", data={"tag": "agent"})

    assert resp.status_code == 200
    assert tags_of(ALPHA) == {"agent"}
    assert f'id="job-tags-{ALPHA}" hx-swap-oob="true"' in resp.text
    page = client.get(f"/jobs/pipelines/{ALPHA}").text
    assert 'aria-label="Retirer Agent"' in page


@pytest.mark.integration
@pytest.mark.usefixtures("_db")
@pytest.mark.parametrize("active", [True, False])
def test_dod_2_toggle_removes_carried_tag(client, mocker, active):
    serve(mocker)
    add_tag("agent", active=active)
    add_tag("veille")
    tag_pipeline(ALPHA, "agent", "veille")

    client.post(f"/api/jobs/pipelines/{ALPHA}/tags", data={"tag": "agent"})

    assert tags_of(ALPHA) == {"veille"}


@pytest.mark.integration
@pytest.mark.usefixtures("_db")
def test_dod_3_new_term_is_created_pending_in_nature_and_set(client, mocker):
    serve(mocker)

    resp = client.post(f"/api/jobs/pipelines/{ALPHA}/tags/new", data={"label": "Veille BOAMP"})

    assert resp.status_code == 200
    assert tags_of(ALPHA) == {"veille-boamp"}
    with get_db() as session:
        tag = session.scalar(select(Tag).where(Tag.name == "veille-boamp"))
        assert (tag.type, tag.label, tag.pending) == ("nature", "Veille BOAMP", True)


@pytest.mark.integration
@pytest.mark.usefixtures("app")
def test_dod_3_agent_term_is_seeded_by_migration_and_reseeding_is_harmless():
    path = next(Path("alembic/versions").glob("*_seed_agent_nature_tag.py"))
    spec = importlib.util.spec_from_file_location(path.stem, path)
    migration = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(migration)

    for _ in range(2):
        with get_engine().begin() as connection, Operations.context(MigrationContext.configure(connection)):
            migration.upgrade()

    with get_db() as session:
        tag = session.scalar(select(Tag).where(Tag.name == "agent"))
        assert (tag.type, tag.label, tag.active, tag.pending) == ("nature", "Agent", True, True)


@pytest.mark.integration
@pytest.mark.usefixtures("_db")
@pytest.mark.parametrize("label", ["", "  ", "!!!"])
def test_dod_3_new_term_refuses_empty_label(client, mocker, label):
    serve(mocker)

    assert client.post(f"/api/jobs/pipelines/{ALPHA}/tags/new", data={"label": label}).status_code == 400
    assert tags_of(ALPHA) == set()


@pytest.mark.integration
@pytest.mark.usefixtures("_db")
def test_dod_3_new_term_refuses_deactivated_term(client, mocker):
    serve(mocker)
    add_tag("obsolete", active=False)

    assert client.post(f"/api/jobs/pipelines/{ALPHA}/tags/new", data={"label": "obsolete"}).status_code == 400
    assert tags_of(ALPHA) == set()


@pytest.mark.integration
@pytest.mark.usefixtures("_db")
@pytest.mark.parametrize(
    "query,expected",
    [
        ("?tag=agent", ["alpha", "beta"]),
        ("?tag=agent&tag=veille", ["beta"]),
        ("", ["alpha", "beta", "gamma"]),
    ],
)
def test_dod_4_filter_keeps_pipelines_carrying_every_tag(client, mocker, query, expected):
    serve(mocker)
    add_tag("agent")
    add_tag("veille")
    tag_pipeline(ALPHA, "agent")
    tag_pipeline(BETA, "agent", "veille")

    assert sorted(listed(client.get(f"/jobs{query}").text)) == expected


@pytest.mark.integration
@pytest.mark.usefixtures("_db")
def test_dod_4_filter_on_uncarried_tag_says_so(client, mocker):
    serve(mocker)

    html = client.get("/jobs?tag=inconnu").text

    assert listed(html) == []
    assert "Aucun pipeline ne porte ce tag." in html


@pytest.mark.integration
@pytest.mark.usefixtures("_db")
def test_dod_4_filter_and_sort_stay_on_pipeline_links(client, mocker):
    serve(mocker)
    add_tag("agent")
    tag_pipeline(ALPHA, "agent")

    html = client.get("/jobs?tag=agent&tri=nom").text

    assert f'href="/jobs/pipelines/{ALPHA}?tag=agent&amp;tri=nom"' in html


@pytest.mark.integration
@pytest.mark.usefixtures("_db")
@pytest.mark.parametrize(
    "tri,expected",
    [
        ("activite", ["beta", "gamma", "alpha"]),
        ("nom", ["alpha", "beta", "gamma"]),
        ("tag", ["alpha", "beta", "gamma"]),
        ("n-importe-quoi", ["beta", "gamma", "alpha"]),
    ],
)
def test_dod_5_sort_orders_the_list(client, mocker, tri, expected):
    serve(
        mocker,
        runs=[{"id": "r1", "status": "completed", "pipeline_id": BETA, "created_at": "2026-06-05T00:00:00+00:00"}],
    )
    add_tag("agent")
    add_tag("veille")
    tag_pipeline(ALPHA, "agent")
    tag_pipeline(BETA, "veille")

    html = client.get(f"/jobs?tri={tri}").text

    assert listed(html) == expected


@pytest.mark.integration
@pytest.mark.usefixtures("_db")
@pytest.mark.parametrize("email", ["chargee@inclusion.gouv.fr", "autre@inclusion.gouv.fr"])
def test_dod_6_any_connected_user_can_tag(client, mocker, email):
    serve(mocker)
    add_tag("agent")

    resp = client.post(f"/api/jobs/pipelines/{ALPHA}/tags", data={"tag": "agent"}, headers={"X-Forwarded-Email": email})

    assert resp.status_code == 200
    assert tags_of(ALPHA) == {"agent"}


@pytest.mark.integration
@pytest.mark.usefixtures("_db")
@pytest.mark.parametrize(
    "path,data",
    [("/tags", {"tag": "agent"}), ("/tags/new", {"label": "veille"})],
)
def test_dod_6_unknown_pipeline_is_404_and_writes_nothing(client, mocker, path, data):
    serve(mocker)
    add_tag("agent")
    unknown = "44444444-4444-4444-4444-444444444444"

    assert client.post(f"/api/jobs/pipelines/{unknown}{path}", data=data).status_code == 404
    assert tags_of(unknown) == set()


@pytest.mark.integration
@pytest.mark.usefixtures("_db")
@pytest.mark.parametrize(
    "path,data",
    [("/tags", {"tag": "agent"}), ("/tags/new", {"label": "veille"})],
)
def test_dod_6_jobs_service_down_is_502_and_writes_nothing(client, mocker, path, data):
    mocker.patch(
        "web.routes.jobs.jobs.list_pipelines",
        side_effect=httpx.ConnectError("down", request=httpx.Request("GET", "http://x")),
    )
    add_tag("agent")

    assert client.post(f"/api/jobs/pipelines/{ALPHA}{path}", data=data).status_code == 502
    assert tags_of(ALPHA) == set()


@pytest.mark.integration
@pytest.mark.usefixtures("_db")
@pytest.mark.parametrize("name", ["inconnu", "obsolete"])
def test_dod_1_toggle_refuses_unknown_or_inactive_term(client, mocker, name):
    serve(mocker)
    add_tag("obsolete", active=False)

    assert client.post(f"/api/jobs/pipelines/{ALPHA}/tags", data={"tag": name}).status_code == 400
    assert tags_of(ALPHA) == set()


@pytest.mark.integration
@pytest.mark.usefixtures("_db")
def test_dod_7_tag_sync_counts_job_tags_as_assigned(client):
    tag_id = add_tag("agent")
    tag_pipeline(ALPHA, "agent")

    with get_db() as session:
        assert tag_id in assigned_tag_ids(session)


@pytest.mark.integration
@pytest.mark.usefixtures("_db")
def test_dod_8_jobs_page_renders_filters_sort_and_editor(client, mocker):
    serve(mocker)
    add_tag("agent")
    add_tag("veille", pending=True)
    add_tag("siae", facet="audience")
    tag_pipeline(ALPHA, "agent")
    tag_pipeline(BETA, "agent")

    html = client.get(f"/jobs/pipelines/{ALPHA}").text

    assert 'href="/jobs?tag=agent"' in html
    assert 'Agent <span class="opacity-75 ms-1">2</span>' in html
    assert "Tri : Activité récente" in html
    assert 'href="/jobs?tri=nom"' in html
    assert '<option value="veille">Veille</option>' in html
    assert "proposé" not in html
    assert 'value="agent"' not in html
    assert "Siae" not in html
    assert f'hx-post="/api/jobs/pipelines/{ALPHA}/tags/new"' in html


@pytest.mark.integration
@pytest.mark.usefixtures("_db")
@pytest.mark.parametrize(
    "path,data",
    [("/tags", {"tag": "agent"}), ("/tags/new", {"label": "veille"})],
)
def test_dod_6_tagging_log_strips_line_breaks_from_user_email(client, mocker, caplog, path, data):
    serve(mocker)
    add_tag("agent")
    caplog.set_level("INFO", logger="web.routes.jobs")

    resp = client.post(
        f"/api/jobs/pipelines/{ALPHA}{path}", data=data, headers={"X-Forwarded-Email": "a@b.fr\r\nFAUX journal"}
    )

    assert resp.status_code == 200
    assert [r.getMessage() for r in caplog.records if "FAUX" in r.getMessage()] == [
        f"job {ALPHA} : {'tag agent basculé' if path == '/tags' else 'terme proposé veille'} par a@b.frFAUX journal"
    ]
