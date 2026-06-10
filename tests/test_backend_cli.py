"""Tests specific to the CLI backend."""


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
    mocker.patch("web.agents.cli.config.CONTAINER_ENV", False)
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


def test_tool_permission_args_blocks_askuserquestion(mocker):
    from web import config
    from web.agents.cli import CLIBackend

    mocker.patch.object(config, "CONTAINER_ENV", False)
    mocker.patch.object(config, "ALLOWED_TOOLS", "Read,Bash(python:*)")
    mocker.patch.object(config, "DISALLOWED_TOOLS", "AskUserQuestion")
    args = CLIBackend()._tool_permission_args()

    assert args == ["--allowedTools", "Read,Bash(python:*)", "--disallowedTools", "AskUserQuestion"]


def test_tool_permission_args_blocks_askuserquestion_in_container(mocker):
    from web import config
    from web.agents.cli import CLIBackend

    mocker.patch.object(config, "CONTAINER_ENV", True)
    mocker.patch.object(config, "DISALLOWED_TOOLS", "AskUserQuestion")
    args = CLIBackend()._tool_permission_args()

    assert "--dangerously-skip-permissions" in args
    assert args[-2:] == ["--disallowedTools", "AskUserQuestion"]
