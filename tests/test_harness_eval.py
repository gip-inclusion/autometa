"""Tests for lib/harness_eval.py, lib/eval_corpus.py, evals/metrics/gold_free.py, web/harness_eval.py."""

import json

import pytest
from fastapi import FastAPI
from fastapi.testclient import TestClient

from lib.harness_eval import (
    MetricResult,
    RunResult,
    Session,
    SessionResult,
    ToolCall,
    Turn,
    diff_runs,
    parse_gold_json,
    parse_session_jsonl,
    run_benchmark,
    run_metrics,
    run_result_from_json,
    run_result_to_json,
)


def make_turn(index=0, user_text="hello", assistant_text="world", **kwargs):
    return Turn(index=index, user_text=user_text, assistant_text=assistant_text, **kwargs)


def make_session(session_id="test", turns=None, **kwargs):
    return Session(session_id=session_id, turns=turns or [], **kwargs)


class TestSessionParsing:
    def test_parses_user_and_assistant(self):
        text = "\n".join([
            json.dumps({"type": "user", "message": {"role": "user", "content": "Bonjour"}, "timestamp": "T1"}),
            json.dumps({
                "message": {
                    "role": "assistant",
                    "content": [{"type": "text", "text": "Salut"}],
                    "usage": {"input_tokens": 100, "output_tokens": 50},
                },
                "timestamp": "T2",
            }),
        ])
        s = parse_session_jsonl(text, session_id="abc")
        assert s.session_id == "abc"
        assert len(s.turns) == 1
        assert s.turns[0].user_text == "Bonjour"
        assert s.total_input_tokens == 100

    def test_skips_queue_operations(self):
        text = "\n".join([
            json.dumps({"type": "queue-operation", "operation": "enqueue", "timestamp": "T1"}),
            json.dumps({"type": "user", "message": {"role": "user", "content": "Hi"}, "timestamp": "T2"}),
            json.dumps({
                "message": {"role": "assistant", "content": [{"type": "text", "text": "Hello"}], "usage": {}},
                "timestamp": "T3",
            }),
        ])
        s = parse_session_jsonl(text, session_id="x")
        assert len(s.turns) == 1

    def test_extracts_sql_from_text(self):
        sql_text = "Result:\n```sql\nSELECT COUNT(*) FROM users\n```"
        text = "\n".join([
            json.dumps({"type": "user", "message": {"role": "user", "content": "Combien ?"}, "timestamp": "T1"}),
            json.dumps({
                "message": {"role": "assistant", "content": [{"type": "text", "text": sql_text}], "usage": {}},
                "timestamp": "T2",
            }),
        ])
        s = parse_session_jsonl(text, session_id="x")
        assert len(s.turns[0].sql_statements) == 1
        assert "SELECT COUNT" in s.turns[0].sql_statements[0]

    def test_extracts_tool_use(self):
        text = "\n".join([
            json.dumps({"type": "user", "message": {"role": "user", "content": "go"}, "timestamp": "T1"}),
            json.dumps({
                "message": {
                    "role": "assistant",
                    "content": [{"type": "tool_use", "name": "Bash", "input": {"command": "ls"}}],
                    "usage": {},
                },
                "timestamp": "T2",
            }),
        ])
        s = parse_session_jsonl(text, session_id="x")
        assert s.turns[0].tool_calls[0].name == "Bash"
        assert s.turns[0].tool_calls[0].input == {"command": "ls"}

    def test_skips_corrupt_lines(self):
        text = (
            "{corrupt\n"
            + json.dumps({"type": "user", "message": {"role": "user", "content": "Hi"}, "timestamp": "T1"})
            + "\n"
            + json.dumps({
                "message": {"role": "assistant", "content": [{"type": "text", "text": "Yo"}], "usage": {}},
                "timestamp": "T2",
            })
        )
        s = parse_session_jsonl(text, session_id="x")
        assert len(s.turns) == 1


class TestGoldParsing:
    def test_full_gold(self):
        data = {
            "session_id": "abc-123",
            "version": 1,
            "conversation_level": {"overall_quality": 4, "correctness": 5, "tags": ["sql"]},
            "turns": [{"turn_index": 0, "gold_sql": "SELECT 1", "is_correction": False}],
        }
        gold = parse_gold_json(json.dumps(data))
        assert gold.session_id == "abc-123"
        assert gold.overall_quality == 4
        assert gold.turns[0].gold_sql == "SELECT 1"

    def test_empty_gold(self):
        data = {"session_id": "x", "version": 0, "conversation_level": {}, "turns": []}
        gold = parse_gold_json(json.dumps(data))
        assert gold.version == 0
        assert gold.turns == []


class TestDataclassDefaults:
    def test_turn_independent_lists(self):
        a = Turn(index=0, user_text="", assistant_text="")
        b = Turn(index=1, user_text="", assistant_text="")
        a.tool_calls.append(ToolCall(name="Bash"))
        assert b.tool_calls == []

    def test_metric_result_defaults(self):
        r = MetricResult(name="m", score=0.5)
        assert r.details == {}


class TestPersistence:
    def test_roundtrip(self):
        run = RunResult(
            run_id="r1",
            timestamp="T1",
            session_results=[SessionResult(session_id="s1", metrics=[MetricResult(name="m", score=0.85)])],
            aggregate_scores={"m": 0.85},
        )
        loaded = run_result_from_json(run_result_to_json(run))
        assert loaded.run_id == "r1"
        assert loaded.aggregate_scores["m"] == 0.85
        assert loaded.session_results[0].metrics[0].score == 0.85


class TestRunner:
    def test_collects_results(self):
        session = make_session(turns=[make_turn()])
        result = run_metrics(session, [lambda s: MetricResult(name="dummy", score=0.9)])
        assert result.metrics[0].score == 0.9

    def test_handles_metric_failure(self):
        def broken(s):
            raise ValueError("boom")

        result = run_metrics(make_session(turns=[make_turn()]), [broken])
        assert result.metrics[0].score == 0.0
        assert "boom" in result.metrics[0].details["error"]

    def test_benchmark_aggregates(self):
        sessions = [make_session("s1", [make_turn()]), make_session("s2", [make_turn()])]
        result = run_benchmark(sessions, [lambda s: MetricResult(name="const", score=0.8)], run_id="t")
        assert result.aggregate_scores["const"] == 0.8


class TestDiff:
    def test_structured_diff(self):
        b = RunResult(
            run_id="b",
            timestamp="T1",
            aggregate_scores={"m": 0.8},
            session_results=[
                SessionResult(session_id="s1", metrics=[MetricResult(name="m", score=0.8)]),
            ],
        )
        v = RunResult(
            run_id="v",
            timestamp="T2",
            aggregate_scores={"m": 0.9},
            session_results=[
                SessionResult(session_id="s1", metrics=[MetricResult(name="m", score=0.9)]),
            ],
        )
        d = diff_runs(b, v)
        assert d["baseline_run_id"] == "b"
        assert d["aggregate"][0]["delta"] == pytest.approx(0.1)
        assert d["per_session"][0]["session_id"] == "s1"


class TestGoldFreeMetrics:
    def test_correction_keywords(self):
        from evals.metrics.gold_free import metric_correction_rate

        s = make_session(
            turns=[
                make_turn(0, "Montre stats"),
                make_turn(1, "Non, pas ça, je voulais X"),
                make_turn(2, "Merci"),
            ]
        )
        r = metric_correction_rate(s)
        assert r.details["n_corrections"] == 1
        assert r.score < 1.0

    def test_correction_no_corrections(self):
        from evals.metrics.gold_free import metric_correction_rate

        r = metric_correction_rate(make_session(turns=[make_turn(0, "Bonjour"), make_turn(1, "Merci")]))
        assert r.score == 1.0

    def test_tool_chain_length(self):
        from evals.metrics.gold_free import metric_tool_chain_length

        s = make_session(
            turns=[
                make_turn(0, tool_calls=[ToolCall("Bash"), ToolCall("Read"), ToolCall("Edit")]),
            ]
        )
        r = metric_tool_chain_length(s)
        assert r.details["total_tool_calls"] == 3
        assert r.details["max_chain"] == 3

    def test_knowledge_read_before_api(self):
        from evals.metrics.gold_free import metric_knowledge_utilization

        s = make_session(
            turns=[
                make_turn(
                    0,
                    tool_calls=[
                        ToolCall("Read", {"file_path": "knowledge/sites/emplois.md"}),
                        ToolCall("Skill", {"skill": "matomo_query"}),
                    ],
                )
            ]
        )
        assert metric_knowledge_utilization(s).score == 1.0

    def test_knowledge_api_before_read(self):
        from evals.metrics.gold_free import metric_knowledge_utilization

        s = make_session(turns=[make_turn(0, tool_calls=[ToolCall("Bash", {"command": "echo"})])])
        assert metric_knowledge_utilization(s).score == 0.0

    def test_hallucination_known_site(self):
        from evals.metrics.gold_free import metric_hallucination_signals

        s = make_session(turns=[make_turn(0, "stats", "idSite=117 shows...")])
        assert metric_hallucination_signals(s).score == 1.0

    def test_hallucination_phantom_site(self):
        from evals.metrics.gold_free import metric_hallucination_signals

        s = make_session(turns=[make_turn(0, "stats", "idSite=999 shows...")])
        r = metric_hallucination_signals(s)
        assert r.score < 1.0
        assert 999 in r.details["phantom_site_ids"]

    def test_sql_syntactic_no_sql(self):
        from evals.metrics.gold_free import metric_sql_syntactic_validity

        assert metric_sql_syntactic_validity(make_session(turns=[make_turn()])).score == 1.0

    def test_token_efficiency(self):
        from evals.metrics.gold_free import metric_token_efficiency

        s = make_session(
            turns=[make_turn(input_tokens=1000, output_tokens=500, cache_read_tokens=300)],
            total_input_tokens=1000,
            total_output_tokens=500,
        )
        r = metric_token_efficiency(s)
        assert 0.0 < r.score <= 1.0

    @pytest.mark.parametrize(
        "user_text,expect_score",
        [
            ("Combien de candidatures ?", 0.0),
            ("Bonjour", 1.0),
        ],
    )
    def test_sql_presence(self, user_text, expect_score):
        from evals.metrics.gold_free import metric_sql_presence

        r = metric_sql_presence(make_session(turns=[make_turn(0, user_text, "no SQL")]))
        assert r.score == expect_score or r.details.get("note")


class TestGoldBackedMetrics:
    def _gold(self, short_id="abc12345", expected_skills=None, overall_quality=None):
        from lib.harness_eval import Gold

        return Gold(
            session_id=f"{short_id}-full-uuid",
            version=1,
            overall_quality=overall_quality,
            expected_skills=expected_skills or [],
        )

    def test_expected_skills_all_used(self):
        from evals.metrics.gold_backed import make_metric_expected_skills_used

        gold = self._gold(expected_skills=["metabase_query", "matomo_query"])
        gold_by_id = {"abc12345": gold}
        metric = make_metric_expected_skills_used(gold_by_id)

        session = Session(
            session_id="abc12345-full-uuid",
            turns=[
                Turn(
                    index=0,
                    user_text="",
                    assistant_text="",
                    tool_calls=[
                        ToolCall(name="Skill", input={"skill": "metabase_query"}),
                        ToolCall(name="Skill", input={"skill": "matomo_query"}),
                    ],
                ),
            ],
        )
        r = metric(session)
        assert r.score == 1.0
        assert set(r.details["matched"]) == {"metabase_query", "matomo_query"}

    def test_expected_skills_partial(self):
        from evals.metrics.gold_backed import make_metric_expected_skills_used

        gold_by_id = {"abc12345": self._gold(expected_skills=["metabase_query", "matomo_query"])}
        metric = make_metric_expected_skills_used(gold_by_id)
        session = Session(
            session_id="abc12345-x",
            turns=[
                Turn(
                    index=0,
                    user_text="",
                    assistant_text="",
                    tool_calls=[
                        ToolCall(name="Skill", input={"skill": "metabase_query"}),
                    ],
                ),
            ],
        )
        r = metric(session)
        assert r.score == 0.5
        assert r.details["missing"] == ["matomo_query"]

    def test_expected_skills_no_gold(self):
        from evals.metrics.gold_backed import make_metric_expected_skills_used

        metric = make_metric_expected_skills_used({})
        r = metric(Session(session_id="unknown", turns=[]))
        assert r.score == 1.0
        assert r.details["note"] == "no gold"

    def test_overall_quality_normalized(self):
        from evals.metrics.gold_backed import make_metric_overall_quality

        gold_by_id = {"abc12345": self._gold(overall_quality=4)}
        metric = make_metric_overall_quality(gold_by_id)
        r = metric(Session(session_id="abc12345-x", turns=[]))
        assert r.score == 0.8
        assert r.details["raw_score_1_to_5"] == 4

    def test_build_gold_backed_returns_two(self):
        from evals.metrics.gold_backed import build_gold_backed_metrics

        metrics = build_gold_backed_metrics({})
        assert len(metrics) == 2
        names = {m.__name__ for m in metrics}
        assert names == {"metric_expected_skills_used", "metric_overall_quality"}


class TestEvalCorpusS3:
    def test_list_sessions(self, mocker):
        mocker.patch(
            "web.s3.eval_corpus.list_files",
            return_value=[
                {"path": "sessions/abc.jsonl", "size": 100, "last_modified": "T1"},
                {"path": "sessions/def.jsonl", "size": 200, "last_modified": "T2"},
                {"path": "sessions/ignore.txt", "size": 50, "last_modified": "T3"},
            ],
        )
        from lib import eval_corpus

        assert eval_corpus.list_sessions() == ["abc", "def"]

    def test_load_session_not_found(self, mocker):
        mocker.patch("web.s3.eval_corpus.download", return_value=None)
        from lib import eval_corpus

        assert eval_corpus.load_session("missing") is None

    def test_load_run_roundtrip(self, mocker):
        from lib import eval_corpus
        from lib.harness_eval import RunResult, run_result_to_json

        run = RunResult(run_id="r", timestamp="T", aggregate_scores={"m": 0.5})
        mocker.patch("web.s3.eval_corpus.download", return_value=run_result_to_json(run).encode())
        loaded = eval_corpus.load_run("r")
        assert loaded.run_id == "r"
        assert loaded.aggregate_scores["m"] == 0.5

    def test_list_runs_sorted(self, mocker):
        mocker.patch(
            "web.s3.eval_corpus.list_files",
            return_value=[
                {"path": "results/older.json", "size": 100, "last_modified": "2026-01-01"},
                {"path": "results/newer.json", "size": 100, "last_modified": "2026-05-01"},
            ],
        )
        from lib import eval_corpus

        runs = eval_corpus.list_runs()
        assert runs[0]["run_id"] == "newer"

    def test_persist_run(self, mocker):
        mock_upload = mocker.patch("web.s3.eval_corpus.upload", return_value=True)
        from lib import eval_corpus
        from lib.harness_eval import RunResult

        eval_corpus.persist_run(RunResult(run_id="r1", timestamp="T", aggregate_scores={}))
        mock_upload.assert_called_once()
        assert mock_upload.call_args[0][0] == "results/r1.json"


class TestWebRoutes:
    @pytest.fixture
    def client(self, mocker):
        from web import config, harness_eval

        config.ADMIN_USERS = ["admin@test.com"]
        app = FastAPI()
        app.include_router(harness_eval.router)
        app.dependency_overrides[harness_eval.get_current_user] = lambda: "admin@test.com"
        return TestClient(app), mocker

    def test_list_runs_admin_only(self, mocker):
        from web import config, harness_eval

        config.ADMIN_USERS = ["admin@test.com"]
        app = FastAPI()
        app.include_router(harness_eval.router)
        app.dependency_overrides[harness_eval.get_current_user] = lambda: "nobody@test.com"
        client = TestClient(app)
        assert client.get("/harness-eval").status_code == 403

    def test_run_not_found(self, client):
        c, mocker = client
        mocker.patch("lib.eval_corpus.load_run", return_value=None)
        mocker.patch("lib.eval_corpus.list_runs", return_value=[])
        assert c.get("/harness-eval/runs/missing").status_code == 404

    def test_diff_renders(self, client):
        c, mocker = client
        from lib.harness_eval import MetricResult, RunResult, SessionResult

        def fake_load(run_id):
            return RunResult(
                run_id=run_id,
                timestamp="T",
                session_results=[SessionResult(session_id="s1", metrics=[MetricResult(name="m", score=0.5)])],
                aggregate_scores={"m": 0.5},
            )

        mocker.patch("lib.eval_corpus.load_run", side_effect=fake_load)
        resp = c.get("/harness-eval/diff?baseline=a&variant=b")
        assert resp.status_code == 200
        assert b"baseline" in resp.content.lower() or b"variant" in resp.content.lower()
