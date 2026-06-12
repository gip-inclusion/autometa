"""Tests for web/agents/cli.py — CLI backend event parsing and process lifecycle."""

import asyncio

import pytest

from web.agents.cli import CLIBackend


def make_backend():
    return CLIBackend()


def parse(event):
    return make_backend()._parse_events(event)


def test_parse_assistant_text_block():
    event = {"type": "assistant", "message": {"content": [{"type": "text", "text": "  Bonjour  "}]}}
    messages = parse(event)
    assert len(messages) == 1
    assert messages[0].type == "assistant"
    assert messages[0].content == "Bonjour"
    assert messages[0].raw == event


def test_parse_assistant_skips_empty_text():
    event = {"type": "assistant", "message": {"content": [{"type": "text", "text": "   "}]}}
    assert parse(event) == []


def test_parse_assistant_mixed_blocks_keeps_order():
    event = {
        "type": "assistant",
        "message": {
            "content": [
                {"type": "text", "text": "Je lance la requête"},
                {"type": "tool_use", "name": "Bash", "input": {"command": "ls"}},
            ]
        },
    }
    messages = parse(event)
    assert [m.type for m in messages] == ["assistant", "tool_use"]
    assert messages[1].content == {"tool": "Bash", "input": {"command": "ls"}}


@pytest.mark.parametrize("tool_key", ["tool", "name"])
def test_parse_top_level_tool_use(tool_key):
    event = {"type": "tool_use", tool_key: "Read", "input": {"file": "x"}}
    messages = parse(event)
    assert len(messages) == 1
    assert messages[0].type == "tool_use"
    assert messages[0].content == {"tool": "Read", "input": {"file": "x"}}


def test_parse_top_level_tool_result():
    messages = parse({"type": "tool_result", "tool": "Read", "output": "data"})
    assert len(messages) == 1
    assert messages[0].type == "tool_result"
    assert messages[0].content == {"tool": "Read", "output": "data"}


def test_parse_user_tool_result_block_truncates_id():
    event = {
        "type": "user",
        "message": {"content": [{"type": "tool_result", "tool_use_id": "toolu_0123456789", "content": "result"}]},
    }
    messages = parse(event)
    assert len(messages) == 1
    assert messages[0].type == "tool_result"
    assert messages[0].content == {"tool": "toolu_01", "output": "result"}


def test_parse_user_without_tool_result_yields_nothing():
    assert parse({"type": "user", "message": {"content": [{"type": "text", "text": "hi"}]}}) == []


@pytest.mark.parametrize(
    "event,expected_content",
    [
        ({"type": "system", "message": "init done"}, "init done"),
        ({"type": "system", "subtype": "init"}, "init"),
        ({"type": "error", "message": "boom"}, "boom"),
    ],
)
def test_parse_system_and_error_events(event, expected_content):
    messages = parse(event)
    assert len(messages) == 1
    assert messages[0].type == event["type"]
    assert messages[0].content == expected_content


def test_parse_result_event_keeps_usage_in_raw():
    event = {"type": "result", "subtype": "success", "usage": {"input_tokens": 12}}
    messages = parse(event)
    assert len(messages) == 1
    assert messages[0].type == "system"
    assert messages[0].content == "Completed: success"
    assert messages[0].raw["usage"] == {"input_tokens": 12}


@pytest.mark.parametrize("event", [{}, {"type": "unknown"}, {"type": None}])
def test_parse_unknown_event_yields_nothing(event):
    assert parse(event) == []


def test_build_prompt_without_history_is_message():
    assert make_backend()._build_prompt("salut", []) == "salut"


def test_build_prompt_formats_history_as_transcript():
    history = [
        {"role": "user", "content": "question"},
        {"role": "assistant", "content": "réponse"},
    ]
    prompt = make_backend()._build_prompt("suite", history)
    assert prompt == "User: question\n\nAssistant: réponse\n\nUser: suite"


def test_build_env_strips_api_key_and_sets_context(monkeypatch):
    monkeypatch.setenv("ANTHROPIC_API_KEY", "secret")
    env = make_backend()._build_env(conversation_id="c1", user_email="a@b.c")
    assert "ANTHROPIC_API_KEY" not in env
    assert env["AUTOMETA_CONVERSATION_ID"] == "c1"
    assert env["AUTOMETA_USER_EMAIL"] == "a@b.c"


def test_drain_stderr_keeps_tail_when_over_limit():
    async def _run():
        reader = asyncio.StreamReader()
        reader.feed_data(b"a" * 30 + b"\n" + b"end\n")
        reader.feed_eof()
        return await CLIBackend._drain_stderr(reader, max_bytes=10)

    out = asyncio.run(_run())
    assert out.endswith(b"end\n")
    assert len(out) <= 14


def test_cancel_without_process_returns_false():
    assert asyncio.run(make_backend().cancel("nope")) is False


def test_cancel_terminates_tracked_process(mocker):
    backend = make_backend()
    process = mocker.MagicMock()
    process.wait = mocker.AsyncMock()
    backend._processes["c1"] = process

    assert asyncio.run(backend.cancel("c1")) is True
    process.send_signal.assert_called_once()
    assert "c1" not in backend._processes


def test_is_running_reflects_returncode(mocker):
    backend = make_backend()
    process = mocker.MagicMock()
    process.returncode = None
    backend._processes["c1"] = process

    assert backend.is_running("c1") is True
    process.returncode = 0
    assert backend.is_running("c1") is False
    assert backend.is_running("unknown") is False


def make_stub_cli(tmp_path, body):
    script = tmp_path / "claude-stub"
    script.write_text(f"#!/bin/sh\n{body}\n")
    script.chmod(0o755)
    return str(script)


def collect_messages(backend, **kwargs):
    async def _run():
        return [
            m
            async for m in backend.send_message(
                conversation_id=kwargs.get("conversation_id", "c1"),
                message=kwargs.get("message", "salut"),
                history=kwargs.get("history", []),
                session_id=kwargs.get("session_id"),
            )
        ]

    return asyncio.run(_run())


@pytest.fixture
def stub_config(mocker, tmp_path):
    mocker.patch("web.agents.cli.build_system_prompt", return_value="")
    mocker.patch("web.agents.cli.config.ADDITIONAL_DIRS", [])
    mocker.patch("web.agents.cli.config.BASE_DIR", tmp_path)

    def _install(body):
        mocker.patch("web.agents.cli.config.CLAUDE_CLI", make_stub_cli(tmp_path, body))

    return _install


def test_send_message_streams_parsed_events(stub_config):
    stub_config(
        'echo \'{"type": "assistant", "message": {"content": [{"type": "text", "text": "Bonjour"}]}}\'\n'
        'echo \'{"type": "result", "subtype": "success"}\''
    )
    messages = collect_messages(make_backend())
    assert [m.type for m in messages] == ["assistant", "system"]
    assert messages[0].content == "Bonjour"
    assert messages[1].content == "Completed: success"


def test_send_message_wraps_non_json_line_as_system(stub_config):
    stub_config("echo 'plain text output'")
    messages = collect_messages(make_backend())
    assert messages[0].type == "system"
    assert messages[0].raw == {"raw_line": "plain text output"}


def test_send_message_yields_error_on_nonzero_exit(stub_config):
    stub_config("echo 'boom' >&2\nexit 3")
    messages = collect_messages(make_backend())
    assert messages[-1].type == "error"
    assert "Process exited with code 3" in messages[-1].content
    assert "boom" in messages[-1].content
    assert messages[-1].raw["code"] == 3
