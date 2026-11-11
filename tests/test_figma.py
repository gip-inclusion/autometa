import pytest

from lib import figma

KEY = "A" * 22
BRANCH = "B" * 22


def node(type_, name="n", children=None, text=None, visible=True, width=None, id_="1:1"):
    n = {"id": id_, "type": type_, "name": name, "children": children or []}
    if text is not None:
        n["characters"] = text
    if not visible:
        n["visible"] = False
    if width is not None:
        n["absoluteBoundingBox"] = {"width": width, "height": 100}
    return n


@pytest.mark.parametrize(
    ("url", "expected"),
    [
        (f"https://www.figma.com/design/{KEY}/Maquette?node-id=4524-5330&t=x", figma.FigmaLink(KEY, "4524:5330")),
        (f"https://www.figma.com/design/{KEY}/Maquette?node-id=12%3A34", figma.FigmaLink(KEY, "12:34")),
        (f"https://www.figma.com/board/{KEY}/Notifications?t=x", figma.FigmaLink(KEY, None)),
        (f"https://www.figma.com/design/{KEY}/branch/{BRANCH}/x?node-id=1-5", figma.FigmaLink(BRANCH, "1:5")),
        (f"https://www.figma.com/design/{KEY}/x/branch/{BRANCH}/x?node-id=1-5", figma.FigmaLink(BRANCH, "1:5")),
        ("https://exemple.fr/design/abc", None),
    ],
)
def test_parse_link(url, expected):
    assert figma.parse_link(url) == expected


def test_dod_1_visible_texts_ignores_hidden_layers():
    frame = node(
        "FRAME",
        children=[
            node("TEXT", text="Titre"),
            node("GROUP", visible=False, children=[node("TEXT", text="Ancien texte")]),
            node("TEXT", text="  "),
            node("TEXT", text="Bouton"),
        ],
    )
    assert figma.visible_texts(frame) == ["Titre", "Bouton"]


@pytest.mark.parametrize(
    ("root", "names"),
    [
        (node("FRAME", name="Écran"), ["Écran"]),
        (
            node("SECTION", name="S", children=[node("FRAME", name="Vue pro"), node("FRAME", name="Vue candidat")]),
            ["Vue pro", "Vue candidat"],
        ),
        (node("CANVAS", children=[node("FRAME", name=str(i)) for i in range(8)]), ["0", "1", "2", "3", "4", "5"]),
        (
            node("CANVAS", children=[node("FRAME", name="masqué", visible=False), node("FRAME", name="visible")]),
            ["visible"],
        ),
    ],
)
def test_pick_frames(root, names):
    assert [c["name"] for c in figma.pick_frames(root)] == names


def test_dod_1_read_frames_without_node_reads_nothing(mocker):
    call = mocker.patch.object(figma, "call_api")
    assert figma.read_frames(figma.FigmaLink(KEY, None)) == []
    call.assert_not_called()


def test_dod_1_read_frames_gives_name_texts_and_width(mocker):
    document = node(
        "SECTION",
        children=[
            node(
                "FRAME",
                name="Choix 1",
                id_="2:2",
                width=1435,
                children=[node("TEXT", text="Accepter la candidature")],
            )
        ],
    )
    mocker.patch.object(figma, "call_api", return_value={"nodes": {"4:5": {"document": document}}})
    frames = figma.read_frames(figma.FigmaLink(KEY, "4:5"))
    assert frames == [figma.Frame(id="2:2", name="Choix 1", texts=["Accepter la candidature"], width=1435)]


@pytest.mark.parametrize(("width", "scale"), [(3200, 0.5), (800, 1.0), (0, 1.0)])
def test_dod_1_export_images_reduces_the_width_and_writes_the_png(mocker, tmp_path, width, scale):
    call = mocker.patch.object(figma, "call_api", return_value={"images": {"2:2": "https://rendu/2-2.png"}})
    mocker.patch.object(figma.httpx, "get", return_value=mocker.Mock(content=b"PNG"))
    frame = figma.Frame(id="2:2", name="Choix 1", texts=[], width=width)
    images = figma.export_images(figma.FigmaLink(KEY, "4:5"), [frame], tmp_path)
    assert call.call_args.args[1]["scale"] == scale
    assert images == {"2:2": tmp_path / "frame-1.png"}
    assert (tmp_path / "frame-1.png").read_bytes() == b"PNG"


def test_dod_1_export_images_skips_an_unrendered_frame(mocker, tmp_path):
    call = mocker.patch.object(
        figma, "call_api", return_value={"images": {"2:2": None, "2:3": "https://rendu/2-3.png"}}
    )
    mocker.patch.object(figma.httpx, "get", return_value=mocker.Mock(content=b"PNG"))
    frames = [figma.Frame(id=i, name=i, texts=[], width=800) for i in ("2:2", "2:3")]
    images = figma.export_images(figma.FigmaLink(KEY, "4:5"), frames, tmp_path)
    assert images == {"2:3": tmp_path / "frame-2.png"}
    assert not (tmp_path / "frame-1.png").exists()
    call.assert_called_once()
    assert call.call_args.args[1]["ids"] == "2:2,2:3"


@pytest.mark.parametrize("response", [{"nodes": {}}, {"nodes": {"4:5": None}}])
def test_dod_1_read_frames_missing_node_returns_nothing(mocker, response):
    mocker.patch.object(figma, "call_api", return_value=response)
    assert figma.read_frames(figma.FigmaLink(KEY, "4:5")) == []


def test_call_api_sends_the_plan_token(mocker):
    mocker.patch.object(figma.config, "FIGMA_ACCESS_TOKEN", "jeton")
    get = mocker.patch.object(figma.httpx, "get", return_value=mocker.Mock(json=lambda: {"ok": True}))
    assert figma.call_api("files/x/nodes", {"ids": "1:2"}) == {"ok": True}
    assert get.call_args.kwargs["headers"] == {"X-Figma-Token": "jeton"}
    assert get.call_args.kwargs["timeout"] == figma.TIMEOUT
