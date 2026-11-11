"""Tests de la mention d'un job autometa-jobs (@nom) dans un message du chat."""

import httpx
import pytest

from lib import job_mentions
from web.db import get_db
from web.db import test_transaction as _test_tx
from web.models import Agent, AgentRun

PIPELINE_ID = "22222222-2222-2222-2222-222222222222"
RUN_OK = "11111111-1111-1111-1111-111111111111"
RUN_KO = "33333333-3333-3333-3333-333333333333"


def make_pipeline(name="veille-dora", system_prompt="Analyse les services Dora.", pipeline_id=PIPELINE_ID):
    return {"id": pipeline_id, "name": name, "system_prompt": system_prompt}


def make_run(run_id, status, created_at, pipeline_id=PIPELINE_ID):
    return {"id": run_id, "status": status, "created_at": created_at, "pipeline_id": pipeline_id}


def fake_jobs(mocker):
    """Service de jobs simulé : un pipeline, deux runs, une sortie."""
    jobs = mocker.patch("lib.job_mentions.jobs")
    jobs.list_pipelines.return_value = [make_pipeline()]
    jobs.list_runs.return_value = [
        make_run(RUN_OK, "completed", "2026-11-01T09:00:00"),
        make_run(RUN_KO, "failed", "2026-11-03T09:00:00"),
    ]
    jobs.get_run_output.return_value = "## Rapport\n42 services sans horaires."
    return jobs


@pytest.fixture
def orchestrator(mocker):
    """Service de jobs simulé, aucun pipeline n'étant celui d'un agent."""
    mocker.patch("lib.job_mentions.agent_slug", return_value=None)
    return fake_jobs(mocker)


@pytest.mark.parametrize(
    "text,expected",
    [
        ("relance @veille-dora stp", ["veille-dora"]),
        ("@veille-dora.", ["veille-dora"]),
        ("@a @b @a", ["a", "b"]),
        ("@dora-services-2026.06, et ensuite", ["dora-services-2026.06"]),
        ("écris à prenom.nom@inclusion.gouv.fr", []),
        ("aucune mention", []),
    ],
)
def test_dod_1_mentioned_names(text, expected):
    assert job_mentions.mentioned_names(text) == expected


def test_dod_1_context_carries_prompt_runs_and_last_output(orchestrator):
    context = job_mentions.build_context("que donne @veille-dora ?")

    assert "@veille-dora" in context
    assert PIPELINE_ID in context
    assert "Analyse les services Dora." in context
    assert context.index(RUN_KO) < context.index(RUN_OK)
    assert "42 services sans horaires." in context
    orchestrator.list_runs.assert_called_once_with(pipeline_id=PIPELINE_ID, limit=20)
    orchestrator.get_run_output.assert_called_once_with(RUN_OK)


def test_dod_2_context_is_bounded(orchestrator):
    names = [f"job-{i}" for i in range(6)]
    orchestrator.list_pipelines.return_value = [
        make_pipeline(name=n, system_prompt="consigne " * 5000, pipeline_id=f"{i}" * 8) for i, n in enumerate(names)
    ]
    orchestrator.list_runs.return_value = [
        make_run(f"run-{i}", "completed", f"2026-10-{i + 10}T09:00:00") for i in range(10)
    ]
    orchestrator.get_run_output.return_value = "x" * 500_000

    context = job_mentions.build_context(" ".join(f"@{n}" for n in names))

    assert len(context) < 20_000
    assert "[… tronqué]" in context
    assert [n for n in names if f"@{n}" in context] == names[:3]
    assert context.count("run-") == 3 * 3 + 3
    assert orchestrator.get_run_output.call_count == 3


@pytest.mark.parametrize("text", ["salut @inconnu", "pas de mention", "mail@exemple.fr"])
def test_dod_3_unknown_or_absent_mention_adds_nothing(orchestrator, text):
    assert job_mentions.build_context(text) == ""


def test_dod_3_no_mention_does_not_call_the_service(orchestrator):
    job_mentions.build_context("pas de mention")

    orchestrator.list_pipelines.assert_not_called()


@pytest.mark.parametrize("failure", [httpx.ConnectError("down"), ValueError("not JSON")])
def test_dod_3_service_down_adds_nothing(orchestrator, failure):
    orchestrator.list_pipelines.side_effect = failure

    assert job_mentions.build_context("@veille-dora") == ""


def test_dod_1_unavailable_output_is_reported(orchestrator):
    orchestrator.get_run_output.side_effect = httpx.ReadTimeout("slow")

    context = job_mentions.build_context("@veille-dora")

    assert "sortie indisponible" in context
    assert "Analyse les services Dora." in context


def test_dod_1_last_success_found_beyond_the_three_listed_runs(orchestrator):
    orchestrator.list_runs.return_value = [
        make_run(RUN_OK, "completed", "2026-10-01T09:00:00"),
        *(make_run(f"ko-{d}", "failed", f"2026-11-0{d}T09:00:00") for d in (1, 2, 3)),
    ]

    context = job_mentions.build_context("@veille-dora")

    assert "ko-3" in context
    assert f"- completed — 2026-10-01T09:00:00 — run {RUN_OK}" not in context
    assert f"Dernière sortie réussie (run {RUN_OK})" in context
    orchestrator.get_run_output.assert_called_once_with(RUN_OK)


def test_dod_1_no_completed_run(orchestrator):
    orchestrator.list_runs.return_value = [make_run(RUN_KO, "failed", "2026-11-03T09:00:00")]

    context = job_mentions.build_context("@veille-dora")

    assert "aucun run réussi" in context
    orchestrator.get_run_output.assert_not_called()


def test_dod_4_mention_never_launches_and_asks_for_explicit_yes(orchestrator):
    context = job_mentions.build_context("@veille-dora")

    orchestrator.trigger_run.assert_not_called()
    orchestrator.create_pipeline.assert_not_called()
    orchestrator.create_and_run.assert_not_called()
    assert "« oui » explicite" in context
    assert f"--relaunch {PIPELINE_ID}" in context


@pytest.mark.integration
@pytest.mark.usefixtures("_db")
@pytest.mark.parametrize("current", [True, False])
def test_agent_job_is_relaunched_through_the_agents_skill(mocker, current):
    orchestrator = fake_jobs(mocker)
    with _test_tx(), get_db() as session:
        agent = Agent(
            slug="veille-boamp",
            config={},
            system_prompt="Consigne.",
            pipeline_id=PIPELINE_ID if current else "nouveau-pipeline",
            version=1 if current else 2,
            status="active",
            owner_email="lj@example.org",
            changeset_id="c",
            cursors={},
        )
        session.add(agent)
        session.flush()
        if not current:
            session.add(AgentRun(id=RUN_OK, agent_id=agent.id, pipeline_id=PIPELINE_ID, status="collected"))
        orchestrator.list_pipelines.return_value = [make_pipeline(name="agent-veille-boamp")]

        context = job_mentions.build_context("@agent-veille-boamp")

    assert "--relaunch" not in context
    assert "propose-launch --agent veille-boamp" in context
