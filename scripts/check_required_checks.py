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
    """None quand gh est absent, la protection non armée, ou illisible avec le token courant."""
    try:
        result = subprocess.run(
            ["gh", "api", f"repos/{repo}/branches/{branch}/protection/required_status_checks"],
            capture_output=True,
            text=True,
            check=False,
        )
    except FileNotFoundError:
        return None
    if result.returncode != 0:
        return None
    return set(json.loads(result.stdout).get("contexts", []))


def drift(declared: set[str], required: set[str]) -> list[str]:
    problems = [
        f"Job « {name} » déclaré dans ci.yml mais non requis sur {BRANCH}" for name in sorted(declared - required)
    ]
    problems += [f"Check « {name} » requis sur {BRANCH} mais absent de ci.yml" for name in sorted(required - declared)]
    return problems


def main() -> int:
    declared = declared_check_names(WORKFLOW)
    required = required_check_names(REPO, BRANCH)

    if required is None:
        print(
            f"Protection de branche non armée sur {BRANCH}, ou illisible avec le token courant "
            "(la lecture exige un droit admin). Aucune dérive vérifiable.\n"
            f"Checks à inscrire dans required_status_checks : {', '.join(sorted(declared))}"
        )
        return 0

    problems = drift(declared, required)
    if problems:
        print("\n".join(problems))
        print(
            "\nUn check requis dont le nom n'existe pas reste indéfiniment « Expected — Waiting for "
            "status to be reported », et enforce_admins interdit de forcer le passage."
        )
        return 1

    print(f"Checks requis alignés sur ci.yml : {', '.join(sorted(required))}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
