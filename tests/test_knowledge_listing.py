"""Listing de la base de connaissances — web/helpers.list_knowledge_files."""

from web import helpers


def test_knowledge_listing_survives_a_hidden_parent_directory(tmp_path, monkeypatch):
    """Un dépôt qui vit sous un répertoire caché (worktree) ne doit pas vider la base de connaissances."""
    root = tmp_path / ".claude" / "worktrees" / "essai" / "knowledge"
    (root / "sites").mkdir(parents=True)
    (root / "sites" / "emplois.md").write_text("# Emplois")
    (root / ".cache").mkdir()
    (root / ".cache" / "ignore.md").write_text("# caché")
    monkeypatch.setattr(helpers, "KNOWLEDGE_ROOT", root)

    sections = helpers.list_knowledge_files()

    assert list(sections) == ["sites"]
