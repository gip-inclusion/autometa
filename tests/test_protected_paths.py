"""Les couches qui protègent l'outillage recopient toutes la même liste : elle doit rester une."""

import json
import tomllib
from pathlib import Path

import pytest

REPO = Path(__file__).parent.parent
GATES = tomllib.loads((REPO / "gates.toml").read_text())["tool"]["protected_paths"]
DENY = json.loads((REPO / ".claude" / "settings.json").read_text())["permissions"]["deny"]
CODEOWNERS = (REPO / ".github" / "CODEOWNERS").read_text()


def chemins_denies():
    return {regle[len("Edit(/") : -1] for regle in DENY if regle.startswith("Edit(")}


def test_la_couche_1_couvre_exactement_les_chemins_declares():
    """Un chemin déclaré protégé mais absent du deny est une protection qui n'existe pas."""
    assert chemins_denies() == set(GATES["outillage"]) | set(GATES["artefacts"])


@pytest.mark.parametrize(
    "chemin",
    [".claude/hooks/", ".github/workflows/", "gates.toml", "Makefile", "scripts/", "lib/attestation.py"],
)
def test_la_couche_4_couvre_l_outillage(chemin):
    """CODEOWNERS est la seule couche hors du dépôt : ce qu'elle ne nomme pas n'est consenti par personne."""
    assert f"/{chemin}" in CODEOWNERS


@pytest.mark.parametrize(
    "commande",
    [
        "Bash(git push --force*)",
        "Bash(git commit * --no-verify*)",
        "Bash(git -c core.hooksPath=*)",
        "Bash(gh * --add-label*)",
    ],
)
def test_les_contournements_connus_restent_refuses(commande):
    """L'agent qui se pose lui-même un break-glass lève le seul gate qui vérifie ses preuves."""
    assert commande in DENY


def test_le_parcours_nominal_ne_demande_pas_d_autorisation():
    """Sans liste allow, chaque `make` et chaque `git` du parcours ouvre une invite au demandeur."""
    allow = json.loads((REPO / ".claude" / "settings.json").read_text())["permissions"]["allow"]

    for commande in ["Bash(make *)", "Bash(git commit*)", "Bash(gh pr create*)"]:
        assert commande in allow


def test_pyproject_reste_hors_de_la_couche_1():
    """Une fonctionnalité peut légitimement ajouter une dépendance ; CODEOWNERS suffit là-dessus."""
    assert "pyproject.toml" not in chemins_denies()
    assert "/pyproject.toml" in CODEOWNERS
