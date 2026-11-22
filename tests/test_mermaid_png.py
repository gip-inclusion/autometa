"""Rendu d'un graphique Mermaid en PNG : un processus à part, un seul à la fois, arrêté s'il s'éternise."""

import signal
import subprocess

import pytest

from lib import mermaid_draw, mermaid_png

PNG = b"\x89PNG\r\n\x1a\n...."


def child(mocker, returncode=0, out=PNG, err=b""):
    process = mocker.MagicMock(returncode=returncode, pid=4242)
    process.communicate.return_value = (out, err)
    return mocker.patch.object(mermaid_png.subprocess, "Popen", return_value=process)


def test_a_chart_is_drawn_by_a_child_process_given_its_source_on_stdin(mocker):
    popen = child(mocker)

    assert mermaid_png.render("pie title Parts") == PNG

    command = popen.call_args.args[0]
    assert command[1:] == ["-m", "lib.mermaid_draw"]
    assert popen.call_args.kwargs["start_new_session"] is True
    popen.return_value.communicate.assert_called_once_with(b"pie title Parts", timeout=20)


@pytest.mark.parametrize(
    "returncode,out",
    [(1, b""), (0, b""), (0, b"<html>pas une image</html>")],
    ids=["child failed", "nothing drawn", "not a PNG"],
)
def test_a_chart_that_could_not_be_drawn_gives_nothing_and_says_why(mocker, caplog, returncode, out):
    child(mocker, returncode, out, err=b"Error: Parse error on line 1")

    assert mermaid_png.render("pas un graphique") is None
    assert "Parse error on line 1" in caplog.text


def test_a_render_that_takes_too_long_is_killed_with_its_browser(mocker, caplog):
    popen = child(mocker)
    popen.return_value.communicate.side_effect = [subprocess.TimeoutExpired("draw", 20), (b"", b"")]
    killpg = mocker.patch.object(mermaid_png.os, "killpg")

    assert mermaid_png.render("graph TD; A-->B") is None

    killpg.assert_called_once_with(4242, signal.SIGKILL)
    assert "arrêté après 20 s" in caplog.text
    assert mermaid_png.rendering.acquire(blocking=False)
    mermaid_png.rendering.release()


def test_only_one_chart_is_drawn_at_a_time_and_a_second_one_gives_up(mocker, caplog):
    popen = child(mocker)
    lock = mocker.patch.object(mermaid_png, "rendering")
    lock.acquire.return_value = False

    assert mermaid_png.render("graph TD; A-->B") is None

    lock.acquire.assert_called_once_with(timeout=30)
    popen.assert_not_called()
    lock.release.assert_not_called()
    assert "un autre rendu est en cours" in caplog.text


@pytest.mark.parametrize(
    "url,let_through",
    [
        (mermaid_draw.MERMAID_URL, True),
        ("https://cdn.jsdelivr.net/npm/mermaid@11.17.2/dist/other.js", False),
        ("https://evil.example/collect?d=1", False),
        ("http://169.254.169.254/latest/meta-data", False),
    ],
)
def test_the_drawing_page_loads_the_mermaid_script_and_nothing_else(mocker, url, let_through):
    route = mocker.MagicMock()
    route.request.url = url

    mermaid_draw.only_mermaid(route)

    assert route.continue_.called is let_through
    assert route.abort.called is not let_through
