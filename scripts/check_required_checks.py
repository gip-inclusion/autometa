"""Échoue si les checks requis sur `main` divergent des jobs déclarés dans ci.yml."""

import json
import subprocess
import sys
from pathlib import Path

import yaml

WORKFLOW = Path(".github/workflows/ci.yml")
REPO = "gip-inclusion/autometa"
BRANCH = "main"


def declared_check_names(path: Path) -> set[str]:
    """GitHub matche sur le nom publié du check run, c'est-à-dire le `name:` du job."""
    jobs = yaml.safe_load(path.read_text())["jobs"]
    return {job.get("name", job_id) for job_id, job in jobs.items()}


def required_check_names(repo: str, branch: str) -> set[str] | None:
    """None quand gh est absent ; lève si l'API répond mal, un check aveugle étant pire que pas de check."""
    # Why: les checks requis vivent dans un ruleset, pas dans la protection de branche classique.
    # `/branches/{b}/protection` ne renvoie que les contextes de la protection classique — sur ce
    # dépôt, un seul des sept — et le script se croyait aligné en ne voyant presque rien.
    try:
        result = subprocess.run(
            ["gh", "api", f"repos/{repo}/rules/branches/{branch}"],
            capture_output=True,
            text=True,
            check=False,
        )
    except FileNotFoundError:
        return None
    if result.returncode != 0:
        raise RuntimeError(result.stderr.strip() or f"gh api a échoué ({result.returncode})")
    return {
        check["context"]
        for rule in json.loads(result.stdout)
        if rule.get("type") == "required_status_checks"
        for check in rule["parameters"]["required_status_checks"]
    }


def drift(declared: set[str], required: set[str]) -> tuple[list[str], list[str]]:
    """Bloquants d'abord : seul le sens « requis mais inexistant » gèle le dépôt."""
    bloquants = [f"Check « {name} » requis sur {BRANCH} mais absent de ci.yml" for name in sorted(required - declared)]
    # Un check neuf ne peut pas être requis avant d'avoir été publié une fois : l'inscrire d'avance
    # le laisserait en « Expected » sur toutes les PR. Cette fenêtre est normale, elle doit se fermer.
    a_inscrire = [
        f"Job « {name} » déclaré dans ci.yml mais non requis sur {BRANCH}" for name in sorted(declared - required)
    ]
    return bloquants, a_inscrire


def main() -> int:
    declared = declared_check_names(WORKFLOW)
    try:
        required = required_check_names(REPO, BRANCH)
    except RuntimeError as erreur:
        print(f"Ruleset de {BRANCH} illisible : {erreur}")
        print(
            "\nLe ruleset d'un dépôt public se lit sans droit particulier. Une lecture qui échoue "
            "rend ce check aveugle, donc vert quoi qu'il arrive : on échoue plutôt que de rassurer."
        )
        return 1

    if required is None:
        print(
            f"gh absent : dérive des checks requis non vérifiable sur {BRANCH}.\n"
            f"Checks à inscrire dans le ruleset : {', '.join(sorted(declared))}"
        )
        return 0

    if not required:
        print(
            f"Aucun check requis dans le ruleset de {BRANCH}. Aucune dérive vérifiable.\n"
            f"Checks à inscrire : {', '.join(sorted(declared))}"
        )
        return 0

    bloquants, a_inscrire = drift(declared, required)
    if bloquants:
        print("\n".join(bloquants))
        print(
            "\nUn check requis dont le nom n'existe pas reste indéfiniment « Expected — Waiting for "
            "status to be reported », et enforce_admins interdit de forcer le passage."
        )
        return 1

    if a_inscrire:
        print("\n".join(a_inscrire))
        print("\nÀ inscrire dans required_status_checks dès que ce check a été publié une première fois.")
        return 0

    print(f"Checks requis alignés sur ci.yml : {', '.join(sorted(required))}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
