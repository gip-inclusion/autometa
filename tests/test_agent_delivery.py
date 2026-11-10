import json
import logging

import httpx
import pytest
from sqlalchemy import func, select

from lib import agent_config, agent_delivery, agents
from web.db import get_db
from web.db import test_transaction as _test_tx
from web.models import Agent, AgentDelivery, AgentFileVersion, AgentProposal, AgentRun

pytestmark = [pytest.mark.integration, pytest.mark.usefixtures("_db")]

SLUG = "signaux-faibles-mep"
RUN_ID = "11111111-1111-1111-1111-111111111111"
TARGETS = {"produit.signal_faible": "C0SLACK", "produit.opportunite": "db-notion"}


class Rows:
    """What the agents' tables hold, read back as the code records it."""

    def deliveries(self) -> list[dict]:
        with get_db() as session:
            rows = session.scalars(select(AgentDelivery).order_by(AgentDelivery.id)).all()
            return [agent_delivery.as_dict(r) for r in rows]

    def delivery(self, rank=0, run_id=RUN_ID) -> dict:
        return next(d for d in self.deliveries() if d["run_id"] == run_id and d["rank"] == rank)

    def run(self, run_id=RUN_ID) -> AgentRun:
        with get_db() as session:
            return session.get(AgentRun, run_id)

    def count(self, model=AgentDelivery) -> int:
        with get_db() as session:
            return session.scalar(select(func.count()).select_from(model))

    def size(self) -> int:
        """Everything the agents' tables hold, in rows."""
        return sum(self.count(m) for m in (Agent, AgentProposal, AgentRun, AgentDelivery, AgentFileVersion))

    def agent(self, slug: str) -> dict | None:
        with get_db() as session:
            agent = session.scalar(select(Agent).where(Agent.slug == slug))
            return agent and {c.name: getattr(agent, c.name) for c in Agent.__table__.columns}

    def launched(self) -> list[str]:
        with get_db() as session:
            return list(session.scalars(select(AgentRun.id).where(AgentRun.status == "launched")))


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
    mocker.patch("lib.agent_delivery.config.AGENT_DESTINATION_TARGETS", TARGETS)
    mocker.patch("lib.agent_delivery.config.AGENT_SLACK_BOT_TOKEN", "agent-bot-token")
    with _test_tx():
        yield Rows()


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
        "title": "Signaux faibles des mises en production",
        "mission": "Signaler à l'équipe produit les MEP dont l'effet n'est pas mesurable.",
        "destinations": [{"id": d, "mode": m} for d, m in contacts],
    }


def make_envoi(destination="produit.signal_faible", **extra):
    return {"destination": destination, "title": "MEP du 3 novembre", "text": "Effet non mesurable.", **extra}


def registered(doc: dict, run_id: str = RUN_ID) -> None:
    """The agent of doc, active, with a launched run of its job, as execute leaves them."""
    with get_db() as session:
        agent = session.scalar(select(Agent).where(Agent.slug == doc["slug"]))
        if agent is None:
            agent = Agent(
                slug=doc["slug"],
                config=doc,
                system_prompt="Consigne.",
                pipeline_id="p",
                version=1,
                status="active",
                owner_email="lj@example.org",
                changeset_id="c",
                cursors={},
            )
            session.add(agent)
            session.flush()
        agent.config = doc
        if session.get(AgentRun, run_id) is None:
            session.add(AgentRun(id=run_id, agent_id=agent.id, pipeline_id="p", status="launched"))


def deliver(mocker, doc: dict, deliveries: object, run_id: str = RUN_ID, chain=None, files=None) -> list[dict]:
    """A completed run of the agent's job handing back deliveries, delivered as the skill or the cron would."""
    registered(doc, run_id)
    output = {"deliveries": deliveries, **({"files": files} if files is not None else {})}
    mocker.patch("lib.agents.jobs.get_run", return_value={"status": "completed"})
    mocker.patch("lib.agents.jobs.get_run_output", return_value=json.dumps(output))
    if chain:
        mocker.patch("lib.agents.agent_subagents.run_chain", lambda subagents, delivery: chain(delivery))
    return agents.deliver_run(doc["slug"], run_id)


def open_real_mode(mocker):
    destinations = agent_config.known_destinations()
    for destination in destinations.values():
        destination["autonomous_allowed"] = [SLUG]
    mocker.patch("lib.agent_config.known_destinations", return_value=destinations)


@pytest.mark.parametrize(
    ("deliveries", "message"),
    [
        ([make_envoi(), make_envoi("bizdev.marche")], "'bizdev.marche' n'est ni une destination"),
        ([make_envoi("#general")], "'#general' n'est ni une destination"),
        ([make_envoi(channel="C0AUTRE")], "attendu destination, title, text"),
        ([make_envoi(title=" ")], "non vides"),
        ([make_envoi(key="../x")], "key en minuscules"),
        ("pas une liste", "attendu une liste"),
    ],
)
def test_dod_3_production_outside_the_list_refuses_the_whole_run(store, post, mocker, deliveries, message):
    open_real_mode(mocker)
    with pytest.raises(ValueError, match=message):
        deliver(mocker, make_agent(("produit.signal_faible", "autonomous")), deliveries)
    assert store.count() == 0
    assert store.run().status == "refused"
    post.assert_not_called()


def test_dod_3_invalid_agent_configuration_is_refused(store, post, mocker):
    with pytest.raises(ValueError, match="configuration d'agent refusée"):
        deliver(mocker, make_agent(("#general", "autonomous")), [make_envoi("#general")])
    assert store.count() == 0


def test_dod_4_background_mode_records_and_writes_nothing(store, post, fake_notion, mocker):
    agent = make_agent(("produit.signal_faible", "background"), ("produit.opportunite", "background"))
    summary = deliver(mocker, agent, [make_envoi(), make_envoi("produit.opportunite")])
    assert [s["status"] for s in summary] == ["recorded", "recorded"]
    assert store.delivery()["text"] == "Effet non mesurable."
    post.assert_not_called()
    assert fake_notion.calls == []


def test_dod_5_review_mode_writes_once_and_only_after_approval(store, post, mocker):
    deliver(mocker, make_agent(("produit.signal_faible", "conversational")), [make_envoi()])
    post.assert_not_called()
    delivery_id = store.delivery()["id"]
    assert store.delivery()["status"] == "pending_review"

    assert agent_delivery.approve(delivery_id, "lj@example.org") == "sent"
    post.assert_called_once_with("agent-bot-token", "C0SLACK", "*MEP du 3 novembre*\n\nEffet non mesurable.")
    assert store.delivery()["approved_by"] == "lj@example.org"

    with pytest.raises(ValueError, match="est sent, attendu pending_review"):
        agent_delivery.approve(delivery_id, "lj@example.org")
    post.assert_called_once()


@pytest.mark.parametrize("delivery_id", ["999999", "../x", "-1"])
def test_dod_5_showing_an_unknown_production_is_refused(store, post, mocker, delivery_id):
    deliver(mocker, make_agent(("produit.signal_faible", "conversational")), [make_envoi()])
    with get_db() as session:
        agent_id = session.scalar(select(Agent.id))
        with pytest.raises(ValueError, match="introuvable"):
            agent_delivery.show(session, agent_id, delivery_id)


def test_dod_5_background_production_cannot_be_approved(store, post, mocker):
    deliver(mocker, make_agent(("produit.signal_faible", "background")), [make_envoi()])
    with pytest.raises(ValueError, match="est recorded"):
        agent_delivery.approve(store.delivery()["id"], "lj@example.org")
    post.assert_not_called()


def test_dod_6_autonomous_mode_posts_to_slack_with_control_sequences_escaped(store, post, mocker):
    open_real_mode(mocker)
    delivery = make_envoi(title="<!channel> MEP", text="voir <https://x.example|ici> & co")
    summary = deliver(mocker, make_agent(("produit.signal_faible", "autonomous")), [delivery])
    assert summary == [
        {
            "id": store.delivery()["id"],
            "destination": "produit.signal_faible",
            "mode": "autonomous",
            "status": "sent",
            "calls": 0,
        }
    ]
    text = post.call_args.args[2]
    assert "<" not in text
    assert text == "*&lt;!channel&gt; MEP*\n\nvoir &lt;https://x.example|ici&gt; &amp; co"


def test_dod_6_autonomous_mode_creates_a_notion_page_in_the_database(store, fake_notion, mocker):
    open_real_mode(mocker)
    deliver(mocker, make_agent(("produit.opportunite", "autonomous")), [make_envoi("produit.opportunite")])
    assert fake_notion.writes() == [("POST", "pages"), ("PATCH", "blocks/page-1/children")]
    _, _, payload = fake_notion.calls[1]
    assert payload == {
        "parent": {"database_id": "db-notion"},
        "properties": {"Nom": {"title": [{"text": {"content": "MEP du 3 novembre"}}]}},
    }
    assert store.delivery()["notion_page_url"] == "https://notion.so/page-1"


@pytest.mark.parametrize(
    ("failure", "error"),
    [
        ({"target": {}}, "sans identifiant dans AGENT_DESTINATION_TARGETS"),
        ({"slack_ok": False}, "Slack a refusé le message"),
        ({"slack_raises": httpx.ConnectError("coupé")}, "coupé"),
        ({"slack_raises": json.JSONDecodeError("pas du JSON", "<html>", 0)}, "pas du JSON"),
    ],
)
def test_dod_6_failed_write_is_retried_then_recorded_as_failed_and_can_be_approved_again(
    store, post, mocker, failure, error
):
    """Review 2.4: a Slack answer that is not JSON used to leave the delivery pending_send for ever."""
    open_real_mode(mocker)
    if "target" in failure:
        mocker.patch("lib.agent_delivery.config.AGENT_DESTINATION_TARGETS", failure["target"])
    post.return_value = failure.get("slack_ok", True)
    post.side_effect = failure.get("slack_raises")
    summary = deliver(mocker, make_agent(("produit.signal_faible", "autonomous")), [make_envoi()])
    assert summary[0]["status"] == "pending_send"
    assert error in store.delivery()["error"]
    for _ in range(agent_delivery.SEND_ATTEMPTS_MAX - 1):
        agent_delivery.send_pending()
    assert store.delivery()["status"] == "failed"
    assert store.delivery()["attempts"] == agent_delivery.SEND_ATTEMPTS_MAX

    mocker.patch("lib.agent_delivery.config.AGENT_DESTINATION_TARGETS", TARGETS)
    post.return_value, post.side_effect = True, None
    assert agent_delivery.approve(store.delivery()["id"], "lj@example.org") == "sent"


@pytest.mark.parametrize("mode", ["autonomous", "conversational"])
def test_dod_10_slack_writes_need_the_agents_bot_and_never_fall_back_to_the_alerts_bot(store, post, mocker, mode):
    open_real_mode(mocker)
    mocker.patch("lib.agent_delivery.config.AGENT_SLACK_BOT_TOKEN", "")
    mocker.patch("lib.agent_delivery.config.SLACK_BOT_TOKEN", "alerts-bot-token")
    summary = deliver(mocker, make_agent(("produit.signal_faible", mode)), [make_envoi()])
    if mode == "conversational":
        assert summary[0]["status"] == "pending_review"
        agent_delivery.approve(store.delivery()["id"], "lj@example.org")
    assert store.delivery()["status"] == "pending_send"
    assert "AGENT_SLACK_BOT_TOKEN absent" in store.delivery()["error"]
    post.assert_not_called()


def test_dod_7_same_key_updates_the_notion_page_instead_of_creating_another(store, fake_notion, mocker):
    open_real_mode(mocker)
    agent = make_agent(("produit.opportunite", "autonomous"))
    deliver(mocker, agent, [make_envoi("produit.opportunite", key="mep-2026-11")])
    fake_notion.calls.clear()
    second_run = "22222222-2222-2222-2222-222222222222"
    deliver(mocker, agent, [make_envoi("produit.opportunite", key="mep-2026-11", text="Mis à jour.")], second_run)
    assert fake_notion.writes() == [
        ("PATCH", "pages/page-1"),
        ("DELETE", "blocks/b1"),
        ("PATCH", "blocks/page-1/children"),
    ]
    assert store.delivery(run_id=second_run)["notion_page_url"] == "https://notion.so/page-1"


def test_dod_7_a_page_whose_content_failed_is_replaced_not_created_again(store, fake_notion, mocker):
    """Review 2.4: the page id is kept as soon as the page exists, so the retry does not create a second one."""
    open_real_mode(mocker)
    append = mocker.patch("lib.agent_delivery.notion.append_markdown", side_effect=httpx.ConnectError("coupé"))
    deliver(mocker, make_agent(("produit.opportunite", "autonomous")), [make_envoi("produit.opportunite")])
    assert store.delivery()["status"] == "pending_send"
    append.side_effect = None
    fake_notion.calls.clear()
    agent_delivery.send_pending()
    assert store.delivery()["status"] == "sent"
    assert ("POST", "pages") not in fake_notion.writes()
    assert ("PATCH", "pages/page-1") in fake_notion.writes()


def test_dod_8_delivering_the_same_run_twice_writes_nothing_more(store, post, mocker):
    open_real_mode(mocker)
    agent = make_agent(("produit.signal_faible", "autonomous"))
    first = deliver(mocker, agent, [make_envoi()])
    second = deliver(mocker, agent, [make_envoi()])
    assert first == second
    post.assert_called_once()


def test_dod_8_a_delivery_is_claimed_once(store, post, mocker):
    """Review 1.1: the claim is a conditional update; a second sender finds nothing to take."""
    deliver(mocker, make_agent(("produit.signal_faible", "conversational")), [make_envoi()])
    delivery_id = store.delivery()["id"]
    with get_db() as session:
        session.get(AgentDelivery, delivery_id).status = "pending_send"
    assert agent_delivery.claim(delivery_id).status == "sending"
    assert agent_delivery.claim(delivery_id) is None
    assert agent_delivery.send(delivery_id) == "sending"
    post.assert_not_called()


def test_dod_9_logs_name_the_production_never_its_content(store, post, caplog, mocker):
    caplog.set_level(logging.INFO, logger="lib.agent_delivery")
    deliver(mocker, make_agent(("produit.signal_faible", "conversational")), [make_envoi()])
    agent_delivery.approve(store.delivery()["id"], "lj@example.org")
    logged = caplog.text
    assert SLUG in logged
    assert "produit.signal_faible" in logged
    assert "conversational" in logged
    assert "pending_review" in logged
    assert "sent" in logged
    assert "MEP du 3 novembre" not in logged
    assert "Effet non mesurable" not in logged


@pytest.mark.parametrize(
    ("deliveries", "message"),
    [
        ([make_envoi()] * (agent_delivery.DELIVERIES_MAX + 1), f"{agent_delivery.DELIVERIES_MAX} au plus par run"),
        ([make_envoi(title="x" * (agent_delivery.TITLE_MAX + 1))], "title de 300 caractères au plus"),
        ([make_envoi(text="x" * (agent_delivery.TEXT_MAX + 1))], "text de 20000 au plus"),
    ],
)
def test_review_2_5_a_run_beyond_its_caps_is_refused(store, post, mocker, deliveries, message):
    with pytest.raises(ValueError, match=message):
        deliver(mocker, make_agent(("produit.signal_faible", "background")), deliveries)
    assert store.count() == 0
