import datetime
import gzip
import json

import pytest

from lib import zendesk_changeset as cs
from lib.zendesk import Article, ZendeskError


class FakeStore:
    def __init__(self):
        self.files: dict[str, bytes] = {}

    def upload(self, path, content, content_type=None):
        self.files[path] = content
        return True

    def download(self, path):
        return self.files.get(path)

    def get_url(self, path, expires_in=3600):
        return f"https://s3.example/{path}"

    def list_directories(self, prefix=""):
        return sorted({p[len(prefix) :].split("/")[0] for p in self.files if p.startswith(prefix)})

    def json(self, path):
        raw = self.files[path]
        return json.loads(gzip.decompress(raw) if path.endswith(".gz") else raw)


class FakeZendesk:
    """In-memory Guide: get_article reads, update_article_content writes and bumps updated_at."""

    def __init__(self, articles, sections=(), categories=(), fail_on=None):
        self.articles = {a.id: a for a in articles}
        self.sections, self.categories = list(sections), list(categories)
        self.fail_on = fail_on
        self.writes = []

    def list_articles(self):
        return list(self.articles.values())

    def list_sections(self):
        return self.sections

    def list_categories(self):
        return self.categories

    def get_article(self, article_id):
        if article_id not in self.articles:
            raise ZendeskError(404, "not found")
        return self.articles[article_id]

    def update_article_content(self, article_id, title, body, locale="fr"):
        if article_id == self.fail_on:
            raise ConnectionError("réseau coupé")
        old = self.articles[article_id]
        self.articles[article_id] = Article(
            id=old.id,
            title=title,
            body=body,
            section_id=old.section_id,
            draft=old.draft,
            updated_at=old.updated_at + "+1",
            html_url=old.html_url,
        )
        self.writes.append(article_id)
        return self.articles[article_id]


def article(article_id, title="Titre", body="<p>Dora est un service.</p>\n<p>Autre ligne.</p>", draft=False):
    return Article(
        id=article_id,
        title=title,
        body=body,
        section_id=1,
        draft=draft,
        updated_at="t0",
        html_url=f"https://aide.example/hc/fr/articles/{article_id}",
    )


@pytest.fixture
def store(mocker):
    fake = FakeStore()
    mocker.patch.object(cs.s3, "zendesk", fake)
    mocker.patch.object(cs, "datetime", mocker.MagicMock(now=lambda: datetime.datetime(2026, 9, 11, 10, 32)))
    return fake


def planned(api, ids=None):
    articles = None if ids is None else [api.get_article(i) for i in ids]
    return cs.replace(api, "Dora", "Nova", articles=articles)["id"]


def test_dod_1_replace_lists_changed_articles_with_diff_and_writes_nothing(store):
    api = FakeZendesk([
        article(1),
        article(2, body="<p>Sans le mot.</p>"),
        article(3, title="Dora pour tous", draft=True),
    ])

    result = cs.replace(api, "Dora", "Nova", label="Renommer Dora")

    assert api.writes == []
    assert result["id"] == "2026-09-11-1032-renommer-dora"
    assert result["status"] == "planned"
    assert result["scanned"] == 3
    assert [e["id"] for e in result["articles"]] == [1, 3]
    assert result["articles"][0]["lines_changed"] == 1
    assert result["diff_url"] == "https://s3.example/changesets/2026-09-11-1032-renommer-dora/diff.md"
    prefix = "changesets/2026-09-11-1032-renommer-dora"
    diff = store.files[f"{prefix}/diff.md"].decode()
    assert "# Renommer Dora" in diff
    assert "-<p>Dora est un service.</p>" in diff
    assert "+<p>Nova est un service.</p>" in diff
    assert "Titre : 'Dora pour tous' → 'Nova pour tous'" in diff
    assert store.json(f"{prefix}/manifest.json")["articles"] == result["articles"]


def test_dod_2_plan_on_one_article_touches_only_it(store, mocker):
    api = FakeZendesk([article(1), article(2)])
    spy = mocker.spy(api, "list_articles")

    def add_paragraph(title, body):
        return title, body.replace("<p>Autre ligne.</p>", "<p>Autre ligne.</p>\n<p>Encart.</p>")

    result = cs.plan([api.get_article(1)], add_paragraph, "ajout encart")

    assert spy.call_count == 0
    assert [e["id"] for e in result["articles"]] == [1]
    assert "+<p>Encart.</p>" in store.files[f"changesets/{result['id']}/diff.md"].decode()


def test_dod_3_planned_changeset_stays_inert_until_applied(store):
    api = FakeZendesk([article(1)])
    changeset_id = planned(api)

    assert api.writes == []
    assert cs.show(changeset_id)["status"] == "planned"
    assert "Dora" in api.get_article(1).body
    assert [m["id"] for m in cs.list_changesets()] == [changeset_id]


def test_dod_4_apply_writes_every_article_and_counts_them(store):
    api = FakeZendesk([article(i) for i in range(1, 101)])
    changeset_id = planned(api)

    report = cs.apply(api, changeset_id)

    assert report == {"id": changeset_id, "status": "applied", "written": 100, "skipped": [], "errors": []}
    assert len(api.writes) == 100
    assert all("Nova" in a.body for a in api.articles.values())
    applied = store.json(f"changesets/{changeset_id}/applied.json")
    assert applied["written"]["1"] == {"title": "Titre", "body": api.articles[1].body, "updated_at": "t0+1"}


def test_dod_5_apply_skips_articles_modified_since_plan(store):
    api = FakeZendesk([article(1), article(2)])
    changeset_id = planned(api)
    api.update_article_content(2, "Titre", "<p>Quelqu'un a édité Dora.</p>")

    report = cs.apply(api, changeset_id)

    assert report["written"] == 1
    assert report["skipped"] == [
        {"id": 2, "reason": "modifié entre-temps", "expected_updated_at": "t0", "updated_at": "t0+1"}
    ]
    assert "Quelqu'un" in api.get_article(2).body


def test_dod_5_apply_records_http_errors_and_continues(store):
    api = FakeZendesk([article(1), article(2)])
    changeset_id = planned(api)
    del api.articles[1]

    report = cs.apply(api, changeset_id)

    assert report["written"] == 1
    assert report["errors"] == [{"id": 1, "error": "Zendesk 404: not found"}]


def test_dod_6_revert_restores_written_articles_unless_edited_after_apply(store):
    api = FakeZendesk([article(1), article(2), article(3)])
    changeset_id = planned(api)
    api.update_article_content(3, "Titre", "<p>édité avant apply</p>")
    cs.apply(api, changeset_id)
    api.update_article_content(2, "Titre", "<p>édité après apply</p>")

    report = cs.revert(api, changeset_id)

    assert report["status"] == "reverted"
    assert report["written"] == 1
    assert [s["id"] for s in report["skipped"]] == [2]
    assert api.articles[1].body == article(1).body
    assert api.articles[2].body == "<p>édité après apply</p>"
    assert api.articles[3].body == "<p>édité avant apply</p>"
    assert store.json(f"changesets/{changeset_id}/reverted.json")["written"].keys() == {"1"}


def test_dod_7_export_articles_dumps_raw_payloads_gzipped_with_a_link(store):
    api = FakeZendesk([article(1), article(2)])
    for a in api.articles.values():
        a.raw = {"id": a.id, "body": a.body, "extra": True}

    result = cs.export_articles(api)

    assert result == {
        "path": "exports/2026-09-11T10-32-articles.json.gz",
        "count": 2,
        "url": "https://s3.example/exports/2026-09-11T10-32-articles.json.gz",
    }
    assert store.json(result["path"]) == [a.raw for a in api.articles.values()]


@pytest.mark.parametrize(
    "transform",
    [lambda t, b: (t, b), lambda t, b: (t, b.replace("Nova", "Neo"))],
    ids=["identity", "pattern absent"],
)
def test_dod_9_plan_returns_none_when_nothing_changes(store, transform):
    assert cs.plan([article(1)], transform, "rien") is None
    assert store.files == {}


def test_dod_10_snapshots_hold_only_touched_articles_and_no_full_export(store):
    api = FakeZendesk([article(i) for i in range(1, 11)] + [article(11, body="<p>Rien.</p>")])
    changeset_id = planned(api)
    cs.apply(api, changeset_id)

    prefix = f"changesets/{changeset_id}"
    assert set(store.json(f"{prefix}/before.json.gz")) == {str(i) for i in range(1, 11)}
    assert set(store.json(f"{prefix}/after.json.gz")) == {str(i) for i in range(1, 11)}
    assert store.json(f"{prefix}/before.json.gz")["1"] == {
        "title": "Titre",
        "body": article(1).body,
        "updated_at": "t0",
    }
    assert not [p for p in store.files if p.startswith("exports/")]


@pytest.mark.parametrize(
    "kwargs, expected_id, expected_body, expected_title",
    [
        ({"pattern": "Dora", "replacement": "Nova"}, "1", "<p>Nova est un service.</p>", "Nova pour tous"),
        ({"pattern": "dora", "replacement": "Nova"}, "3", "<p>Nova est un service.</p>", "Nova pour tous"),
        ({"pattern": "D.ra", "replacement": "Nova"}, "2", "<p>Nova est un service.</p>", "Nova pour tous"),
        (
            {"pattern": r"D(o)ra", "replacement": r"N\1va", "regex": True},
            "1",
            "<p>Nova est un service.</p>",
            "Nova pour tous",
        ),
        (
            {"pattern": "Dora", "replacement": r"C:\dora"},
            "1",
            r"<p>C:\dora est un service.</p>",
            r"C:\dora pour tous",
        ),
    ],
    ids=["literal", "case-sensitive", "dot is literal", "regex on request", "backslash in replacement"],
)
def test_dod_11_replace_is_literal_unless_regex_requested(store, kwargs, expected_id, expected_body, expected_title):
    api = FakeZendesk([
        article(1, title="Dora pour tous", body="<p>Dora est un service.</p>"),
        article(2, title="D.ra pour tous", body="<p>D.ra est un service.</p>"),
        article(3, title="dora pour tous", body="<p>dora est un service.</p>"),
    ])
    result = cs.replace(api, **kwargs)
    after = store.json(f"changesets/{result['id']}/after.json.gz")
    assert list(after) == [expected_id]
    assert (after[expected_id]["body"], after[expected_id]["title"]) == (expected_body, expected_title)
    assert result["params"] == {
        "pattern": kwargs["pattern"],
        "replacement": kwargs["replacement"],
        "regex": kwargs.get("regex", False),
        "include_markup": False,
    }
    assert result["label"] == f"remplacer {kwargs['pattern']}"


def test_dod_12_empty_pattern_is_refused(store):
    api = FakeZendesk([article(1)])
    with pytest.raises(ValueError, match="vide"):
        cs.replace(api, "", "Nova")
    assert store.files == {}


@pytest.mark.parametrize(
    "action, setup, message",
    [
        (cs.apply, lambda api, cid: cs.apply(api, cid), "est applied, attendu planned ou applying"),
        (cs.revert, lambda api, cid: None, "est planned, attendu applied ou applying"),
        (cs.revert, lambda api, cid: (cs.apply(api, cid), cs.revert(api, cid)), "est reverted, attendu applied"),
        (cs.apply, lambda api, cid: cs.s3.zendesk.files.clear(), "introuvable"),
    ],
    ids=["apply twice", "revert unapplied", "revert twice", "unknown id"],
)
def test_dod_14_apply_and_revert_refuse_wrong_status_without_writing(store, action, setup, message):
    api = FakeZendesk([article(1)])
    changeset_id = planned(api)
    setup(api, changeset_id)
    writes_before = list(api.writes)
    with pytest.raises(ValueError, match=message):
        action(api, changeset_id)
    assert api.writes == writes_before


def test_dod_15_interrupted_apply_keeps_written_articles_revertible_and_names_the_rest(store):
    api = FakeZendesk([article(1), article(2), article(3)], fail_on=2)
    changeset_id = planned(api)

    with pytest.raises(ConnectionError):
        cs.apply(api, changeset_id)

    shown = cs.show(changeset_id)
    assert shown["status"] == "applying"
    assert list(shown["applied"]["written"]) == ["1"]
    assert [e["id"] for e in shown["remaining"]] == [2, 3]

    api.fail_on = None
    assert cs.apply(api, changeset_id)["written"] == 3
    assert api.writes == [1, 2, 3]


def test_dod_15_interrupted_apply_can_be_reverted(store):
    api = FakeZendesk([article(1), article(2)], fail_on=2)
    changeset_id = planned(api)
    with pytest.raises(ConnectionError):
        cs.apply(api, changeset_id)

    api.fail_on = None
    report = cs.revert(api, changeset_id)

    assert report["written"] == 1
    assert api.articles[1].body == article(1).body
    assert "Dora" in api.articles[2].body


def test_dod_16_section_and_category_names_are_named_but_untouched(store):
    api = FakeZendesk(
        [article(1)],
        sections=[{"id": 10, "name": "Utiliser Dora"}, {"id": 11, "name": "Autre"}],
        categories=[{"id": 20, "name": "Dora et vous"}],
    )
    result = cs.replace(api, "Dora", "Nova")

    assert result["structure_hits"] == [
        {"kind": "section", "id": 10, "name": "Utiliser Dora"},
        {"kind": "category", "id": 20, "name": "Dora et vous"},
    ]
    cs.apply(api, result["id"])
    assert api.sections[0]["name"] == "Utiliser Dora"


def test_dod_17_replace_leaves_links_and_attributes_alone_and_names_them(store):
    body = '<p>Dora aide. <a href="https://dora.inclusion.gouv.fr" title="Dora">le site Dora</a></p><img alt="logo Dora" src="/dora.png">'
    api = FakeZendesk([article(1, body=body), article(2, body='<a href="/Dora">lien</a>')])

    result = cs.replace(api, "Dora", "Babouche")

    after = store.json(f"changesets/{result['id']}/after.json.gz")
    assert (
        after["1"]["body"]
        == '<p>Babouche aide. <a href="https://dora.inclusion.gouv.fr" title="Dora">le site Babouche</a></p><img alt="logo Dora" src="/dora.png">'
    )
    assert "2" not in after
    assert result["markup_hits"] == {1: 2, 2: 1}
    assert store.json(f"changesets/{result['id']}/manifest.json")["markup_hits"] == {"1": 2, "2": 1}


def test_dod_17_markup_is_replaced_only_on_explicit_request(store):
    api = FakeZendesk([article(1, body='<a href="/Dora" title="Dora">Dora</a>')])

    result = cs.replace(api, "Dora", "Babouche", include_markup=True)

    after = store.json(f"changesets/{result['id']}/after.json.gz")
    assert after["1"]["body"] == '<a href="/Babouche" title="Babouche">Babouche</a>'
    assert result["params"]["include_markup"] is True


def test_show_and_list_changesets(store):
    api = FakeZendesk([article(1)])
    changeset_id = planned(api)
    cs.apply(api, changeset_id)

    shown = cs.show(changeset_id)
    assert (shown["status"], shown["applied"]["written"].keys(), shown["remaining"], shown["reverted"]) == (
        "applied",
        {"1"},
        [],
        None,
    )
    assert shown["diff_url"].endswith("/diff.md")
    assert [m["id"] for m in cs.list_changesets()] == [changeset_id]
    with pytest.raises(ValueError, match="introuvable"):
        cs.show("nope")


def test_write_json_raises_on_upload_failure(store, mocker):
    mocker.patch.object(store, "upload", return_value=False)
    with pytest.raises(RuntimeError, match="S3 upload failed"):
        cs.write_json("x.json", {})


@pytest.mark.external
def test_sandbox_roundtrip(store):
    """Plan → apply → revert on a throwaway draft article in the Zendesk sandbox section (S3 in memory)."""
    from lib.sources import get_zendesk

    api = get_zendesk()
    # Section « Charte édito » of the « Bac a sable des emplois » category.
    created = api.create_article(29763119236753, "[test changeset — à supprimer]", "<p>Dora test.</p>")
    try:
        result = cs.replace(api, "Dora", "Nova", articles=[api.get_article(created.id)], label="test roundtrip")
        assert cs.apply(api, result["id"])["written"] == 1
        assert "Nova" in api.get_article(created.id).body
        assert cs.revert(api, result["id"])["written"] == 1
        assert "Dora" in api.get_article(created.id).body
    finally:
        api._request("DELETE", f"help_center/articles/{created.id}.json")
