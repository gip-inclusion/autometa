"""Every agent declared in the repository (agents/<slug>.yaml, .md, and its files' initial values) is accepted."""

from pathlib import Path

import pytest
import yaml

from lib import agent_config
from web import config

AGENTS_DIR = config.BASE_DIR / "agents"
CONSIGNE = "Tu es chargé de la veille des marchés publics.\n"


def initial_files(path: Path) -> dict[str, str]:
    """Why: agents/<slug>/<nom> is the initial value of the declared file <nom>, given to proposer --fichier."""
    folder = path.with_suffix("")
    return {f.name: f.read_text() for f in sorted(folder.iterdir())} if folder.is_dir() else {}


def repo_errors(path: Path) -> list[str]:
    """Every error of a repository agent: its configuration, its slug, its job prompt, its files' initial values."""
    try:
        doc = agent_config.parse(path.read_text())
    except yaml.YAMLError as exc:
        return [f"{path.name} : YAML illisible : {exc}"]
    found = agent_config.validate(doc)
    if isinstance(doc, dict):
        found += agent_config.initial_errors(initial_files(path), doc.get("fichiers", []))
    if isinstance(doc, dict) and "slug" in doc and doc["slug"] != path.stem:
        found.append(f"slug : {doc['slug']!r} diffère du nom du fichier, attendu {path.stem!r}.")
    consigne = path.with_suffix(".md")
    if not consigne.is_file() or not consigne.read_text().strip():
        found.append(f"consigne : {consigne.name} absente ou vide, la consigne du job vit à côté de la configuration.")
    return [f"{path.name} : {error}" for error in found]


def agent_file(directory: Path, slug: str, destination: str = "bizdev.marche", mode: str = "ombre") -> Path:
    path = directory / f"{slug}.yaml"
    path.write_text(
        f"format: pdi.agent/1\nslug: {slug}\ntitre: Veille des marchés\n"
        "mission: Repérer les avis de marchés publics utiles à l'équipe bizdev.\n"
        f"points_de_contact:\n  - id: {destination}\n    mode: {mode}\n"
    )
    return path


@pytest.mark.parametrize("path", sorted(AGENTS_DIR.glob("*.yaml")), ids=lambda p: p.stem)
def test_dod_3_every_agent_of_the_repository_is_accepted(path):
    assert repo_errors(path) == []


def test_dod_3_the_check_finds_the_repository_agents():
    assert "veille-boamp" in [p.stem for p in AGENTS_DIR.glob("*.yaml")]


@pytest.mark.parametrize(
    ("destination", "mode", "field", "message"),
    [
        ("bizdev.marches", "ombre", "id", "'bizdev.marches' n'est pas une destination"),
        ("bizdev.marche", "reel", "mode", "le mode reel sur 'bizdev.marche' n'est pas ouvert à cet agent"),
        ("bizdev.marche", "direct", "mode", "'direct' inconnu"),
    ],
)
def test_dod_3_a_wrong_destination_or_mode_is_refused(tmp_path, destination, mode, field, message):
    path = agent_file(tmp_path, "veille-marches", destination, mode)
    path.with_suffix(".md").write_text(CONSIGNE)
    [error] = repo_errors(path)
    assert error.startswith(f"veille-marches.yaml : points_de_contact[0].{field} : ")
    assert message in error


def test_dod_3_a_slug_other_than_the_file_name_is_refused(tmp_path):
    renamed = agent_file(tmp_path, "veille-marches").rename(tmp_path / "veille-boamp.yaml")
    renamed.with_suffix(".md").write_text(CONSIGNE)
    assert repo_errors(renamed) == [
        "veille-boamp.yaml : slug : 'veille-marches' diffère du nom du fichier, attendu 'veille-boamp'."
    ]


@pytest.mark.parametrize("consigne", [None, "  \n"])
def test_dod_3_an_agent_without_a_job_prompt_is_refused(tmp_path, consigne):
    path = agent_file(tmp_path, "veille-marches")
    if consigne is not None:
        path.with_suffix(".md").write_text(consigne)
    assert repo_errors(path) == [
        "veille-marches.yaml : consigne : veille-marches.md absente ou vide, "
        "la consigne du job vit à côté de la configuration."
    ]


def agent_with_initial_file(directory: Path, fichiers: str, contenu: str) -> Path:
    path = agent_file(directory, "veille-marches")
    path.write_text(path.read_text() + fichiers)
    path.with_suffix(".md").write_text(CONSIGNE)
    (directory / "veille-marches").mkdir()
    (directory / "veille-marches" / "regles.md").write_text(contenu)
    return path


def test_an_initial_value_for_an_undeclared_file_is_refused(tmp_path):
    path = agent_with_initial_file(tmp_path, "", "# Règles")
    assert repo_errors(path) == [
        "veille-marches.yaml : fichier initial regles.md : pas un fichier déclaré de l'agent, fichiers : aucun."
    ]


def test_an_oversized_initial_value_is_refused(tmp_path):
    path = agent_with_initial_file(tmp_path, "fichiers: [regles.md]\n", "x" * 100_001)
    assert repo_errors(path) == ["veille-marches.yaml : fichier initial regles.md : 100001 caractères, 100000 au plus."]


def test_the_boamp_agent_rules_are_its_declared_file():
    assert list(initial_files(AGENTS_DIR / "veille-boamp.yaml")) == ["regles.md"]


def test_dod_3_unreadable_yaml_is_refused(tmp_path):
    path = tmp_path / "veille-marches.yaml"
    path.write_text("slug: a\nslug: b\n")
    [error] = repo_errors(path)
    assert error.startswith("veille-marches.yaml : YAML illisible : ")
    assert "clé en double : slug" in error
