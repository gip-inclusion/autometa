"""Tests du rendu du message de rattrapage."""

import json

import pytest

from web.catchup import CLIP_MARKER_OVERHEAD, TOTAL_CAP, build_catchup
from web.database import Message


def _msg(msg_id, type_, content):
    return Message(id=msg_id, conversation_id="c1", type=type_, content=content)


def test_empty_input_yields_empty_catchup():
    assert build_catchup([]) == []


def test_renders_user_and_assistant_turns():
    msgs = [_msg(1, "user", "quelle audience ?"), _msg(2, "assistant", "je regarde")]

    assert build_catchup(msgs) == [
        {"role": "user", "content": "quelle audience ?"},
        {"role": "assistant", "content": "je regarde"},
    ]


def test_renders_tool_use_and_tool_result():
    msgs = [
        _msg(1, "tool_use", json.dumps({"tool": "Read", "input": {"file_path": "/a.md"}})),
        _msg(2, "tool_result", json.dumps({"output": "contenu"})),
    ]
    result = build_catchup(msgs)

    assert result[0]["role"] == "assistant"
    assert "Read" in result[0]["content"] and "/a.md" in result[0]["content"]
    assert "contenu" in result[1]["content"]


@pytest.mark.parametrize("ignored", ["system", "limit"])
def test_drops_noise_types(ignored):
    assert build_catchup([_msg(1, ignored, "bruit")]) == []


@pytest.mark.parametrize(
    "type_, content, cap, prefix",
    [
        ("tool_use", json.dumps({"tool": "Bash", "input": {"command": "x" * 5000}}), 300, "[appel Bash] "),
        ("tool_result", json.dumps({"output": "y" * 5000}), 1000, "[résultat] "),
    ],
)
def test_caps_tool_payloads(type_, content, cap, prefix):
    rendered = build_catchup([_msg(1, type_, content)])[0]["content"]

    max_overhead = len(prefix) + CLIP_MARKER_OVERHEAD
    assert len(rendered) < cap + max_overhead
    assert "tronqué" in rendered


def test_caps_total_size_keeping_the_tail():
    msgs = [_msg(i, "assistant", f"bloc {i} " + "z" * 900) for i in range(60)]
    msgs.append(_msg(999, "user", "DERNIER MESSAGE"))
    result = build_catchup(msgs)

    total = sum(len(e["content"]) for e in result)
    assert total <= TOTAL_CAP
    assert "DERNIER MESSAGE" in result[-1]["content"]


def test_tolerates_non_json_tool_content():
    assert build_catchup([_msg(1, "tool_use", "pas du json")])[0]["content"]


def test_oversized_single_entry_is_clipped_to_its_tail():
    """Une entrée unique plus longue que le plafond est tronquée, pas jetée — et on garde sa fin,
    la plus proche du tour à jouer."""
    long_answer = "DEBUT " + "x" * (TOTAL_CAP + 10000) + " FIN"
    msgs = [_msg(1, "user", "question courte"), _msg(2, "assistant", long_answer)]
    result = build_catchup(msgs)

    assert len(result) == 1
    assert sum(len(e["content"]) for e in result) <= TOTAL_CAP
    assert "tronqué" in result[-1]["content"]
    assert result[-1]["content"].endswith(" FIN")
    assert "DEBUT" not in result[-1]["content"]


@pytest.mark.parametrize(
    "wrong_shape",
    [
        json.dumps([1, 2, 3]),
        json.dumps(42),
        json.dumps("string"),
    ],
)
def test_valid_json_but_wrong_shape_degrades_gracefully(wrong_shape):
    """Valid JSON that isn't an object must not crash."""
    result = build_catchup([_msg(1, "tool_result", wrong_shape)])

    assert len(result) > 0
    assert "résultat" in result[0]["content"]
