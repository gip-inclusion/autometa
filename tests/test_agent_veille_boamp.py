import json
import re
from datetime import datetime, timezone
from urllib.parse import parse_qs, urlsplit

import httpx
import pytest

from lib import agent_config, agents
from skills.agents.scripts import agents as cli
from tests.test_agent_connectors import PUBLIC, addresses
from tests.test_agent_delivery import Rows
from tests.test_agents import PIPELINE_ID, RUN_ID, Conversation, labels_cloud, write_file
from web import config
from web.db import test_transaction as _test_tx

AGENTS_DIR = config.BASE_DIR / "agents"
CONFIG = (AGENTS_DIR / "veille-boamp.yaml").read_text()
CONSIGNE = (AGENTS_DIR / "veille-boamp.md").read_text()
REGLES = (AGENTS_DIR / "veille-boamp" / "regles.md").read_text()
BOAMP = "boamp-datadila.opendatasoft.com"
HEADER = "idweb;dateparution;objet;nomacheteur;code_departement;datelimitereponse;descripteur_libelle\r\n"
CSV = {
    "SERVICES": HEADER
    + "26-000001;2026-11-03;Logiciel de suivi des parcours des bénéficiaires du RSA;Département fictif;99;"
    "2026-12-04T12:00:00+00:00;Logiciel\r\n"
    + "26-000002;2026-11-04;Nettoyage des locaux;Commune fictive;98;2026-12-01T12:00:00+00:00;Nettoyage\r\n",
    "FOURNITURES": HEADER
    + "26-000003;2026-11-05;Accompagnement socio-professionnel des allocataires;Agglomération fictive;97;"
    "2026-12-10T12:00:00+00:00;Insertion\r\n",
}


def avis(idweb, objet, acheteur, departement, date, descripteurs):
    text = (
        f"Acheteur : {acheteur} ({departement})\nRéponse avant le {date}\nDescripteurs : {descripteurs}\n"
        f"https://www.boamp.fr/pages/avis/?q=idweb:{idweb}"
    )
    return {"destination": "bizdev.marche", "title": objet, "text": text}


# Why: a worker that read regles.md keeps three avis, including one that clef will judge off topic.
OUTPUT = {
    "deliveries": [
        avis(
            "26-000001",
            "Logiciel de suivi des parcours des bénéficiaires du RSA",
            "Département fictif",
            "99",
            "04/12/2026",
            "Logiciel",
        ),
        avis(
            "26-000004",
            "Plateforme d'information des usagers des transports",
            "Région fictive",
            "96",
            "06/12/2026",
            "Informatique",
        ),
        avis(
            "26-000003",
            "Accompagnement socio-professionnel des allocataires",
            "Agglomération fictive",
            "97",
            "10/12/2026",
            "Insertion",
        ),
    ],
    "files": [{"name": "regles.md", "content": REGLES + "- 2026-11-09 : ajout du terme « mission locale »."}],
}


class Boamp:
    """The public BOAMP export behind httpx's MockTransport: answers the CSV of the market type asked."""

    def __init__(self, mocker):
        self.requests = []
        transport = httpx.MockTransport(self.handle)
        mocker.patch("lib.agent_connectors.url.client", lambda: httpx.Client(transport=transport, timeout=30))
        mocker.patch("lib.agent_connectors.url.socket.getaddrinfo", side_effect=addresses(PUBLIC))

    def handle(self, request):
        self.requests.append(request)
        where = parse_qs(urlsplit(str(request.url)).query)["where"][0]
        kind = re.search(r'type_marche="(\w+)"', where).group(1)
        return httpx.Response(200, text=CSV[kind], headers={"content-type": "text/csv; charset=utf-8"})


@pytest.fixture
def store(_db, mocker):
    mocker.patch("lib.agent_delivery.config.AGENT_DESTINATION_TARGETS", {"bizdev.marche": "C0BIZDEV"})
    with _test_tx():
        yield Rows()


def registered(mocker) -> dict:
    conversation = Conversation(mocker)
    mocker.patch("lib.agents.jobs.create_pipeline", return_value={"id": PIPELINE_ID})
    proposal = agents.plan(CONFIG, CONSIGNE, {"regles.md": REGLES})
    conversation.user_replies()
    return agents.apply(proposal["id"])


def test_dod_1_boamp_agent_is_composed_of_generic_bricks_only():
    doc = agent_config.parse(CONFIG)
    assert agent_config.validate(doc) == []
    assert doc["destinations"] == [{"id": "bizdev.marche", "mode": "background", "grouping": "digest"}]
    assert agent_config.known_destinations()["bizdev.marche"]["channel"] == "slack"
    assert doc["schedule"] == {"weekdays": ["monday"]}
    assert {urlsplit(p["url"]).hostname for p in doc["preparations"]} == {BOAMP}
    assert [o["type"] for o in doc["subagents"]] == ["classifier", "classifier"]
    assert doc["files"] == ["regles.md"]
    assert agent_config.describe(doc)[1:3] == [
        "sous-agent 1 : classifier clef:27b, filtre « L'avis achète-t-il une prestation ou un outil au "
        "service de l'insertion professionnelle, de l'IAE, de l'accompagnement des bénéficiaires du RSA ou du "
        "retour à l'emploi ? » au seuil 0.7",
        "sous-agent 2 : classifier clef:27b, étiquettes outils-numeriques, prestations-insertion au seuil 0.5, "
        "sans rien écarter",
    ]


def test_dod_1_preparations_cover_seven_full_days_of_open_notices_without_gap():
    wheres = [parse_qs(urlsplit(p["url"]).query)["where"][0] for p in agent_config.parse(CONFIG)["preparations"]]
    assert all('nature="APPEL_OFFRE" and etat="INITIAL"' in w for w in wheres)
    windows = [re.findall(r"now\(days=(-\d)\)", w) for w in wheres]
    assert windows == [["-8", "-5"], ["-5", "-1"], ["-8", "-1"]]
    assert ['type_marche="SERVICES"' in w for w in wheres] == [True, True, False]


def test_dod_2_job_prompt_reads_its_input_and_rules_and_calls_no_api():
    hosts = {urlsplit(url).hostname for url in re.findall(r"https?://\S+", CONSIGNE)}
    assert hosts == {"www.boamp.fr"}
    assert "curl" not in CONSIGNE
    for rule in ("regles.md", "un envoi par avis retenu", '{"deliveries": []}', "idweb"):
        assert rule in CONSIGNE


def test_dod_2_rules_file_holds_terms_exclusions_and_both_headings():
    for part in ("insertion par l'activite economique", "nettoyage", "Outils numériques", "Prestations d'insertion"):
        assert part in REGLES


@pytest.mark.parametrize("text", [CONSIGNE, REGLES, json.dumps(OUTPUT, ensure_ascii=False)])
def test_dod_2_nothing_carries_a_long_dash(text):
    assert not re.search("[–—]", text)


@pytest.mark.integration
def test_dod_4_repository_agent_registers_with_its_rules_as_first_version(store, mocker):
    conversation = Conversation(mocker)
    create = mocker.patch("lib.agents.jobs.create_pipeline", return_value={"id": PIPELINE_ID})
    proposal = agents.plan(CONFIG, CONSIGNE, {"regles.md": REGLES})
    create.assert_not_called()
    assert proposal["system_prompt"].startswith(CONSIGNE)
    assert "destination : une de bizdev.marche, file:regles.md, aucune autre." in proposal["system_prompt"]
    assert proposal["review"][-2:] == [
        "cadence : chaque monday",
        f"valeur initiale de regles.md : {len(REGLES)} caractères, écrite à la création si le fichier est vide",
    ]
    conversation.user_replies()
    agents.apply(proposal["id"])
    create.assert_called_once_with("agent-veille-boamp", proposal["system_prompt"], {"output_format": "json"})
    assert agents.read_file("veille-boamp", "regles.md")["content"] == REGLES


@pytest.mark.integration
def test_dod_4_the_skill_proposes_the_repository_files_as_they_are(store, mocker, capsys):
    Conversation(mocker)
    folder = AGENTS_DIR / "veille-boamp"
    args = ["--config", str(AGENTS_DIR / "veille-boamp.yaml"), "--instructions", str(AGENTS_DIR / "veille-boamp.md")]
    assert cli.main(["propose", *args, "--file", str(folder / "regles.md")]) == 0
    assert json.loads(capsys.readouterr().out)["initial_files"] == {"regles.md": REGLES}


@pytest.mark.integration
@pytest.mark.parametrize(
    ("initial_files", "message"),
    [
        ({"notes.md": "x"}, "fichier initial notes.md : pas un fichier déclaré de l'agent, files : regles.md."),
        ({"regles.md": "x" * 100_001}, "fichier initial regles.md : 100001 caractères, 100000 au plus."),
    ],
)
@pytest.mark.integration
def test_an_initial_value_outside_the_declared_files_is_refused(store, mocker, initial_files, message):
    Conversation(mocker)
    with pytest.raises(ValueError, match=re.escape(message)):
        agents.plan(CONFIG, CONSIGNE, initial_files)


@pytest.mark.integration
def test_an_initial_value_never_overwrites_what_the_agent_wrote(store, mocker):
    registered(mocker)
    write_file("veille-boamp", "regles.md", "# Revu par l'agent")
    registered(mocker)
    assert [v["origin"][:15] for v in agents.file_history("veille-boamp", "regles.md")] == [
        "valeur initiale",
        "run r",
    ]


@pytest.mark.parametrize(("day", "due"), [("2026-11-09T07:00:00", True), ("2026-11-10T07:00:00", False)])
def test_dod_6_the_generic_cron_launches_it_on_mondays_only(mocker, day, due):
    mocker.patch("lib.agents.cron.utcnow", return_value=datetime.fromisoformat(day).replace(tzinfo=timezone.utc))
    assert agents.due(agent_config.parse(CONFIG)["schedule"]) is due


@pytest.mark.integration
def test_dod_5_a_simulated_run_judges_each_notice_then_sends_one_shadow_digest_by_heading(store, mocker):
    """BOAMP and Ollama are mocked at the HTTP level; Slack and Notion are never called."""
    registered(mocker)
    boamp = Boamp(mocker)
    publish = mocker.patch("lib.agents.job_inputs.publish_dataset", return_value={"url": "https://s3/entree.jsonl"})
    mocker.patch("lib.agents.jobs.trigger_run", return_value={"id": RUN_ID})
    mocker.patch("lib.agents.jobs.get_run", return_value={"pipeline_id": PIPELINE_ID, "status": "completed"})
    mocker.patch("lib.agents.jobs.get_run_output", return_value=json.dumps(OUTPUT))
    mocker.patch("lib.agent_subagents.config.OLLAMA_API_KEY", "ollama-key")
    verdicts = labels_cloud((0.92,), (0.81, 0.12), (0.18,), (0.95,), (0.07, 0.88))
    ollama = mocker.patch("lib.agent_subagents.httpx.post", side_effect=verdicts)
    slack = mocker.patch("lib.agent_delivery.slack.post_message")
    notion = mocker.patch("lib.agent_delivery.notion.create_page")

    agents.execute("veille-boamp")

    assert [r.headers["host"] for r in boamp.requests] == [BOAMP] * 3
    rows = publish.call_args.args[2]
    assert [(r[1], r[3]) for r in rows] == [
        ("url", CSV["SERVICES"]),
        ("url", CSV["SERVICES"]),
        ("url", CSV["FOURNITURES"]),
        ("file", REGLES),
    ]

    summary = agents.deliver_run("veille-boamp", RUN_ID)

    assert [(e["status"], e["calls"]) for e in summary] == [
        ("grouped", 2),
        ("discarded", 1),
        ("grouped", 2),
        ("recorded", 0),
    ]
    assert ollama.call_count == 5
    records = [store.delivery(i) for i in range(3)]
    assert [r["labels"] for r in records] == [["outils-numeriques"], [], ["prestations-insertion"]]
    assert records[0]["text"].endswith("idweb:26-000001\n\nÉtiquettes : outils-numeriques")
    assert records[1]["subagent_steps"][0]["probability"] == 0.18
    digest = store.delivery(None)
    assert digest["title"].endswith(" : retenus 2, écartés 1")
    assert digest["text"] == (
        "## outils-numeriques\n"
        "- Logiciel de suivi des parcours des bénéficiaires du RSA : https://www.boamp.fr/pages/avis/?q=idweb:26-000001\n\n"
        "## prestations-insertion\n"
        "- Accompagnement socio-professionnel des allocataires : https://www.boamp.fr/pages/avis/?q=idweb:26-000003\n\n"
        "## Fichiers réécrits par ce run, à relire\n"
        f"- regles.md : version 2, {len(OUTPUT['files'][0]['content'])} caractères (avant : {len(REGLES)}) ; "
        "comparer avec la commande diff du skill agents"
    )
    slack.assert_not_called()
    notion.assert_not_called()
    assert [v["version"] for v in agents.file_history("veille-boamp", "regles.md")] == [1, 2]
    assert agents.read_file("veille-boamp", "regles.md")["content"].endswith("« mission locale ».")
