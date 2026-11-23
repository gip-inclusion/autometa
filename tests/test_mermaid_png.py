"""Rendu d'un graphique Mermaid en PNG : merman-cli à part, police fournie, profil borné, image trop grande refusée."""

import struct
import subprocess

import pytest

from lib import mermaid_png


def png(width=800, height=600, weight=0):
    return b"\x89PNG\r\n\x1a\n\x00\x00\x00\rIHDR" + struct.pack(">II", width, height) + b"x" * weight


def merman(mocker, returncode=0, out=None, err=b""):
    drawn = mocker.MagicMock(returncode=returncode, stdout=png() if out is None else out, stderr=err)
    return mocker.patch.object(mermaid_png.subprocess, "run", return_value=drawn)


def test_a_chart_is_drawn_by_merman_given_its_source_on_stdin(mocker):
    run = merman(mocker)

    assert mermaid_png.render("pie title Parts") == png()

    command = run.call_args.args[0]
    assert command[:7] == [str(mermaid_png.MERMAN / "merman-cli"), "render", "-", "--format", "png", "--output", "-"]
    assert run.call_args.kwargs == {
        "input": b"pie title Parts",
        "capture_output": True,
        "timeout": 10,
        "check": False,
        "env": {},
    }


def options(command):
    return {name: value for name, value in zip(command, command[1:]) if name.startswith("--")}


def test_merman_measures_and_paints_with_the_supplied_font_and_no_system_font(mocker):
    run = merman(mocker)

    mermaid_png.render("pie title Parts")

    command = run.call_args.args[0]

    assert [command[i + 1] for i, word in enumerate(command) if word == "--font-file"] == [
        str(mermaid_png.MERMAN / "DejaVuSans.ttf"),
        str(mermaid_png.MERMAN / "DejaVuSans-Bold.ttf"),
    ]
    assert options(command)["--font-system"] == "off"


def test_merman_runs_bounded_for_untrusted_input_and_without_network(mocker):
    run = merman(mocker)

    mermaid_png.render("graph TD; A-->B")

    command = run.call_args.args[0]
    assert options(command)["--resource-profile"] == "constrained"
    assert options(command)["--operation-timeout-ms"] == "8000"
    assert (options(command)["--raster-max-width"], options(command)["--raster-max-height"]) == ("2400", "4000")
    assert not {"--allow-network", "--allow-private-network", "--icon-pack", "--raster-unbounded"} & set(command)


@pytest.mark.parametrize(
    "returncode,out",
    [(1, b""), (0, b""), (0, b"<html>pas une image</html>")],
    ids=["merman refused", "nothing drawn", "not a PNG"],
)
def test_a_chart_that_could_not_be_drawn_gives_nothing_and_says_why(mocker, caplog, returncode, out):
    merman(mocker, returncode, out, err=b"Diagram parse error (sankey): invalid character")

    assert mermaid_png.render("pas un graphique") is None
    assert "Diagram parse error (sankey)" in caplog.text


def test_a_render_that_takes_too_long_gives_nothing(mocker, caplog):
    merman(mocker).side_effect = subprocess.TimeoutExpired("merman-cli", 10)

    assert mermaid_png.render("graph TD; A-->B") is None
    assert "arrêté après 10 s" in caplog.text


def test_without_merman_installed_a_chart_gives_nothing_and_says_how_to_install_it(mocker, caplog):
    merman(mocker).side_effect = FileNotFoundError("merman-cli")

    assert mermaid_png.render("graph TD; A-->B") is None
    assert "`make merman` l'installe" in caplog.text


@pytest.mark.parametrize(
    "image",
    [png(height=4000), png(weight=3_000_000)],
    ids=["reduced to the height limit", "too heavy"],
)
def test_an_image_too_large_for_a_card_is_not_shown(mocker, caplog, image):
    merman(mocker, out=image)

    assert mermaid_png.render("sequenceDiagram") is None
    assert "Graphique non montré" in caplog.text


def test_a_wide_chart_reduced_to_the_width_limit_is_still_shown(mocker):
    merman(mocker, out=png(width=2400, height=300))

    assert mermaid_png.render("graph LR") == png(width=2400, height=300)


def test_merman_is_given_none_of_the_environment_of_the_server(mocker, monkeypatch):
    monkeypatch.setenv("DATABASE_URL", "postgresql://secret")
    run = merman(mocker)

    mermaid_png.render("graph TD; A-->B")

    assert run.call_args.kwargs["env"] == {}
