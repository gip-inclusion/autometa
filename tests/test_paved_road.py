"""Tests for lib/paved_road.py — ligne de base d'instrumentation du paved road."""

import importlib.util
from datetime import datetime, timedelta, timezone
from pathlib import Path

import pytest

from lib import paved_road
from web.db import get_db
from web.models import Conversation, CronRun, UsageEvent

_spec = importlib.util.spec_from_file_location(
    "paved_road_baseline", Path(__file__).parent.parent / "scripts" / "paved_road_baseline.py"
)
baseline_script = importlib.util.module_from_spec(_spec)
_spec.loader.exec_module(baseline_script)

NOW = datetime.now(timezone.utc)
SINCE = NOW - timedelta(days=90)


def add_conversation(
    session,
    conv_id,
    *,
    started_ago_hours=2,
    minutes=60,
    pr_url=None,
    tokens=(0, 0, 0, 0),
    flag_reason=None,
    needs_response=0,
):
    created = NOW - timedelta(hours=started_ago_hours)
    session.add(
        Conversation(
            id=conv_id,
            created_at=created,
            updated_at=created + timedelta(minutes=minutes),
            pr_url=pr_url,
            usage_input_tokens=tokens[0],
            usage_output_tokens=tokens[1],
            usage_cache_creation_tokens=tokens[2],
            usage_cache_read_tokens=tokens[3],
            flagged_at=NOW if flag_reason else None,
            flag_reason=flag_reason,
            needs_response=needs_response,
        )
    )


def add_turns(session, conv_id, count):
    for _ in range(count):
        session.add(UsageEvent(conversation_id=conv_id, timestamp=NOW, kind="turn", backend="cli"))


def iso(moment):
    return moment.isoformat().replace("+00:00", "Z")


def a_baseline(**overrides):
    data = {
        "days": 90,
        "since": SINCE,
        "feature_runs": [],
        "duration_minutes": paved_road.distribution([30.0, 90.0]),
        "tokens_total": paved_road.distribution([1000.0]),
        "turns": paved_road.distribution([3]),
        "tokens_by_column": dict.fromkeys(paved_road.TOKEN_COLUMNS, 250),
        "human_takeovers": {
            "conversations": 4,
            "with_pr": 2,
            "flagged": 1,
            "needs_response": 0,
            "flag_reasons": [("réponse fausse", 1)],
        },
        "dashboard_health": [{"week": "2026-S32", "runs": 2, "failed": 1, "median_duration_ms": 200}],
        "coverage_floor_drift": [{"date": "2026-05-01", "sha": "abcdef12", "coverage": 74.90, "diff_cover": 90}],
        "gate_noise": None,
    }
    return {**data, **overrides}


@pytest.mark.parametrize(
    "values, expected",
    [
        ([], {"count": 0, "median": None, "max": None}),
        ([5], {"count": 1, "median": 5, "max": 5}),
        ([1, 3, 10], {"count": 3, "median": 3, "max": 10}),
        ([1, 3, 10, 20], {"count": 4, "median": 6.5, "max": 20}),
    ],
)
def test_distribution(values, expected):
    assert paved_road.distribution(values) == expected


def test_feature_runs_keeps_only_conversations_with_a_pr(app):
    with get_db() as session:
        add_conversation(session, "conv-pr", minutes=30, pr_url="https://github.com/x/pull/1", tokens=(10, 20, 30, 40))
        add_conversation(session, "conv-sans-pr", minutes=999)
        add_turns(session, "conv-pr", 3)

    with get_db() as session:
        runs = paved_road.feature_runs(session, SINCE)

    assert [run["id"] for run in runs] == ["conv-pr"]
    assert runs[0]["minutes"] == 30
    assert runs[0]["turns"] == 3
    assert runs[0]["tokens_total"] == 100
    assert runs[0]["tokens"]["usage_cache_read_tokens"] == 40


def test_feature_runs_counts_zero_turns_without_usage_events(app):
    with get_db() as session:
        add_conversation(session, "conv-muette", pr_url="https://github.com/x/pull/2")

    with get_db() as session:
        assert paved_road.feature_runs(session, SINCE)[0]["turns"] == 0


def test_feature_runs_excludes_conversations_older_than_the_window(app):
    with get_db() as session:
        add_conversation(session, "conv-vieille", started_ago_hours=24 * 120, pr_url="https://github.com/x/pull/3")

    with get_db() as session:
        assert paved_road.feature_runs(session, SINCE) == []


def test_human_takeovers_counts_flags_reasons_and_pending_responses(app):
    with get_db() as session:
        add_conversation(session, "c1", pr_url="https://github.com/x/pull/4", flag_reason="réponse fausse")
        add_conversation(session, "c2", flag_reason="réponse fausse")
        add_conversation(session, "c3", needs_response=1)

    with get_db() as session:
        stats = paved_road.human_takeovers(session, SINCE)

    assert stats == {
        "conversations": 3,
        "with_pr": 1,
        "flagged": 2,
        "needs_response": 1,
        "flag_reasons": [("réponse fausse", 2)],
    }


def test_dashboard_health_groups_runs_by_iso_week(app):
    with get_db() as session:
        for days_ago, status, duration in [(1, "success", 100), (1, "failure", 300), (8, "success", 500)]:
            session.add(
                CronRun(
                    app_slug="tdb",
                    started_at=NOW - timedelta(days=days_ago),
                    status=status,
                    duration_ms=duration,
                )
            )

    with get_db() as session:
        weeks = paved_road.dashboard_health(session, SINCE)

    assert [week["runs"] for week in weeks] == [1, 2]
    assert weeks[-1] == {"week": weeks[-1]["week"], "runs": 2, "failed": 1, "median_duration_ms": 200}


def test_dashboard_health_reports_no_median_without_durations(app):
    with get_db() as session:
        session.add(CronRun(app_slug="tdb", started_at=NOW - timedelta(days=1), status="success"))

    with get_db() as session:
        assert paved_road.dashboard_health(session, SINCE)[0]["median_duration_ms"] is None


def test_github_pages_stops_on_a_short_page(mocker):
    pages = [[{"n": n} for n in range(100)], [{"n": 100}]]
    github_get = mocker.patch.object(paved_road, "github_get", side_effect=pages)

    assert len(list(paved_road.github_pages("/actions/runs", {}, "workflow_runs"))) == 101
    assert github_get.call_count == 2


def test_github_pages_warns_when_truncated(mocker, caplog):
    mocker.patch.object(paved_road, "github_get", return_value=[{"n": n} for n in range(100)])

    assert len(list(paved_road.github_pages("/actions/runs", {}, "workflow_runs"))) == 100 * paved_road.MAX_PAGES
    assert "tronqué" in caplog.text


def test_github_get_unwraps_and_authenticates(mocker):
    mocker.patch.object(paved_road.config, "GITHUB_TOKEN", "jeton")
    response = mocker.MagicMock()
    response.json.return_value = {"jobs": [{"name": "Tests"}]}
    get = mocker.patch.object(paved_road.httpx, "get", return_value=response)

    assert paved_road.github_get("/actions/runs/1/jobs", {}, "jobs") == [{"name": "Tests"}]
    assert get.call_args.kwargs["headers"]["Authorization"] == "Bearer jeton"
    assert get.call_args.kwargs["timeout"] == 30


CI_PATH = ".github/workflows/ci.yml"


def test_gate_noise_aggregates_failures_by_job_and_merged_pulls(mocker):
    since = NOW - timedelta(days=30)
    responses = {
        "/actions/workflows": [{"id": 42, "path": CI_PATH}],
        "/actions/workflows/42/runs": [
            {"id": 1, "name": "PR #1", "path": CI_PATH, "conclusion": "failure", "head_branch": "feat"},
            {"id": 2, "name": "PR #2", "path": CI_PATH, "conclusion": "success", "head_branch": "feat"},
            {"id": 3, "name": "PR #3", "path": CI_PATH, "conclusion": "success", "head_branch": "autre"},
        ],
        "/actions/runs/1/jobs": [
            {"name": "Tests", "conclusion": "failure"},
            {"name": "Lint", "conclusion": "success"},
        ],
        "/pulls": [
            {"updated_at": iso(NOW - timedelta(days=1)), "merged_at": iso(NOW), "head": {"ref": "feat"}},
            {"updated_at": iso(NOW - timedelta(days=2)), "merged_at": None, "head": {"ref": "abandonnee"}},
            {"updated_at": iso(NOW - timedelta(days=40)), "merged_at": iso(NOW), "head": {"ref": "hors-fenetre"}},
        ],
    }
    mocker.patch.object(paved_road, "github_get", side_effect=lambda path, params, key=None: responses[path])

    noise = paved_road.gate_noise(since)

    assert noise["runs"] == 3
    assert noise["failed_runs"] == 1
    assert noise["by_workflow"] == [{"workflow": CI_PATH, "runs": 3, "failed": 1}]
    assert noise["by_job"] == [{"workflow": CI_PATH, "job": "Tests", "failures": 1, "workflow_runs": 3}]
    assert noise["merged_pulls"] == 1
    assert noise["merged_pulls_with_failure"] == 1


PYPROJECT_70 = "[tool.coverage.report]\nfail_under = 70.0\n[tool.diff_cover]\nfail_under = 90\n"
PYPROJECT_74 = "[tool.coverage.report]\nfail_under = 74.90\n[tool.diff_cover]\nfail_under = 90\n"


def test_git_output_runs_git_in_the_repository():
    assert len(paved_road.git_output("rev-parse", "HEAD").strip()) == 40


@pytest.mark.parametrize(
    "files, expected",
    [
        ({"pyproject.toml": PYPROJECT_74}, (74.90, 90)),
        ({"gates.toml": PYPROJECT_74}, (74.90, 90)),
        ({"pyproject.toml": PYPROJECT_70, "gates.toml": PYPROJECT_74}, (74.90, 90)),
        ({"pyproject.toml": "[tool.ruff]\nline-length = 120\n"}, (None, None)),
        ({}, (None, None)),
    ],
)
def test_coverage_floors_at_reads_gates_then_pyproject(mocker, files, expected):
    mocker.patch.object(paved_road, "file_at", side_effect=lambda sha, path: files.get(path, ""))

    assert paved_road.coverage_floors_at("deadbeef") == expected


def test_file_at_returns_empty_for_a_missing_file():
    assert paved_road.file_at("HEAD", "fichier-qui-n-existe-pas.toml") == ""


def test_coverage_floor_drift_reports_only_changes(mocker):
    contents = {"aaaaaaaa": PYPROJECT_70, "bbbbbbbb": PYPROJECT_70, "cccccccc": PYPROJECT_74}
    logs = [
        "aaaaaaaa 2026-05-01T10:00:00+02:00\n",
        "bbbbbbbb 2026-06-01T10:00:00+02:00\ncccccccc 2026-07-01T10:00:00+02:00\n",
    ]

    mocker.patch.object(paved_road, "git_output", side_effect=lambda *args: logs.pop(0))
    mocker.patch.object(
        paved_road, "file_at", side_effect=lambda sha, path: contents[sha] if path == "pyproject.toml" else ""
    )

    drift = paved_road.coverage_floor_drift(SINCE)

    assert [(row["sha"], row["coverage"]) for row in drift] == [("aaaaaaaa", 70.0), ("cccccccc", 74.90)]
    assert drift[0]["date"] == "2026-05-01"


@pytest.mark.parametrize("token, expected", [("", None), ("jeton", {"runs": 0})])
def test_collect_computes_gate_noise_only_with_a_token(app, mocker, token, expected):
    mocker.patch.object(paved_road.config, "GITHUB_TOKEN", token)
    mocker.patch.object(paved_road, "coverage_floor_drift", return_value=[])
    mocker.patch.object(paved_road, "gate_noise", return_value={"runs": 0})

    collected = paved_road.collect(days=7)

    assert collected["gate_noise"] == expected
    assert collected["days"] == 7
    assert collected["since"] > NOW - timedelta(days=8)


def test_collect_summarizes_the_conversations_that_produced_a_pr(app, mocker):
    mocker.patch.object(paved_road.config, "GITHUB_TOKEN", "")
    mocker.patch.object(paved_road, "coverage_floor_drift", return_value=[])
    with get_db() as session:
        add_conversation(session, "c1", minutes=30, pr_url="https://github.com/x/pull/1", tokens=(1, 2, 3, 4))
        add_conversation(session, "c2", minutes=90, pr_url="https://github.com/x/pull/2", tokens=(1, 2, 3, 4))

    collected = paved_road.collect(days=7)

    assert collected["duration_minutes"] == {"count": 2, "median": 60.0, "max": 90.0}
    assert collected["tokens_total"]["median"] == 10
    assert collected["tokens_by_column"]["usage_input_tokens"] == 2


@pytest.mark.parametrize(
    "rows, expected",
    [([], "_Aucune donnée sur la fenêtre._"), ([["a", None]], "| a | — |")],
)
def test_table(rows, expected):
    assert paved_road.table(["x", "y"], rows)[-1] == expected


def test_render_states_the_pr_url_proxy_caveat():
    assert paved_road.PROXY_CAVEAT in paved_road.render(a_baseline())


def test_render_says_when_the_github_token_is_missing():
    assert "`GITHUB_TOKEN` absent" in paved_road.render(a_baseline())


def test_render_reports_the_gate_noise_share_and_job_table():
    noise = {
        "runs": 10,
        "failed_runs": 4,
        "by_workflow": [{"workflow": "CI", "runs": 10, "failed": 4}],
        "by_job": [{"workflow": "CI", "job": "Tests", "failures": 3, "workflow_runs": 10}],
        "merged_pulls": 8,
        "merged_pulls_with_failure": 2,
    }

    rendered = paved_road.render(a_baseline(gate_noise=noise))

    assert "2 des 8 PR mergées ont connu au moins un échec (25 %)" in rendered
    assert "| CI | Tests | 3 | 30 % |" in rendered


def test_render_handles_a_window_without_any_merged_pull():
    noise = {
        "runs": 0,
        "failed_runs": 0,
        "by_workflow": [],
        "by_job": [],
        "merged_pulls": 0,
        "merged_pulls_with_failure": 0,
    }

    assert "0 des 0 PR mergées ont connu au moins un échec (—)" in paved_road.render(a_baseline(gate_noise=noise))


def test_main_prints_the_baseline_for_the_requested_window(mocker, capsys):
    collect = mocker.patch.object(paved_road, "collect", return_value=a_baseline(days=30))

    assert baseline_script.main(["--days", "30"]) == 0
    collect.assert_called_once_with(30)
    assert "# Ligne de base du paved road — 30 derniers jours" in capsys.readouterr().out
