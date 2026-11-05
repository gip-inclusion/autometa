import pytest

from lib import agent_files
from tests.test_agent_delivery import FakeStore

SLUG = "veille-backlog"


@pytest.fixture
def store(mocker):
    fake = FakeStore()
    mocker.patch("lib.agent_delivery.s3.agents", fake)
    return fake


def test_dod_16_every_write_is_a_new_version_and_the_history_keeps_them_all(store, caplog):
    assert agent_files.read(SLUG, "notes.md") == {"nom": "notes.md", "version": 0, "contenu": ""}
    with caplog.at_level("INFO"):
        assert agent_files.write_version(SLUG, "notes.md", "Première idée.", "run r1") == 1
        assert agent_files.write_version(SLUG, "notes.md", "Première idée.", "run r1") == 1
        assert agent_files.write_version(SLUG, "notes.md", "Idée revue.", "run r2") == 2
    assert [(v["version"], v["origine"], v["taille"]) for v in agent_files.history(SLUG, "notes.md")] == [
        (1, "run r1", 14),
        (2, "run r2", 11),
    ]
    assert agent_files.read(SLUG, "notes.md")["contenu"] == "Idée revue."
    assert agent_files.read(SLUG, "notes.md", 1)["contenu"] == "Première idée."
    assert "Idée" not in caplog.text
    assert "notes.md version 2, 11 caractères" in caplog.text


def test_dod_16_two_versions_compare_as_a_unified_diff(store):
    agent_files.write_version(SLUG, "notes.md", "a\nb\n", "run r1")
    agent_files.write_version(SLUG, "notes.md", "a\nc\n", "run r2")
    assert agent_files.compare(SLUG, "notes.md", 1, 2).splitlines() == [
        "--- notes.md version 1",
        "+++ notes.md version 2",
        "@@ -1,2 +1,2 @@",
        " a",
        "-b",
        "+c",
    ]


@pytest.mark.parametrize("version", [-1, 3])
def test_dod_16_an_unknown_version_is_refused(store, version):
    agent_files.write_version(SLUG, "notes.md", "a", "run r1")
    with pytest.raises(ValueError, match=f"version {version} inconnue, versions 1 à 1"):
        agent_files.read(SLUG, "notes.md", version)


def test_dod_16_a_file_beyond_its_size_is_refused(store):
    with pytest.raises(ValueError, match="100000 au plus"):
        agent_files.write_version(SLUG, "notes.md", "x" * 100_001, "run r1")
    assert agent_files.history(SLUG, "notes.md") == []


def test_dod_16_entries_are_appended_and_an_entry_with_a_known_key_is_replaced_in_place(store):
    agent_files.write_version(SLUG, "tickets.md", "# Tickets\n\n", "run r0")
    agent_files.add_entries(SLUG, "tickets.md", [("export", "Export", "v1"), ("carte", "Carte", "texte")], "run r1")
    agent_files.add_entries(
        SLUG, "tickets.md", [("export", "Export CSV", "v2\n"), ("relance", "Relance", "r")], "run r2"
    )
    assert agent_files.read(SLUG, "tickets.md")["contenu"] == (
        "# Tickets\n\n"
        "<!-- entree: export -->\n## Export CSV\n\nv2\n\n"
        "<!-- entree: carte -->\n## Carte\n\ntexte\n\n"
        "<!-- entree: relance -->\n## Relance\n\nr\n\n"
    )
    assert len(agent_files.history(SLUG, "tickets.md")) == 3


@pytest.mark.parametrize(
    ("fichiers", "fed", "expected"),
    [
        ("notes", set(), "fichiers : attendu une liste"),
        ([{"nom": "notes.md"}], set(), "attendu exactement nom et contenu"),
        ([{"nom": "notes.md", "contenu": 3}], set(), "attendu exactement nom et contenu"),
        ([{"nom": "autre.md", "contenu": "x"}], set(), "'autre.md' n'est pas un fichier déclaré"),
        ([{"nom": "notes.md", "contenu": "x" * 100_001}], set(), "100000 au plus"),
        ([{"nom": "notes.md", "contenu": "a"}, {"nom": "notes.md", "contenu": "b"}], set(), "rendu deux fois"),
        ([{"nom": "notes.md", "contenu": "a"}], {"notes.md"}, "reçoit aussi des productions"),
    ],
)
def test_dod_16_a_run_handing_back_wrong_files_is_refused(fichiers, fed, expected):
    found = agent_files.output_errors(fichiers, ["notes.md"], fed)
    assert any(expected in e for e in found), found


def test_dod_16_declared_files_handed_back_once_are_accepted():
    assert agent_files.output_errors([{"nom": "notes.md", "contenu": "x"}], ["notes.md", "b.md"], {"b.md"}) == []
