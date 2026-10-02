import dataclasses
import datetime

import pytest

from lib import zendesk_changeset as cs
from lib import zendesk_macros as zm
from lib.sources import get_zendesk
from lib.zendesk import Macro, ZendeskError
from tests.test_zendesk_changeset import FakeStore, article
from tests.test_zendesk_changeset import FakeZendesk as FakeGuide

REPLY = "<p>Bonjour,</p><p>Dora est un service.</p><p>Bonne journée.</p>"


class FakeZendesk(FakeGuide):
    """In-memory macros on top of the in-memory Guide; same fail_on / fail_after semantics."""

    def __init__(self, macros=(), articles=(), lookups=None, **kwargs):
        super().__init__(articles, **kwargs)
        self.macros = {m.id: m for m in macros}
        self.lookups = lookups or {}

    def list_macros(self):
        return list(self.macros.values())

    def get_macro(self, macro_id):
        if macro_id not in self.macros:
            raise ZendeskError(404, "not found")
        return self.macros[macro_id]

    def update_macro(self, macro_id, **fields):
        if macro_id == self.fail_on:
            raise ConnectionError("réseau coupé")
        old = self.macros[macro_id]
        self.macros[macro_id] = dataclasses.replace(old, **fields, updated_at=old.updated_at + "+1")
        self.writes.append(macro_id)
        if macro_id == self.fail_after:
            raise self.after_write_error
        return self.macros[macro_id]

    def lookup(self, resource, item_id):
        return self.lookups.get((resource, int(item_id)))


def macro(macro_id, title="Candidat::Relance", reply=REPLY, active=True, actions=None, description=""):
    return Macro(
        id=macro_id,
        title=title,
        description=description,
        active=active,
        actions=actions
        if actions is not None
        else [
            {"field": "status", "value": "pending"},
            {"field": "comment_value_html", "value": reply},
        ],
        updated_at="t0",
        html_url=f"https://zd.example/admin/workspaces/agent-workspace/macros/{macro_id}",
    )


def reply_of(fields):
    return next(a["value"] for a in fields["actions"] if a["field"] == "comment_value_html")


@pytest.fixture
def store(mocker):
    fake = FakeStore()
    mocker.patch.object(cs.s3, "zendesk", fake)
    mocker.patch.object(cs, "datetime", mocker.MagicMock(now=lambda: datetime.datetime(2026, 10, 2, 11, 5)))
    return fake


def planned(api, ids=None):
    macros = None if ids is None else [api.get_macro(i) for i in ids]
    return zm.replace(api, "Dora", "Nova", macros=macros)["id"]


def test_dod_1_macros_are_grouped_by_first_title_segment_with_uncategorised_last():
    macros = [
        macro(1, title="Prolongations::Refus"),
        macro(2, title="Bienvenue"),
        macro(3, title="Candidat::Relance::J+7", active=False),
        macro(4, title=" Prolongation :: Accord"),
        macro(5, title="candidature::Suivi"),
    ]

    grouped = zm.by_category(macros)

    assert list(grouped) == ["Candidat", "candidature", "Prolongation", "Prolongations", "Sans catégorie"]
    assert [m.id for m in grouped["Prolongation"]] == [4]
    assert [m.id for m in grouped["Sans catégorie"]] == [2]
    assert grouped["Candidat"][0].active is False


def test_dod_2_describe_names_every_action_and_marks_deleted_references():
    target = macro(
        7,
        title="Candidat::Relance",
        actions=[
            {"field": "status", "value": "pending"},
            {"field": "custom_status_id", "value": "55"},
            {"field": "assignee_id", "value": "current_user"},
            {"field": "group_id", "value": "66"},
            {"field": "custom_fields_77", "value": "employeur_siae"},
            {"field": "brand_id", "value": "404"},
            {"field": "current_tags", "value": "relance nia-ntt"},
            {"field": "comment_mode_is_public", "value": "false"},
            {"field": "comment_value_html", "value": REPLY},
        ],
        description="Relancer le candidat",
    )
    target.restriction = {"type": "Group", "id": 66, "ids": [66, 88]}
    target.usage_30d = 12
    api = FakeZendesk(
        [target],
        lookups={
            ("custom_statuses", 55): {"agent_label": "En attente du candidat"},
            ("groups", 66): {"name": "Support N1"},
            ("ticket_fields", 77): {
                "title": "Type demandeur",
                "custom_field_options": [{"value": "employeur_siae", "name": "Employeur::SIAE"}],
            },
        },
    )

    described = zm.describe(api, target)

    assert {k: described[k] for k in ("id", "title", "category", "active", "description", "usage_30d")} == {
        "id": 7,
        "title": "Candidat::Relance",
        "category": "Candidat",
        "active": True,
        "description": "Relancer le candidat",
        "usage_30d": 12,
    }
    assert described["restricted_to"] == ["Support N1", "inconnu (#88)"]
    assert described["actions"] == [
        {"label": "Statut", "value": "En attente"},
        {"label": "Statut personnalisé", "value": "En attente du candidat"},
        {"label": "Assigné à", "value": "l'agent qui applique la macro"},
        {"label": "Groupe", "value": "Support N1"},
        {"label": "Type demandeur", "value": "Employeur::SIAE"},
        {"label": "Marque", "value": "inconnu (#404)"},
        {"label": "Étiquettes ajoutées", "value": "relance nia-ntt"},
        {"label": "Réponse publique", "value": "non"},
        {"label": "Réponse", "value": REPLY},
    ]


def test_dod_2_unrestricted_macro_deleted_ticket_field_and_list_values():
    target = macro(
        8,
        actions=[
            {"field": "custom_fields_99", "value": "x"},
            {"field": "custom_fields_77", "value": ["employeur_siae", "autre"]},
            {"field": "side_conversation_slack", "value": ["<p>Hello</p>", "canal", "text/html"]},
        ],
    )
    api = FakeZendesk(
        [target],
        lookups={
            ("ticket_fields", 77): {
                "title": "Type demandeur",
                "custom_field_options": [{"value": "employeur_siae", "name": "Employeur::SIAE"}],
            }
        },
    )
    described = zm.describe(api, target)
    assert described["restricted_to"] is None
    assert described["actions"] == [
        {"label": "Champ inconnu (#99)", "value": "x"},
        {"label": "Type demandeur", "value": ["Employeur::SIAE", "autre"]},
        {"label": "side_conversation_slack", "value": ["<p>Hello</p>", "canal", "text/html"]},
    ]


def test_dod_3_replace_lists_changed_macros_by_paragraph_and_writes_nothing(store):
    api = FakeZendesk([
        macro(1),
        macro(2, reply="<p>Sans le mot.</p>"),
        macro(3, title="Dora::Accès", active=False, reply="<p>Rien.</p>", description="Aide Dora"),
        macro(
            4,
            reply="<p>Rien.</p>",
            actions=[{"field": "subject", "value": "Votre accès Dora"}, {"field": "current_tags", "value": "Dora"}],
        ),
    ])

    result = zm.replace(api, "Dora", "Nova", label="Renommer Dora")

    assert api.writes == []
    assert result["id"] == "2026-10-02-110500-renommer-dora"
    assert (result["status"], result["kind"], result["scanned"]) == ("planned", "macros", 4)
    assert [e["id"] for e in result["articles"]] == [1, 3, 4]
    after = store.json(f"changesets/{result['id']}/after.json.gz")
    assert reply_of(after["1"]) == "<p>Bonjour,</p><p>Nova est un service.</p><p>Bonne journée.</p>"
    assert (after["3"]["title"], after["3"]["description"], after["3"]["active"]) == ("Nova::Accès", "Aide Nova", False)
    assert after["4"]["actions"] == [
        {"field": "subject", "value": "Votre accès Nova"},
        {"field": "current_tags", "value": "Dora"},
    ]
    diff = store.files[f"changesets/{result['id']}/diff.md"].decode()
    assert "-<p>Dora est un service.</p>\n+<p>Nova est un service.</p>" in diff
    assert "-<p>Bonjour,</p>" not in diff
    assert "Titre : 'Dora::Accès' → 'Nova::Accès'" in diff
    assert "-Description : Aide Dora\n+Description : Aide Nova" in diff


def test_dod_4_deactivating_a_category_touches_that_exact_category_only(store):
    api = FakeZendesk([
        macro(1, title="Prolongation::Accord"),
        macro(2, title="Prolongations::Refus"),
        macro(3, title="Prolongation::Refus", active=False),
    ])
    targets = [m for m in api.list_macros() if zm.category(m.title) == "Prolongation"]

    result = zm.plan(targets, lambda fields: {**fields, "active": False}, "désactiver Prolongation")

    assert [e["id"] for e in result["articles"]] == [1]
    assert "-Active : oui\n+Active : non" in store.files[f"changesets/{result['id']}/diff.md"].decode()
    assert api.writes == []


def test_dod_5_plan_on_one_macro_touches_only_it(store, mocker):
    api = FakeZendesk([macro(1), macro(2)])
    spy = mocker.spy(api, "list_macros")

    def add_signature(fields):
        actions = [
            {**a, "value": a["value"] + "<p>L'équipe support</p>"} if a["field"] == "comment_value_html" else a
            for a in fields["actions"]
        ]
        return {**fields, "actions": actions}

    result = zm.plan([api.get_macro(1)], add_signature, "signature")

    assert spy.call_count == 0
    assert [e["id"] for e in result["articles"]] == [1]
    assert "+<p>L'équipe support</p>" in store.files[f"changesets/{result['id']}/diff.md"].decode()


def test_dod_5_a_transform_editing_actions_in_place_is_still_seen_as_a_change(store):
    api = FakeZendesk([macro(1)])

    def append_tag(fields):
        fields["actions"].append({"field": "current_tags", "value": "relance"})
        return fields

    result = zm.plan([api.get_macro(1)], append_tag, "étiquette")

    assert [e["id"] for e in result["articles"]] == [1]
    assert len(api.macros[1].actions) == 2
    assert len(store.json(f"changesets/{result['id']}/before.json.gz")["1"]["actions"]) == 2


def test_dod_5_a_transform_adding_a_field_it_cannot_show_is_refused(store):
    with pytest.raises(ValueError, match="exactement les champs"):
        zm.plan([macro(1)], lambda f: {**f, "restriction": {"type": "Group", "id": 1}}, "restreindre")
    assert store.files == {}


def test_dod_6_unapproved_plan_stays_inert_and_is_still_listed_later(store):
    api = FakeZendesk([macro(1)])
    changeset_id = planned(api)

    assert api.writes == []
    assert cs.show(changeset_id)["status"] == "planned"
    assert "Dora" in reply_of(cs.content(api.get_macro(1)))
    assert [m["id"] for m in cs.list_changesets()] == [changeset_id]


def test_dod_7_apply_writes_every_macro_and_counts_them(store):
    api = FakeZendesk([macro(i) for i in range(1, 323)])
    changeset_id = planned(api)

    report = cs.apply(api, changeset_id)

    assert report == {"id": changeset_id, "status": "applied", "written": 322, "skipped": [], "errors": []}
    assert all("Nova" in reply_of(cs.content(m)) for m in api.macros.values())


def test_dod_8_apply_skips_macros_edited_or_deleted_since_plan(store):
    api = FakeZendesk([macro(1), macro(2), macro(3), macro(4)])
    changeset_id = planned(api)
    api.update_macro(2, title="Retouché à la main")
    del api.macros[3]
    api.macros[4] = dataclasses.replace(api.macros[4], updated_at="t-reordered")

    report = cs.apply(api, changeset_id)

    assert (report["status"], report["written"], report["errors"]) == ("applied", 2, [])
    assert report["skipped"] == [
        {
            "id": 2,
            "title": "Candidat::Relance",
            "reason": "modifié entre-temps",
            "expected_updated_at": "t0",
            "updated_at": "t0+1",
        },
        {
            "id": 3,
            "title": "Candidat::Relance",
            "reason": "supprimé entre-temps",
            "expected_updated_at": "t0",
            "updated_at": None,
        },
    ]
    assert api.macros[2].title == "Retouché à la main"
    assert "Nova" in reply_of(cs.content(api.macros[4]))


def test_dod_9_revert_restores_whole_macros_unless_edited_or_deleted_after_apply(store):
    originals = [
        macro(1, title="Dora::A", description="Dora"),
        macro(2),
        macro(3),
    ]
    api = FakeZendesk(originals)
    result = zm.replace(api, "Dora", "Nova")
    cs.apply(api, result["id"])
    api.update_macro(2, active=False)
    del api.macros[3]

    report = cs.revert(api, result["id"])

    assert (report["status"], report["written"]) == ("reverted", 1)
    assert [(s["id"], s["reason"]) for s in report["skipped"]] == [
        (2, "modifié entre-temps"),
        (3, "supprimé entre-temps"),
    ]
    assert cs.editable(cs.content(api.macros[1])) == cs.editable(cs.content(originals[0]))
    assert api.macros[2].active is False
    assert 3 not in api.macros


@pytest.mark.parametrize(
    "transform",
    [lambda f: f, lambda f: {**f, "title": f["title"].replace("Nova", "Neo")}],
    ids=["identity", "pattern absent"],
)
def test_dod_11_plan_returns_none_when_nothing_changes(store, transform):
    assert zm.plan([macro(1)], transform, "rien") is None
    assert zm.replace(FakeZendesk([macro(1)]), "Absent", "Nova") is None
    assert store.files == {}


@pytest.mark.parametrize(
    "kwargs, expected_id, expected_title",
    [
        ({"pattern": "Dora", "replacement": "Nova"}, "1", "Nova::A"),
        ({"pattern": "dora", "replacement": "Nova"}, "3", "Nova::A"),
        ({"pattern": "D.ra", "replacement": "Nova"}, "2", "Nova::A"),
        ({"pattern": r"D(o)ra", "replacement": r"N\1va", "regex": True}, "1", "Nova::A"),
        ({"pattern": "Dora", "replacement": r"C:\dora"}, "1", r"C:\dora::A"),
    ],
    ids=["literal", "case-sensitive", "dot is literal", "regex on request", "backslash in replacement"],
)
def test_dod_12_replace_is_literal_unless_regex_requested(store, kwargs, expected_id, expected_title):
    api = FakeZendesk([
        macro(1, title="Dora::A", reply="<p>Rien.</p>"),
        macro(2, title="D.ra::A", reply="<p>Rien.</p>"),
        macro(3, title="dora::A", reply="<p>Rien.</p>"),
    ])
    result = zm.replace(api, **kwargs)
    after = store.json(f"changesets/{result['id']}/after.json.gz")
    assert list(after) == [expected_id]
    assert after[expected_id]["title"] == expected_title
    diff = store.files[f"changesets/{result['id']}/diff.md"].decode()
    assert f"- regex : {kwargs.get('regex', False)!r}" in diff


def test_dod_12_empty_pattern_is_refused(store):
    with pytest.raises(ValueError, match="vide"):
        zm.replace(FakeZendesk([macro(1)]), "", "Nova")
    assert store.files == {}


@pytest.mark.parametrize(
    "action, setup, message",
    [
        (cs.apply, lambda api, cid: cs.apply(api, cid), "est applied, attendu planned ou applying"),
        (cs.revert, lambda api, cid: None, "est planned, attendu applied ou applying ou reverting"),
        (cs.revert, lambda api, cid: (cs.apply(api, cid), cs.revert(api, cid)), "est reverted, attendu applied"),
    ],
    ids=["apply twice", "revert unapplied", "revert twice"],
)
def test_dod_14_apply_and_revert_refuse_wrong_status_without_writing(store, action, setup, message):
    api = FakeZendesk([macro(1)])
    changeset_id = planned(api)
    setup(api, changeset_id)
    writes_before = list(api.writes)
    with pytest.raises(ValueError, match=message):
        action(api, changeset_id)
    assert api.writes == writes_before


def test_dod_15_interrupted_apply_names_the_rest_resumes_and_reverts(store):
    api = FakeZendesk([macro(1), macro(2), macro(3)], fail_after=2)
    changeset_id = planned(api)

    with pytest.raises(ConnectionError):
        cs.apply(api, changeset_id)

    shown = cs.show(changeset_id)
    assert (shown["status"], list(shown["applied"]["written"])) == ("applying", ["1"])
    assert [e["id"] for e in shown["remaining"]] == [2, 3]

    api.fail_after = None
    assert cs.apply(api, changeset_id)["written"] == 3
    assert api.writes == [1, 2, 3]
    assert cs.revert(api, changeset_id)["written"] == 3
    assert all("Dora" in reply_of(cs.content(m)) for m in api.macros.values())


def test_dod_16_replace_leaves_links_attributes_and_zendesk_placeholders_alone_and_names_them(store):
    reply = (
        '<p>Dora aide. <a href="https://dora.inclusion.gouv.fr" title="Dora">le site Dora</a></p>'
        "<p>Ticket {{ticket.Dora_id}} {% if Dora %}Dora{% endif %} {{dc.dora}}</p>"
    )
    api = FakeZendesk([macro(1, reply=reply), macro(2, reply="<p>{{dc.Dora}}</p>")])

    result = zm.replace(api, "Dora", "Nova")

    after = store.json(f"changesets/{result['id']}/after.json.gz")
    assert reply_of(after["1"]) == (
        '<p>Nova aide. <a href="https://dora.inclusion.gouv.fr" title="Dora">le site Nova</a></p>'
        "<p>Ticket {{ticket.Dora_id}} {% if Dora %}Nova{% endif %} {{dc.dora}}</p>"
    )
    assert "2" not in after
    assert result["markup_hits"] == {1: 3, 2: 1}


def test_dod_16_markup_and_placeholders_are_replaced_only_on_explicit_request(store):
    api = FakeZendesk([macro(1, reply='<a href="/Dora">{{dc.Dora}} Dora</a>')])

    result = zm.replace(api, "Dora", "Nova", include_markup=True)

    after = store.json(f"changesets/{result['id']}/after.json.gz")
    assert reply_of(after["1"]) == '<a href="/Nova">{{dc.Nova}} Nova</a>'
    assert result["params"]["include_markup"] is True
    assert result["markup_hits"] == {}


def test_dod_17_a_changeset_targets_macros_or_articles_never_both(store):
    api = FakeZendesk([macro(1)], articles=[article(1)])
    macros_id = planned(api)
    articles_id = cs.replace(api, "Dora", "Nova", label="articles")["id"]

    cs.apply(api, macros_id)
    assert "Dora" in api.articles[1].body
    assert "Nova" in reply_of(cs.content(api.macros[1]))

    cs.apply(api, articles_id)
    assert "Nova" in api.articles[1].body
    assert api.macros[1].updated_at == "t0+1"
    assert {m["id"]: m["kind"] for m in cs.list_changesets()} == {macros_id: "macros", articles_id: "articles"}
    assert "Porte sur : macros" in store.files[f"changesets/{macros_id}/diff.md"].decode()


def test_dod_17_changesets_planned_before_macros_existed_are_articles(store):
    store.files["changesets/2026-09-01-000000-ancien/manifest.json"] = (
        b'{"id": "2026-09-01-000000-ancien", "status": "planned", "articles": []}'
    )
    assert cs.show("2026-09-01-000000-ancien")["kind"] == "articles"
    assert [m["kind"] for m in cs.list_changesets()] == ["articles"]


def test_dod_18_export_macros_dumps_raw_payloads_gzipped_with_a_link(store):
    api = FakeZendesk([macro(1), macro(2)])
    for m in api.macros.values():
        m.raw = {"id": m.id, "actions": m.actions, "extra": True}

    result = zm.export(api)

    assert result == {
        "path": "exports/2026-10-02T11-05-macros.json.gz",
        "count": 2,
        "url": "https://s3.example/exports/2026-10-02T11-05-macros.json.gz",
    }
    assert store.json(result["path"]) == [m.raw for m in api.macros.values()]


def test_dod_19_replace_tag_swaps_whole_tags_without_duplicates(store):
    api = FakeZendesk([
        macro(1, actions=[{"field": "current_tags", "value": "nia-ntt ntt relance relance pdi"}]),
        macro(2, actions=[{"field": "set_tags", "value": "ntt pdi"}, {"field": "remove_tags", "value": "ntt"}]),
        macro(3, actions=[{"field": "current_tags", "value": "nia-ntt"}, {"field": "subject", "value": "ntt"}]),
    ])

    result = zm.replace_tag(api, "ntt", "pdi")

    after = store.json(f"changesets/{result['id']}/after.json.gz")
    assert list(after) == ["1", "2"]
    assert after["1"]["actions"] == [{"field": "current_tags", "value": "nia-ntt pdi relance relance"}]
    assert after["2"]["actions"] == [{"field": "set_tags", "value": "pdi"}, {"field": "remove_tags", "value": "pdi"}]
    assert result["params"] == {"tag": "ntt", "replacement": "pdi"}


@pytest.mark.parametrize("old, new", [("ntt", "deux mots"), ("deux mots", "ntt"), ("", "pdi"), ("ntt", "")])
def test_dod_19_tag_with_a_space_or_empty_is_refused(store, old, new):
    with pytest.raises(ValueError, match="étiquette"):
        zm.replace_tag(FakeZendesk([macro(1)]), old, new)
    assert store.files == {}


@pytest.mark.parametrize(
    "reply, expected",
    [
        ("<p>Le Pass&nbsp;IAE est valable.</p>", "<p>Le pass IAE est valable.</p>"),
        ("<p>Le Pass\xa0IAE est valable.</p>", "<p>Le pass IAE est valable.</p>"),
        ("<p>Le Pass&#160;IAE&nbsp;: valable.</p>", "<p>Le pass IAE&nbsp;: valable.</p>"),
    ],
    ids=["nbsp entity", "nbsp character", "unrelated nbsp kept"],
)
def test_dod_20_text_is_searched_as_displayed(store, reply, expected):
    result = zm.replace(FakeZendesk([macro(1, reply=reply)]), "Pass IAE", "pass IAE")
    assert reply_of(store.json(f"changesets/{result['id']}/after.json.gz")["1"]) == expected


def test_dod_20_encoded_quotes_and_apostrophes_match_typed_ones(store):
    reply = "<p>Cliquez sur &quot;Mon espace&quot; puis l&#39;onglet.</p>"
    api = FakeZendesk([macro(1, reply=reply)])
    first = zm.replace(api, '"Mon espace"', "« Mon espace »")
    assert reply_of(store.json(f"changesets/{first['id']}/after.json.gz")["1"]) == (
        "<p>Cliquez sur « Mon espace » puis l&#39;onglet.</p>"
    )
    store.files.clear()
    second = zm.replace(api, "l'onglet", "l’onglet")
    assert reply_of(store.json(f"changesets/{second['id']}/after.json.gz")["1"]) == (
        "<p>Cliquez sur &quot;Mon espace&quot; puis l’onglet.</p>"
    )


@pytest.mark.external
def test_sandbox_roundtrip(store):
    """Plan → apply → revert on a throwaway inactive macro in production Zendesk (S3 in memory)."""
    api = get_zendesk()
    reply = "<p>Le Pass&nbsp;IAE de Dora.</p><p>{{ticket.id}}</p>"
    created = api.create_macro("[test changeset — à supprimer]", [{"field": "comment_value_html", "value": reply}])
    try:
        before = cs.content(api.get_macro(created.id))
        result = zm.replace(api, "Pass IAE de Dora", "pass IAE de Nova", macros=[api.get_macro(created.id)])
        assert cs.apply(api, result["id"])["written"] == 1
        assert "Nova" in reply_of(cs.content(api.get_macro(created.id)))
        assert cs.revert(api, result["id"])["written"] == 1
        assert cs.editable(cs.content(api.get_macro(created.id))) == cs.editable(before)
    finally:
        api._request("DELETE", f"macros/{created.id}.json")
