"""Tests for lib/api_signals.py."""

import io
import sys

from lib.api_signals import SIGNAL_PATTERN, emit_api_signal, parse_api_signals, strip_api_signals


def test_emit_api_signal_emits_matomo_signal():
    captured = io.StringIO()
    old_stdout = sys.stdout
    sys.stdout = captured

    emit_api_signal(
        source="matomo",
        instance="inclusion",
        method="VisitsSummary.get",
        url="https://matomo.inclusion.gouv.fr/?module=API&method=VisitsSummary.get",
    )

    sys.stdout = old_stdout
    output = captured.getvalue()

    assert "[AUTOMETA:API:" in output
    assert '"source": "matomo"' in output
    assert '"instance": "inclusion"' in output
    assert '"method": "VisitsSummary.get"' in output
    assert '"url":' in output


def test_emit_api_signal_emits_metabase_signal_with_sql():
    captured = io.StringIO()
    old_stdout = sys.stdout
    sys.stdout = captured

    emit_api_signal(
        source="metabase",
        instance="stats",
        sql="SELECT * FROM users WHERE created_at > '2025-01-01'",
        url="https://stats.inclusion.gouv.fr/question#...",
    )

    sys.stdout = old_stdout
    output = captured.getvalue()

    assert "[AUTOMETA:API:" in output
    assert '"source": "metabase"' in output
    assert '"sql":' in output


def test_emit_api_signal_emits_metabase_signal_with_card_id():
    captured = io.StringIO()
    old_stdout = sys.stdout
    sys.stdout = captured

    emit_api_signal(
        source="metabase",
        instance="stats",
        card_id=123,
        url="https://stats.inclusion.gouv.fr/question/123",
    )

    sys.stdout = old_stdout
    output = captured.getvalue()

    assert '"card_id": 123' in output


def test_emit_api_signal_truncates_long_sql():
    captured = io.StringIO()
    old_stdout = sys.stdout
    sys.stdout = captured

    long_sql = "SELECT " + "x, " * 200 + "y FROM table"
    emit_api_signal(
        source="metabase",
        instance="stats",
        sql=long_sql,
        url="https://example.com",
    )

    sys.stdout = old_stdout
    output = captured.getvalue()

    # SQL should be truncated to ~500 chars + "..."
    assert "..." in output
    assert len(output) < len(long_sql) + 200


def test_parse_api_signals_parses_single_signal():
    content = '[AUTOMETA:API:{"source":"matomo","instance":"inclusion","url":"https://..."}]'
    signals = parse_api_signals(content)

    assert len(signals) == 1
    assert signals[0]["source"] == "matomo"
    assert signals[0]["instance"] == "inclusion"


def test_parse_api_signals_parses_multiple_signals():
    content = """
    [AUTOMETA:API:{"source":"matomo","instance":"inclusion","url":"https://matomo..."}]
    Some output here
    [AUTOMETA:API:{"source":"metabase","instance":"stats","url":"https://metabase..."}]
    More output
    """
    signals = parse_api_signals(content)

    assert len(signals) == 2
    assert signals[0]["source"] == "matomo"
    assert signals[1]["source"] == "metabase"


def test_parse_api_signals_parses_signal_mixed_with_output():
    content = """
    Starting analysis...
    [AUTOMETA:API:{"source":"matomo","method":"VisitsSummary.get","url":"https://..."}]
    Visits: 1,234
    Unique visitors: 567
    Done.
    """
    signals = parse_api_signals(content)

    assert len(signals) == 1
    assert signals[0]["method"] == "VisitsSummary.get"


def test_parse_api_signals_returns_empty_list_when_no_signals():
    content = "Just some regular output\nwith multiple lines\nno signals here"
    signals = parse_api_signals(content)

    assert signals == []


def test_parse_api_signals_ignores_malformed_json():
    content = '[AUTOMETA:API:{"invalid json}] [AUTOMETA:API:{"source":"matomo","url":"x"}]'
    signals = parse_api_signals(content)

    # Should parse the valid one, skip the invalid
    assert len(signals) == 1
    assert signals[0]["source"] == "matomo"


def test_parse_api_signals_handles_nested_json_in_output():
    # The signal should be found even when there's other JSON in the output
    content = """
    Result: {"data": [1, 2, 3]}
    [AUTOMETA:API:{"source":"matomo","url":"https://..."}]
    More data: {"count": 100}
    """
    signals = parse_api_signals(content)

    assert len(signals) == 1
    assert signals[0]["source"] == "matomo"


def test_strip_api_signals_strips_single_signal():
    content = '[AUTOMETA:API:{"source":"matomo","url":"x"}] Hello'
    result = strip_api_signals(content)

    assert "[AUTOMETA:API:" not in result
    assert "Hello" in result


def test_strip_api_signals_strips_multiple_signals():
    content = """
    [AUTOMETA:API:{"source":"matomo","url":"x"}]
    Output line 1
    [AUTOMETA:API:{"source":"metabase","url":"y"}]
    Output line 2
    """
    result = strip_api_signals(content)

    assert "[AUTOMETA:API:" not in result
    assert "Output line 1" in result
    assert "Output line 2" in result


def test_strip_api_signals_preserves_content_without_signals():
    content = "Just regular output\nNo signals here"
    result = strip_api_signals(content)

    assert result == content.strip()


def test_signal_pattern_matches_minimal_signal():
    text = "[AUTOMETA:API:{}]"
    match = SIGNAL_PATTERN.search(text)
    assert match is not None


def test_signal_pattern_matches_with_content():
    text = '[AUTOMETA:API:{"key":"value"}]'
    match = SIGNAL_PATTERN.search(text)
    assert match is not None
    assert match.group(1) == '{"key":"value"}'


def test_signal_pattern_does_not_match_partial():
    # Should not match incomplete patterns
    assert SIGNAL_PATTERN.search("[AUTOMETA:API:") is None
    assert SIGNAL_PATTERN.search("AUTOMETA:API:{}") is None
    assert SIGNAL_PATTERN.search("[AUTOMETA:{}]") is None


def test_roundtrip_matomo():
    captured = io.StringIO()
    old_stdout = sys.stdout
    sys.stdout = captured

    emit_api_signal(
        source="matomo",
        instance="inclusion",
        method="Events.getCategory",
        url="https://matomo.inclusion.gouv.fr/?...",
    )

    sys.stdout = old_stdout
    output = captured.getvalue()

    signals = parse_api_signals(output)
    assert len(signals) == 1
    assert signals[0]["source"] == "matomo"
    assert signals[0]["instance"] == "inclusion"
    assert signals[0]["method"] == "Events.getCategory"


def test_roundtrip_metabase():
    captured = io.StringIO()
    old_stdout = sys.stdout
    sys.stdout = captured

    emit_api_signal(
        source="metabase",
        instance="datalake",
        sql="SELECT COUNT(*) FROM users",
        url="https://datalake.inclusion.gouv.fr/question#...",
    )

    sys.stdout = old_stdout
    output = captured.getvalue()

    signals = parse_api_signals(output)
    assert len(signals) == 1
    assert signals[0]["source"] == "metabase"
    assert signals[0]["instance"] == "datalake"
    assert "SELECT COUNT" in signals[0]["sql"]


def test_roundtrip_multiple():
    captured = io.StringIO()
    old_stdout = sys.stdout
    sys.stdout = captured

    emit_api_signal(source="matomo", instance="inclusion", url="url1")
    print("Some output between signals")
    emit_api_signal(source="metabase", instance="stats", url="url2")

    sys.stdout = old_stdout
    output = captured.getvalue()

    signals = parse_api_signals(output)
    assert len(signals) == 2
    assert signals[0]["source"] == "matomo"
    assert signals[1]["source"] == "metabase"
