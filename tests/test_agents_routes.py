import pytest
from sqlalchemy import select

from lib import agent_delivery
from web.db import get_db
from web.models import Agent, AgentDelivery, AgentRun

pytestmark = [pytest.mark.integration, pytest.mark.usefixtures("_db")]

OWNER = "owner@example.org"
ADMIN = "admin@example.org"
SAME_ORIGIN = {"Sec-Fetch-Site": "same-origin"}


@pytest.fixture
def post(mocker):
    mocker.patch("lib.agent_delivery.config.AGENT_DESTINATION_TARGETS", {"produit.signal_faible": "C0SLACK"})
    mocker.patch("lib.agent_delivery.config.AGENT_SLACK_BOT_TOKEN", "agent-bot-token")
    mocker.patch("web.routes.agents.ADMIN_USERS", [ADMIN])
    return mocker.patch("lib.agent_delivery.slack.post_message", return_value=True)


def make_delivery(status="pending_review", mode="conversational") -> int:
    """An active agent owned by OWNER, one collected run, and one delivery of that run."""
    config = {
        "format": "pdi.agent/1",
        "slug": "veille-test",
        "title": "Veille de test",
        "mission": "Signaler les avis utiles à l'équipe.",
        "destinations": [{"id": "produit.signal_faible", "mode": mode}],
        "schedule": {"weekdays": ["monday"]},
    }
    with get_db() as session:
        agent = Agent(
            slug="veille-test",
            config=config,
            system_prompt="Consigne.",
            pipeline_id="p",
            version=1,
            status="active",
            owner_email=OWNER,
            changeset_id="c",
        )
        session.add(agent)
        session.flush()
        session.add(AgentRun(id="run-1", agent_id=agent.id, pipeline_id="p", status="collected"))
        session.flush()
        delivery = AgentDelivery(
            run_id="run-1",
            rank=0,
            destination="produit.signal_faible",
            mode=mode,
            status=status,
            title="Avis <b>du 3 novembre</b>",
            text="Effet non mesurable.",
            subagent_steps=[{"type": "classifier", "model": "clef:27b", "probability": 0.8231, "threshold": 0.6}],
        )
        session.add(delivery)
        session.flush()
        return delivery.id


def delivery(delivery_id: int) -> dict:
    with get_db() as session:
        return agent_delivery.as_dict(session.scalar(select(AgentDelivery).where(AgentDelivery.id == delivery_id)))


def decide(client, delivery_id: int, decision: str, user: str = OWNER, headers: dict = SAME_ORIGIN):
    return client.post(
        f"/api/agents/deliveries/{delivery_id}/{decision}", headers={"X-Forwarded-Email": user, **headers}
    )


def test_agents_page_lists_each_agent_and_the_review_queue(client, post):
    make_delivery()
    html = client.get("/agents", headers={"X-Forwarded-Email": OWNER}).text
    assert "veille-test" in html
    assert "chaque monday" in html
    assert "conversational" in html
    assert "collected" in html
    assert "À relire (1)" in html
    assert "Avis &lt;b&gt;du 3 novembre&lt;/b&gt;" in html
    assert "clef:27b : 0.82 (seuil 0.6)" in html
    assert 'data-decision="approve"' in html


def test_the_queue_shows_no_button_to_someone_who_may_not_decide(client, post):
    make_delivery()
    html = client.get("/agents", headers={"X-Forwarded-Email": "other@example.org"}).text
    assert "À relire (1)" in html
    assert 'data-decision="approve"' not in html


def test_agent_page_shows_configuration_destinations_runs_and_deliveries(client, post):
    make_delivery()
    html = client.get("/agents/veille-test", headers={"X-Forwarded-Email": ADMIN}).text
    assert "Signaler les avis utiles" in html
    assert "destination produit.signal_faible en mode conversational" in html
    assert "configurée" in html
    assert "run-1" in html
    assert 'data-decision="reject"' in html


@pytest.mark.parametrize(("slug", "status"), [("inconnu", 404), ("../x", 404), ("A", 422)])
def test_unknown_agent_page(client, slug, status):
    assert client.get(f"/agents/{slug}").status_code == status


@pytest.mark.parametrize("user", [OWNER, ADMIN])
def test_approving_sends_once_and_records_the_approver(client, post, user):
    delivery_id = make_delivery()
    response = decide(client, delivery_id, "approve", user)
    assert response.json() == {"id": delivery_id, "status": "sent", "approved_by": user}
    assert delivery(delivery_id)["approved_by"] == user
    post.assert_called_once_with(
        "agent-bot-token", "C0SLACK", "*Avis &lt;b&gt;du 3 novembre&lt;/b&gt;*\n\nEffet non mesurable."
    )


@pytest.mark.parametrize(
    ("first", "second"), [("approve", "approve"), ("reject", "approve"), ("approve", "reject"), ("reject", "reject")]
)
def test_a_delivery_already_taken_is_not_decided_twice(client, post, first, second):
    delivery_id = make_delivery()
    assert decide(client, delivery_id, first).status_code == 200
    response = decide(client, delivery_id, second)
    assert (response.status_code, response.json()) == (409, {"error": "envoi déjà décidé"})
    assert post.call_count == (first == "approve")


def test_rejecting_writes_nothing_and_records_who(client, post):
    delivery_id = make_delivery()
    assert decide(client, delivery_id, "reject").json() == {"id": delivery_id, "status": "rejected"}
    row = delivery(delivery_id)
    assert (row["status"], row["error"], row["approved_by"]) == ("rejected", f"refusé à la relecture par {OWNER}", None)
    post.assert_not_called()


@pytest.mark.parametrize("decision", ["approve", "reject"])
def test_only_the_owner_or_an_admin_decides(client, post, decision):
    delivery_id = make_delivery()
    response = decide(client, delivery_id, decision, "other@example.org")
    assert response.status_code == 403
    assert delivery(delivery_id)["status"] == "pending_review"
    post.assert_not_called()


@pytest.mark.parametrize(
    ("headers", "status"),
    [
        ({}, 403),
        ({"Sec-Fetch-Site": "cross-site"}, 403),
        ({"Sec-Fetch-Site": "same-site"}, 403),
        ({"Origin": "https://evil.example"}, 403),
        ({"Origin": "http://testserver"}, 200),
        ({"Sec-Fetch-Site": "same-origin"}, 200),
    ],
)
def test_a_decision_must_come_from_the_page_itself(client, post, headers, status):
    delivery_id = make_delivery()
    assert decide(client, delivery_id, "approve", headers=headers).status_code == status
    assert post.call_count == (status == 200)


@pytest.mark.parametrize("decision", ["approve", "reject"])
@pytest.mark.parametrize(("status", "mode"), [("recorded", "background"), ("sent", "conversational")])
def test_a_delivery_not_awaiting_review_is_not_decided(client, post, status, mode, decision):
    delivery_id = make_delivery(status, mode)
    assert decide(client, delivery_id, decision).status_code == 409
    assert delivery(delivery_id)["status"] == status
    post.assert_not_called()


@pytest.mark.parametrize(
    ("status", "mode", "error"),
    [
        ("recorded", "background", "cet envoi n'attend pas de relecture"),
        ("sent", "conversational", "envoi déjà décidé"),
    ],
)
@pytest.mark.parametrize("decision", ["approve", "reject"])
def test_a_refused_decision_answers_a_fixed_message_never_the_exception(client, post, status, mode, error, decision):
    response = decide(client, make_delivery(status, mode), decision)
    assert response.json() == {"error": error}
    assert "attendu" not in response.text


@pytest.mark.parametrize("decision", ["approve", "reject"])
def test_a_delivery_gone_after_the_permission_check_is_not_found(client, post, mocker, decision):
    delivery_id = make_delivery()
    mocker.patch("web.routes.agents.reviewed", return_value=None)
    response = decide(client, delivery_id + 1, decision)
    assert (response.status_code, response.json()) == (404, {"error": "envoi introuvable"})


@pytest.mark.parametrize("decision", ["approve", "reject"])
def test_deciding_on_an_unknown_delivery(client, post, decision):
    assert decide(client, 999999, decision).status_code == 404
