import json
from types import SimpleNamespace

import pytest

from web.routes.conversations import extract_previous_findings, extract_tool_output


def msg(type, content):
    return SimpleNamespace(type=type, content=content)


@pytest.mark.parametrize(
    "content, expected",
    [
        (json.dumps({"tool": "Bash", "output": "result text"}), "result text"),
        (json.dumps({"output": {"output": "nested result"}}), "nested result"),
        (json.dumps({"output": {"tool": "x", "output": "data"}, "api_calls": [{"source": "matomo"}]}), "data"),
        (json.dumps({"tool": "Bash"}), ""),
        ("plain text output", "plain text output"),
        ("", ""),
        ("{broken", "{broken"),
    ],
)
def test_extract_tool_output(content, expected):
    assert extract_tool_output(content) == expected


class TestExtractPreviousFindings:
    def test_empty_messages(self):
        assert extract_previous_findings([]) == ""

    def test_no_tool_results(self):
        messages = [msg("user", "hello"), msg("assistant", "world")]
        assert extract_previous_findings(messages) == ""

    def test_single_turn_with_tool_results(self):
        messages = [
            msg("user", "query data"),
            msg("tool_use", json.dumps({"tool": "Bash"})),
            msg("tool_result", json.dumps({"output": "row1: value1, row2: value2, row3: value3"})),
            msg("assistant", "Here are the results"),
        ]
        assert "row1: value1" in extract_previous_findings(messages)

    def test_stops_at_previous_user_message(self):
        messages = [
            msg("user", "first question"),
            msg("tool_result", json.dumps({"output": "old data from first turn here"})),
            msg("assistant", "first answer"),
            msg("user", "second question"),
            msg("tool_result", json.dumps({"output": "new data from second turn here"})),
            msg("assistant", "second answer"),
        ]
        result = extract_previous_findings(messages)
        assert "new data" in result
        assert "old data" not in result

    def test_skips_short_results(self):
        messages = [
            msg("user", "q"),
            msg("tool_result", json.dumps({"output": "ok"})),
            msg("assistant", "a"),
        ]
        assert extract_previous_findings(messages) == ""

    def test_truncates_long_results(self):
        messages = [
            msg("user", "q"),
            msg("tool_result", json.dumps({"output": "x" * 1000})),
            msg("assistant", "a"),
        ]
        result = extract_previous_findings(messages)
        assert len(result) < 500
        assert result.endswith("…")

    def test_caps_total_size(self):
        messages = [msg("user", "q")]
        for i in range(50):
            messages.append(msg("tool_result", json.dumps({"output": f"result number {i} " + "data " * 50})))
        messages.append(msg("assistant", "done"))

        result = extract_previous_findings(messages)
        assert len(result) < 6000
        assert "omis" in result

    @pytest.mark.parametrize(
        "content",
        [
            "plain string result with enough chars to pass",
            json.dumps({"output": "dict output with enough chars to pass"}),
            json.dumps({"output": {"output": "nested output with enough chars to pass"}}),
        ],
    )
    def test_handles_various_content_formats(self, content):
        messages = [
            msg("user", "q"),
            msg("tool_result", content),
            msg("assistant", "a"),
        ]
        assert extract_previous_findings(messages) != ""
