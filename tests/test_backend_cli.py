"""Tests specific to the CLI backend."""

import pytest


def test_build_env_removes_api_key(mocker):
    from web.agents.cli import CLIBackend

    backend = CLIBackend()
    mocker.patch.dict("os.environ", {"ANTHROPIC_API_KEY": "sk-secret", "HOME": "/x"}, clear=True)
    env = backend._build_env()

    assert "ANTHROPIC_API_KEY" not in env
    assert env["HOME"] == "/x"


def test_extra_cmd_args_empty():
    from web.agents.cli import CLIBackend

    backend = CLIBackend()
    assert backend._extra_cmd_args() == []


def test_dash_prompt_is_passed_after_double_dash_on_resume(mocker, tmp_path):
    """A '-'-leading prompt must be passed after '--' so the CLI keeps it positional."""
    import asyncio

    from web.agents.cli import CLIBackend

    session_file = tmp_path / "sess.jsonl"
    session_file.write_text("{}")
    captured = {}

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

    async def fake_exec(*args, **kwargs):
        captured["cmd"] = list(args)
        return FakeProc()

    mocker.patch("web.agents.cli.asyncio.create_subprocess_exec", side_effect=fake_exec)
    mocker.patch("web.agents.cli.session_sync.get_session_path", return_value=session_file)
    mocker.patch("web.agents.cli.session_sync.upload_session")
    mocker.patch("web.agents.cli.build_system_prompt", return_value="")
    mocker.patch("web.agents.cli.config.ADDITIONAL_DIRS", [])
    mocker.patch("web.agents.cli.config.AUTOMETA_ENV", "dev")
    mocker.patch("web.agents.cli.config.ALLOWED_TOOLS", "")
    mocker.patch("web.agents.cli.config.CLAUDE_CLI", "claude")
    mocker.patch("web.agents.cli.config.BASE_DIR", str(tmp_path))

    backend = CLIBackend()

    async def _run():
        async for _ in backend.send_message("c1", "- une question", [], session_id="sess"):
            pass

    asyncio.run(_run())

    cmd = captured["cmd"]
    assert cmd[-3:] == ["-p", "--", "- une question"], cmd


@pytest.mark.parametrize(("env_value", "expects_skip"), [("live", True), ("dev", False)])
def test_skip_permissions_only_in_live_env(mocker, tmp_path, env_value, expects_skip):
    import asyncio

    from web.agents.cli import CLIBackend

    captured = {}

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

    async def fake_exec(*args, **kwargs):
        captured["cmd"] = list(args)
        return FakeProc()

    mocker.patch("web.agents.cli.asyncio.create_subprocess_exec", side_effect=fake_exec)
    mocker.patch("web.agents.cli.session_sync.get_session_path", return_value=tmp_path / "absent.jsonl")
    mocker.patch("web.agents.cli.session_sync.upload_session")
    mocker.patch("web.agents.cli.build_system_prompt", return_value="")
    mocker.patch("web.agents.cli.config.ADDITIONAL_DIRS", [])
    mocker.patch("web.agents.cli.config.AUTOMETA_ENV", env_value)
    mocker.patch("web.agents.cli.config.ALLOWED_TOOLS", "Bash")
    mocker.patch("web.agents.cli.config.CLAUDE_CLI", "claude")
    mocker.patch("web.agents.cli.config.BASE_DIR", str(tmp_path))

    backend = CLIBackend()

    async def _run():
        async for _ in backend.send_message("c1", "hello", []):
            pass

    asyncio.run(_run())

    cmd = captured["cmd"]
    assert ("--dangerously-skip-permissions" in cmd) is expects_skip
    assert ("--allowedTools" in cmd) is not expects_skip


# AskUserQuestion never renders in the autometa UI, so app-started agents (CLIBackend)
# always block it — in live and dev alike, regardless of the skip-permissions gating.
@pytest.mark.parametrize("env_value", ["live", "dev"])
def test_app_agents_always_block_askuserquestion(mocker, env_value):
    from web import config
    from web.agents.cli import CLIBackend

    mocker.patch.object(config, "AUTOMETA_ENV", env_value)
    mocker.patch.object(config, "ALLOWED_TOOLS", "Read,Bash(python:*)")
    mocker.patch.object(config, "DISALLOWED_TOOLS", "AskUserQuestion")
    args = CLIBackend()._tool_permission_args()

    assert args[-2:] == ["--disallowedTools", "AskUserQuestion"]
