"""Base de connaissances — sa liste et le chemin d'une fiche demandée (web/helpers)."""

import pytest

from web import helpers


def test_knowledge_listing_survives_a_hidden_parent_directory(tmp_path, monkeypatch):
    """Un dépôt qui vit sous un répertoire caché (worktree) ne doit pas vider la base de connaissances."""
    root = tmp_path / ".claude" / "worktrees" / "essai" / "knowledge"
    (root / "sites").mkdir(parents=True)
    (root / "sites" / "plateforme-ex-emplois.md").write_text("# Plateforme de l'inclusion (ex-Emplois)")
    (root / ".cache").mkdir()
    (root / ".cache" / "ignore.md").write_text("# caché")
    monkeypatch.setattr(helpers, "KNOWLEDGE_ROOT", root)

    sections = helpers.list_knowledge_files()

    assert list(sections) == ["sites"]


@pytest.fixture
def knowledge(tmp_path, mocker):
    """Une base de connaissances d'une fiche, à côté d'un fichier qui n'en fait pas partie."""
    root = tmp_path / "knowledge"
    (root / "sites").mkdir(parents=True)
    (root / "sites" / "dora.md").write_text("# Dora")
    (root / "sites" / "notes.txt").write_text("notes")
    (tmp_path / "secret.md").write_text("# Secret")
    (tmp_path / "knowledge-prive").mkdir()
    (tmp_path / "knowledge-prive" / "secret.md").write_text("# Secret")
    mocker.patch.object(helpers, "KNOWLEDGE_ROOT", root)
    return root


def test_a_knowledge_file_is_found_at_its_path_under_the_root(knowledge):
    assert helpers.validate_knowledge_path("sites/dora.md") == (knowledge / "sites" / "dora.md").resolve()


@pytest.mark.parametrize(
    "asked",
    [
        "",
        "../secret.md",
        "sites/../../secret.md",
        "../knowledge-prive/secret.md",
        "/etc/passwd",
        "{root}/sites/dora.md",
        "%2e%2e%2fsecret.md",
        "..%2fsecret.md",
        "sites%2fdora.md",
        "sites\\dora.md",
        "sites//dora.md",
        "sites/.dora.md",
        "sites/notes.txt",
        "sites/absente.md",
        "sites",
        "sites/dora.md\x00",
    ],
)
def test_a_path_that_names_no_file_of_the_knowledge_base_is_refused(knowledge, asked):
    assert helpers.validate_knowledge_path(asked.format(root=knowledge)) is None


@pytest.mark.parametrize("target", ["secret.md", "knowledge-prive/secret.md"])
def test_a_link_inside_the_knowledge_base_cannot_lead_out_of_it(knowledge, target):
    (knowledge / "sites" / "lien.md").symlink_to(knowledge.parent / target)
    (knowledge / "dehors").symlink_to(knowledge.parent, target_is_directory=True)

    assert helpers.validate_knowledge_path("sites/lien.md") is None
    assert helpers.validate_knowledge_path(f"dehors/{target}") is None


def test_a_link_that_stays_inside_the_knowledge_base_is_followed(knowledge):
    (knowledge / "sites" / "alias.md").symlink_to(knowledge / "sites" / "dora.md")

    assert helpers.validate_knowledge_path("sites/alias.md") == (knowledge / "sites" / "dora.md").resolve()
