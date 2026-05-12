"""Tests for the one-shot Claude CLI helper used for short completions."""

import subprocess

import pytest

from web import config
from web import llm_call as mod
from web.llm_call import llm_call
from web.llm_errors import LLMError


def _completed(stdout: str = "", stderr: str = "", returncode: int = 0) -> subprocess.CompletedProcess:
    return subprocess.CompletedProcess(args=[], returncode=returncode, stdout=stdout, stderr=stderr)


def test_llm_call_returns_stripped_stdout(mocker):
    mocker.patch("subprocess.run", return_value=_completed(stdout="  Hello world  \n"))

    assert llm_call("prompt") == "Hello world"


def test_llm_call_defaults_to_config_model_and_dedicated_cwd(mocker):
    run = mocker.patch("subprocess.run", return_value=_completed(stdout="ok"))

    llm_call("ping", timeout=12.5)

    args, kwargs = run.call_args
    cmd = args[0]
    assert cmd[1:] == ["--print", "--model", config.LLM_MODEL, "-p", "ping"]
    assert kwargs["cwd"] == str(mod._CWD)
    assert kwargs["timeout"] == 12.5
    assert kwargs["capture_output"] is True
    assert kwargs["text"] is True
    assert mod._CWD.is_dir()


@pytest.mark.parametrize("model", ["claude-sonnet-4-6", "claude-opus-4-7"])
def test_llm_call_honors_model_override(mocker, model):
    run = mocker.patch("subprocess.run", return_value=_completed(stdout="ok"))

    llm_call("prompt", model=model)

    assert run.call_args[0][0][1:4] == ["--print", "--model", model]


@pytest.mark.parametrize(
    "exc,expected_msg",
    [
        (subprocess.TimeoutExpired(cmd="claude", timeout=60), "Claude CLI timed out"),
        (OSError("not found"), "Claude CLI failed: not found"),
    ],
)
def test_llm_call_translates_subprocess_failures(mocker, exc, expected_msg):
    mocker.patch("subprocess.run", side_effect=exc)

    with pytest.raises(LLMError, match=expected_msg):
        llm_call("prompt")


@pytest.mark.parametrize(
    "stderr,expected_msg",
    [
        ("boom\n", "boom"),
        ("", "Claude CLI error"),
    ],
)
def test_llm_call_raises_on_nonzero_exit(mocker, stderr, expected_msg):
    mocker.patch("subprocess.run", return_value=_completed(stderr=stderr, returncode=2))

    with pytest.raises(LLMError, match=expected_msg):
        llm_call("prompt")
