import json
import logging

import httpx
import pytest

from lib import agent_config, agent_delivery

SLUG = "signaux-faibles-mep"
RUN_ID = "11111111-1111-1111-1111-111111111111"
TARGETS = {"produit.signal_faible": "C0SLACK", "produit.opportunite": "db-notion"}


class FakeStore:
    def __init__(self):
        self.files: dict[str, bytes] = {}

    def upload(self, path, content, content_type=None):
        self.files[path] = content
        return True

    def download(self, path):
        return self.files.get(path)

    def head(self, path):
        return {"exists": path in self.files}

    def list_directories(self, prefix=""):
        return sorted({path.split("/")[0] for path in self.files})

    def json(self, path):
        return json.loads(self.files[path])


class FakeNotion:
    """Records every Notion API call; one database whose title property is « Nom », one page holding a nested block."""

    def __init__(self):
        self.calls = []

    def __call__(self, method, endpoint, payload=None):
        self.calls.append((method, endpoint, payload))
        if endpoint.startswith("databases/"):
            return {"properties": {"Statut": {"type": "select"}, "Nom": {"type": "title"}}}
        if endpoint.startswith("blocks/") and method == "GET":
            parent = {"type": "page_id", "page_id": "page-1"}
            nested = {"id": "b2", "parent": {"type": "block_id", "block_id": "b1"}, "has_children": False}
            return {"results": [{"id": "b1", "parent": parent, "has_children": False}, nested], "has_more": False}
        return {"id": "page-1", "url": "https://notion.so/page-1"}

    def writes(self):
        return [(m, e) for m, e, _ in self.calls if m != "GET"]


@pytest.fixture
def store(mocker):
    fake = FakeStore()
    mocker.patch("lib.agent_delivery.s3.agents", fake)
    mocker.patch("lib.agent_delivery.config.AGENT_DESTINATION_TARGETS", TARGETS)
    mocker.patch("lib.agent_delivery.config.AGENT_SLACK_BOT_TOKEN", "agent-bot-token")
    return fake


@pytest.fixture
def post(mocker):
    return mocker.patch("lib.agent_delivery.slack.post_message", return_value=True)


@pytest.fixture
def fake_notion(mocker):
    fake = FakeNotion()
    mocker.patch("lib.notion.notion_request", fake)
    return fake


def make_agent(*contacts):
    return {
        "format": "pdi.agent/1",
        "slug": SLUG,
        "titre": "Signaux faibles des mises en production",
        "mission": "Signaler à l'équipe produit les MEP dont l'effet n'est pas mesurable.",
        "points_de_contact": [{"id": d, "mode": m} for d, m in contacts],
    }


def make_envoi(destination="produit.signal_faible", **extra):
    return {"destination": destination, "titre": "MEP du 3 novembre", "texte": "Effet non mesurable.", **extra}


def open_real_mode(mocker):
    destinations = agent_config.destinations()
    for destination in destinations.values():
        destination["reel_autorise"] = [SLUG]
    mocker.patch("lib.agent_config.destinations", return_value=destinations)


@pytest.mark.parametrize(
    ("envois", "message"),
    [
        ([make_envoi(), make_envoi("bizdev.marche")], "'bizdev.marche' n'est pas un point de contact"),
        ([make_envoi("#general")], "'#general' n'est pas un point de contact"),
        ([make_envoi(canal="C0AUTRE")], "attendu destination, titre, texte"),
        ([make_envoi(titre=" ")], "non vides"),
        ([make_envoi(cle="../x")], "cle en minuscules"),
        ("pas une liste", "attendu une liste"),
    ],
)
def test_dod_3_production_outside_the_list_refuses_the_whole_run(store, post, mocker, envois, message):
    open_real_mode(mocker)
    with pytest.raises(ValueError, match=message):
        agent_delivery.deliver(make_agent(("produit.signal_faible", "reel")), RUN_ID, envois)
    assert store.files == {}
    post.assert_not_called()


def test_dod_3_invalid_agent_configuration_is_refused(store, post):
    with pytest.raises(ValueError, match="configuration d'agent refusée"):
        agent_delivery.deliver(make_agent(("#general", "reel")), RUN_ID, [make_envoi("#general")])
    assert store.files == {}


def test_dod_4_shadow_mode_records_and_writes_nothing(store, post, fake_notion):
    agent = make_agent(("produit.signal_faible", "ombre"), ("produit.opportunite", "ombre"))
    summary = agent_delivery.deliver(agent, RUN_ID, [make_envoi(), make_envoi("produit.opportunite")])
    assert [s["statut"] for s in summary] == ["ombre", "ombre"]
    assert store.json(f"{SLUG}/envois/{RUN_ID}-0.json")["texte"] == "Effet non mesurable."
    post.assert_not_called()
    assert fake_notion.calls == []


def test_dod_5_review_mode_writes_once_and_only_after_approval(store, post):
    agent_delivery.deliver(make_agent(("produit.signal_faible", "relecture")), RUN_ID, [make_envoi()])
    post.assert_not_called()
    envoi_id = f"{RUN_ID}-0"
    assert agent_delivery.show(SLUG, envoi_id)["statut"] == "a_relire"

    assert agent_delivery.approve(SLUG, envoi_id, "lj@example.org")["statut"] == "envoyee"
    post.assert_called_once_with("agent-bot-token", "C0SLACK", "*MEP du 3 novembre*\n\nEffet non mesurable.")
    assert store.json(f"{SLUG}/envois/{envoi_id}.json")["approuve_par"] == "lj@example.org"

    with pytest.raises(ValueError, match="est envoyee, attendu a_relire"):
        agent_delivery.approve(SLUG, envoi_id, "lj@example.org")
    post.assert_called_once()


@pytest.mark.parametrize(("slug", "envoi_id"), [(SLUG, f"{RUN_ID}-9"), ("../x", f"{RUN_ID}-0"), (SLUG, "../x")])
def test_dod_5_approving_an_unknown_production_is_refused(store, post, slug, envoi_id):
    with pytest.raises(ValueError, match="introuvable"):
        agent_delivery.approve(slug, envoi_id, "lj@example.org")
    post.assert_not_called()


def test_dod_5_shadow_production_cannot_be_approved(store, post):
    agent_delivery.deliver(make_agent(("produit.signal_faible", "ombre")), RUN_ID, [make_envoi()])
    with pytest.raises(ValueError, match="est ombre"):
        agent_delivery.approve(SLUG, f"{RUN_ID}-0", "lj@example.org")
    post.assert_not_called()


def test_dod_6_real_mode_posts_to_slack_with_control_sequences_escaped(store, post, mocker):
    open_real_mode(mocker)
    envoi = make_envoi(titre="<!channel> MEP", texte="voir <https://x.example|ici> & co")
    summary = agent_delivery.deliver(make_agent(("produit.signal_faible", "reel")), RUN_ID, [envoi])
    assert summary == [
        {"id": f"{RUN_ID}-0", "destination": "produit.signal_faible", "mode": "reel", "statut": "envoyee", "appels": 0}
    ]
    text = post.call_args.args[2]
    assert "<" not in text
    assert text == "*&lt;!channel&gt; MEP*\n\nvoir &lt;https://x.example|ici&gt; &amp; co"


def test_dod_6_real_mode_creates_a_notion_page_in_the_database(store, fake_notion, mocker):
    open_real_mode(mocker)
    agent_delivery.deliver(make_agent(("produit.opportunite", "reel")), RUN_ID, [make_envoi("produit.opportunite")])
    assert fake_notion.writes() == [("POST", "pages"), ("PATCH", "blocks/page-1/children")]
    _, _, payload = fake_notion.calls[1]
    assert payload == {
        "parent": {"database_id": "db-notion"},
        "properties": {"Nom": {"title": [{"text": {"content": "MEP du 3 novembre"}}]}},
    }
    assert store.json(f"{SLUG}/envois/{RUN_ID}-0.json")["page"]["url"] == "https://notion.so/page-1"


@pytest.mark.parametrize(
    ("failure", "error"),
    [
        ({"target": {}}, "sans identifiant dans AGENT_DESTINATION_TARGETS"),
        ({"slack_ok": False}, "Slack a refusé le message"),
        ({"slack_raises": httpx.ConnectError("coupé")}, "coupé"),
    ],
)
def test_dod_6_failed_write_is_recorded_and_can_be_retried(store, post, mocker, failure, error):
    open_real_mode(mocker)
    if "target" in failure:
        mocker.patch("lib.agent_delivery.config.AGENT_DESTINATION_TARGETS", failure["target"])
    post.return_value = failure.get("slack_ok", True)
    post.side_effect = failure.get("slack_raises")
    summary = agent_delivery.deliver(make_agent(("produit.signal_faible", "reel")), RUN_ID, [make_envoi()])
    assert summary[0]["statut"] == "echec"
    assert error in store.json(f"{SLUG}/envois/{RUN_ID}-0.json")["erreur"]

    mocker.patch("lib.agent_delivery.config.AGENT_DESTINATION_TARGETS", TARGETS)
    post.return_value, post.side_effect = True, None
    assert agent_delivery.approve(SLUG, f"{RUN_ID}-0", "lj@example.org")["statut"] == "envoyee"


@pytest.mark.parametrize("mode", ["reel", "relecture"])
def test_dod_10_slack_writes_need_the_agents_bot_and_never_fall_back_to_the_alerts_bot(store, post, mocker, mode):
    open_real_mode(mocker)
    mocker.patch("lib.agent_delivery.config.AGENT_SLACK_BOT_TOKEN", "")
    mocker.patch("lib.agent_delivery.config.SLACK_BOT_TOKEN", "alerts-bot-token")
    summary = agent_delivery.deliver(make_agent(("produit.signal_faible", mode)), RUN_ID, [make_envoi()])
    if mode == "relecture":
        assert summary[0]["statut"] == "a_relire"
        summary = [agent_delivery.approve(SLUG, f"{RUN_ID}-0", "lj@example.org")]
    assert summary[0]["statut"] == "echec"
    assert "AGENT_SLACK_BOT_TOKEN absent" in store.json(f"{SLUG}/envois/{RUN_ID}-0.json")["erreur"]
    post.assert_not_called()


def test_dod_7_same_key_updates_the_notion_page_instead_of_creating_another(store, fake_notion, mocker):
    open_real_mode(mocker)
    agent = make_agent(("produit.opportunite", "reel"))
    agent_delivery.deliver(agent, RUN_ID, [make_envoi("produit.opportunite", cle="mep-2026-11")])
    fake_notion.calls.clear()
    second_run = "22222222-2222-2222-2222-222222222222"
    agent_delivery.deliver(
        agent, second_run, [make_envoi("produit.opportunite", cle="mep-2026-11", texte="Mis à jour.")]
    )
    assert fake_notion.writes() == [
        ("PATCH", "pages/page-1"),
        ("DELETE", "blocks/b1"),
        ("PATCH", "blocks/page-1/children"),
    ]
    assert store.json(f"{SLUG}/pages/produit.opportunite/mep-2026-11.json") == {
        "id": "page-1",
        "url": "https://notion.so/page-1",
    }


def test_dod_8_delivering_the_same_run_twice_writes_nothing_more(store, post, mocker):
    open_real_mode(mocker)
    agent = make_agent(("produit.signal_faible", "reel"))
    first = agent_delivery.deliver(agent, RUN_ID, [make_envoi()])
    second = agent_delivery.deliver(agent, RUN_ID, [make_envoi()])
    assert first == second
    post.assert_called_once()


def test_dod_9_logs_name_the_production_never_its_content(store, post, caplog):
    caplog.set_level(logging.INFO, logger="lib.agent_delivery")
    agent_delivery.deliver(make_agent(("produit.signal_faible", "relecture")), RUN_ID, [make_envoi()])
    agent_delivery.approve(SLUG, f"{RUN_ID}-0", "lj@example.org")
    logged = caplog.text
    assert SLUG in logged
    assert "produit.signal_faible" in logged
    assert "relecture" in logged
    assert "a_relire" in logged
    assert "envoyee" in logged
    assert "MEP du 3 novembre" not in logged
    assert "Effet non mesurable" not in logged


def test_s3_failures_are_raised_not_mistaken_for_absence(store, mocker):
    mocker.patch.object(store, "head", return_value={"exists": None})
    with pytest.raises(RuntimeError, match="S3 read failed"):
        agent_delivery.show(SLUG, f"{RUN_ID}-0")
    mocker.patch.object(store, "upload", return_value=False)
    with pytest.raises(RuntimeError, match="S3 upload failed"):
        agent_delivery.write_json("x.json", {})
