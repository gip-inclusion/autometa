"""Tests specific to the CLI backend."""

import asyncio
import concurrent.futures

import pytest

from web import config
from web.agents.cli import CLIBackend
from web.environment import Environment


class FakeStream:
    async def readline(self):
        return b""


class FakeProc:
    pid = 123
    returncode = 0
    stdout = FakeStream()
    stderr = FakeStream()

    async def wait(self):
        return 0


def patch_cli(mocker, tmp_path, *, env=Environment.DEV, allowed_tools="", session_path=None) -> dict:
    """Run the CLI backend against a process that exits at once; the returned dict receives its command line."""
    captured = {}

    async def fake_exec(*args, **kwargs):
        captured["cmd"] = list(args)
        return FakeProc()

    mocker.patch("web.agents.cli.asyncio.create_subprocess_exec", side_effect=fake_exec)
    mocker.patch("web.agents.cli.session_sync.get_session_path", return_value=session_path or tmp_path / "absent.jsonl")
    mocker.patch("web.agents.cli.session_sync.upload_session")
    mocker.patch("web.agents.cli.build_system_prompt", return_value="")
    mocker.patch("web.agents.cli.config.ADDITIONAL_DIRS", [])
    mocker.patch("web.agents.cli.config.ENV", env)
    mocker.patch("web.agents.cli.config.ALLOWED_TOOLS", allowed_tools)
    mocker.patch("web.agents.cli.config.CLAUDE_CLI", "claude")
    mocker.patch("web.agents.cli.config.BASE_DIR", str(tmp_path))
    return captured


def run_turn(**kwargs) -> None:
    async def consume():
        async for _ in CLIBackend().send_message("c1", **kwargs):
            pass

    asyncio.run(consume())


def test_build_env_removes_api_key(mocker):
    backend = CLIBackend()
    mocker.patch.dict("os.environ", {"ANTHROPIC_API_KEY": "sk-secret", "HOME": "/x"}, clear=True)
    env = backend._build_env()

    assert "ANTHROPIC_API_KEY" not in env
    assert env["HOME"] == "/x"


def test_extra_cmd_args_empty():
    backend = CLIBackend()
    assert backend._extra_cmd_args() == []


def test_dash_prompt_is_passed_after_double_dash_on_resume(mocker, tmp_path):
    """A '-'-leading prompt must be passed after '--' so the CLI keeps it positional."""
    session_file = tmp_path / "sess.jsonl"
    session_file.write_text("{}")
    captured = patch_cli(mocker, tmp_path, session_path=session_file)

    run_turn(message="- une question", history=[], session_id="sess")

    cmd = captured["cmd"]
    assert cmd[-3:] == ["-p", "--", "- une question"], cmd


@pytest.mark.parametrize(
    ("env_value", "expects_skip"),
    [(Environment.PROD, True), (Environment.STAGING, True), (Environment.REVIEW, True), (Environment.DEV, False)],
)
def test_skip_permissions_on_servers_only(mocker, tmp_path, env_value, expects_skip):
    captured = patch_cli(mocker, tmp_path, env=env_value, allowed_tools="Bash")

    run_turn(message="hello", history=[])

    cmd = captured["cmd"]
    assert ("--dangerously-skip-permissions" in cmd) is expects_skip
    assert ("--allowedTools" in cmd) is not expects_skip


# AskUserQuestion never renders in the autometa UI, so app-started agents (CLIBackend)
# always block it — on servers and dev alike, regardless of the skip-permissions gating.
@pytest.mark.parametrize("env_value", [Environment.PROD, Environment.DEV])
def test_app_agents_always_block_askuserquestion(mocker, env_value):
    mocker.patch.object(config, "ENV", env_value)
    mocker.patch.object(config, "ALLOWED_TOOLS", "Read,Bash(python:*)")
    mocker.patch.object(config, "DISALLOWED_TOOLS", "AskUserQuestion")
    args = CLIBackend()._tool_permission_args()

    assert args[-2:] == ["--disallowedTools", "AskUserQuestion"]


def run_turn_watching_the_upload(mocker, tmp_path) -> dict:
    """Run one turn whose session upload checks that the event loop still answers, and log when each part ends."""
    session_file = tmp_path / "sess.jsonl"
    session_file.write_text("{}")
    patch_cli(mocker, tmp_path, session_path=session_file)
    state = {"loop_free": False, "events": []}

    def upload(session_id):
        # Why: a coroutine submitted from here only runs if the loop is not stuck inside this very call.
        probe = asyncio.run_coroutine_threadsafe(asyncio.sleep(0), state["loop"])
        state["loop_free"] = bool(concurrent.futures.wait([probe], timeout=1).done)
        state["events"].append("session uploaded")

    mocker.patch("web.agents.cli.session_sync.upload_session", side_effect=upload)

    async def turn():
        state["loop"] = asyncio.get_running_loop()
        async for _ in CLIBackend().send_message("c1", "hello", [], session_id="sess"):
            pass
        state["events"].append("turn ended")

    asyncio.run(turn())
    return state


def test_session_upload_leaves_the_event_loop_free(mocker, tmp_path):
    assert run_turn_watching_the_upload(mocker, tmp_path)["loop_free"]


def test_turn_ends_only_after_its_session_is_uploaded(mocker, tmp_path):
    assert run_turn_watching_the_upload(mocker, tmp_path)["events"] == ["session uploaded", "turn ended"]
