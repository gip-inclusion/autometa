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
        # Why: `git commit * --no-verify*` exigeait un token entre les deux — le `*` absorbe l'espace.
        "Bash(git commit*--no-verify*)",
        "Bash(git -c core.hooksPath=*)",
    ],
)
def test_les_contournements_connus_restent_refuses(commande):
    """Chacune de ces commandes désarme un contrôle que l'agent est censé subir."""
    assert commande in DENY


def test_le_parcours_nominal_ne_demande_pas_d_autorisation():
    """Sans liste allow, chaque `make` et chaque `git` du parcours ouvre une invite au demandeur."""
    allow = json.loads((REPO / ".claude" / "settings.json").read_text())["permissions"]["allow"]

    for commande in ["Bash(make *)", "Bash(git commit*)"]:
        assert commande in allow


def test_ouvrir_une_pr_reste_une_action_confirmee():
    """Une PR est une action sortante : elle passe par une confirmation, pas par la liste allow."""
    allow = json.loads((REPO / ".claude" / "settings.json").read_text())["permissions"]["allow"]

    assert not [regle for regle in allow if regle.startswith("Bash(gh pr create")]


def test_le_hook_bash_couvre_ce_qu_un_glob_ne_voit_pas():
    """Un cluster de drapeaux courts (`-nm`) est hors de portée du modèle de motifs des permissions."""
    hooks = json.loads((REPO / ".claude" / "settings.json").read_text())["hooks"]["PreToolUse"]
    commandes = [hook["command"] for entree in hooks if entree["matcher"] == "Bash" for hook in entree["hooks"]]

    assert any("guard_bash.py" in commande for commande in commandes)


def test_pyproject_reste_hors_de_la_couche_1():
    """Une fonctionnalité peut légitimement ajouter une dépendance ; CODEOWNERS suffit là-dessus."""
    assert "pyproject.toml" not in chemins_denies()
    assert "/pyproject.toml" in CODEOWNERS
