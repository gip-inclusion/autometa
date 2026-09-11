"""CLI du skill datadog_logs — skills/datadog_logs/scripts/query.py."""

import importlib.util
import json
from argparse import Namespace
from pathlib import Path

import pytest

from lib.datadog import DatadogError

_spec = importlib.util.spec_from_file_location(
    "datadog_query_cli", Path(__file__).parent.parent / "skills/datadog_logs/scripts/query.py"
)
cli = importlib.util.module_from_spec(_spec)
_spec.loader.exec_module(cli)


def event(attributes: dict) -> dict:
    return {"attributes": {"timestamp": "2026-09-01T00:00:00Z", "attributes": attributes}}


@pytest.mark.parametrize(
    "attributes,expected",
    [
        ({"http": {"url": "/p/1", "status_code": 200}}, {"http.url": "/p/1", "http.status_code": 200}),
        ({"http": {"url": "/p/1"}}, {"http.url": "/p/1", "http.status_code": None}),
        ({"http": None}, {"http.url": None, "http.status_code": None}),
        ({"http": "texte"}, {"http.url": None, "http.status_code": None}),
    ],
    ids=["present", "absent", "intermediate-none", "intermediate-scalar"],
)
def test_pluck_walks_dotted_fields_and_yields_none_when_the_path_breaks(attributes, expected):
    assert cli.pluck(event(attributes), ["http.url", "http.status_code"]) == {"ts": "2026-09-01T00:00:00Z", **expected}


def dump_args(tmp_path, days=2):
    return Namespace(
        query="service:x", days=days, chunk=1, dump=str(tmp_path / "out" / "logs.jsonl"), field=[], workers=1
    )


def test_dump_writes_each_window_as_it_arrives(tmp_path, mocker):
    """Un échec sur une fenêtre ne perd pas les fenêtres déjà lues : elles sont sur disque."""
    client = mocker.Mock()
    client.iter_events.side_effect = [iter([event({"http": {"url": "/a"}})]), DatadogError("HTTP 503")]

    with pytest.raises(DatadogError):
        cli.dump(client, dump_args(tmp_path))

    lines = (tmp_path / "out" / "logs.jsonl").read_text().splitlines()
    assert len(lines) == 1
    assert '"http.url":"/a"' in lines[0]


def test_dump_reports_the_total_and_the_windows(tmp_path, mocker):
    client = mocker.Mock()
    client.iter_events.side_effect = [iter([event({}), event({})]), iter([event({})])]

    result = cli.dump(client, dump_args(tmp_path))

    assert (result["events"], result["windows"]) == (3, 2)
    assert len(Path(result["file"]).read_text().splitlines()) == 3


@pytest.mark.parametrize("fn", [cli.aggregate, cli.dump])
def test_every_cli_path_refuses_to_look_beyond_retention(fn, tmp_path, mocker):
    args = dump_args(tmp_path, days=90)
    args.group_by, args.top, args.distinct = ["@usr.kind"], 5, None

    with pytest.raises(DatadogError, match="30 jours"):
        fn(mocker.Mock(), args)


def test_aggregate_sorts_buckets_by_count_and_adds_the_cardinality_on_demand(mocker):
    client = mocker.Mock()
    client.aggregate.return_value = [
        {"by": {"@usr.kind": "employer"}, "computes": {"c0": 3, "c1": 2}},
        {"by": {"@usr.kind": "prescriber"}, "computes": {"c0": 9, "c1": 4}},
    ]
    args = Namespace(query="service:x", days=7, distinct="@usr.id", group_by=["@usr.kind"], top=5)

    rows = cli.aggregate(client, args)

    assert [(r["by"]["@usr.kind"], r["count"], r["distinct"]) for r in rows] == [
        ("prescriber", 9, 4),
        ("employer", 3, 2),
    ]
    _, kwargs = client.aggregate.call_args
    assert kwargs["compute"] == [{"aggregation": "count"}, {"aggregation": "cardinality", "metric": "@usr.id"}]


@pytest.mark.parametrize(
    "argv,method,expected",
    [
        (["--search", "--limit", "1"], "iter_events", [{"ts": "2026-09-01T00:00:00Z", "http.url": "/a"}]),
        (["--group-by", "@usr.kind"], "aggregate", [{"by": {"@usr.kind": "k"}, "count": 1}]),
        ([], "count", 42),
    ],
    ids=["search", "group-by", "count"],
)
def test_main_dispatches_on_the_flags_and_prints_json(argv, method, expected, mocker, capsys):
    client = mocker.Mock()
    client.__enter__ = lambda self: self
    client.__exit__ = lambda self, *args: None
    client.iter_events.return_value = iter([event({"http": {"url": "/a"}})])
    client.aggregate.return_value = [{"by": {"@usr.kind": "k"}, "computes": {"c0": 1}}]
    client.count.return_value = 42
    mocker.patch.object(cli, "DatadogClient", return_value=client)
    mocker.patch.object(cli, "DEFAULT_FIELDS", ["http.url"])
    mocker.patch("sys.argv", ["query.py", "--query", "service:x", *argv])

    cli.main()

    assert json.loads(capsys.readouterr().out) == expected
    assert getattr(client, method).called


def test_main_dump_writes_the_file_and_prints_its_summary(tmp_path, mocker, capsys):
    client = mocker.Mock()
    client.__enter__ = lambda self: self
    client.__exit__ = lambda self, *args: None
    client.iter_events.return_value = iter([event({})])
    mocker.patch.object(cli, "DatadogClient", return_value=client)
    out = tmp_path / "logs.jsonl"
    mocker.patch("sys.argv", ["query.py", "--query", "service:x", "--days", "1", "--dump", str(out)])

    cli.main()

    assert json.loads(capsys.readouterr().out)["events"] == 1
    assert out.read_text().count("\n") == 1
