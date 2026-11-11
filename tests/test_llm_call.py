"""Tests for the one-shot Claude CLI helper used for short completions."""

import subprocess
import threading
import time

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
    assert kwargs["cwd"] == str(mod.CWD)
    assert kwargs["timeout"] == 12.5
    assert kwargs["capture_output"] is True
    assert kwargs["text"] is True
    assert mod.CWD.is_dir()


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


def test_llm_call_runs_one_short_cli_at_a_time(mocker):
    """Titre et tags partent ensemble au premier message : deux CLI de plus à côté de l'agent (code -9 de #278)."""
    running, peak = [], []

    def run(*args, **kwargs):
        running.append(1)
        peak.append(len(running))
        time.sleep(0.05)
        running.pop()
        return _completed(stdout="ok")

    mocker.patch("subprocess.run", side_effect=run)
    threads = [threading.Thread(target=llm_call, args=("titre",)) for _ in range(3)]
    for thread in threads:
        thread.start()
    for thread in threads:
        thread.join()
    assert max(peak) == 1
    assert len(peak) == 3


def test_llm_call_gives_up_when_another_short_cli_holds_the_slot(mocker):
    run = mocker.patch("subprocess.run")
    with mod.ONE_AT_A_TIME, pytest.raises(LLMError, match="busy"):
        llm_call("titre", timeout=0.01)
    run.assert_not_called()
