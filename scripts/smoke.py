"""Ouvre et borne la passe de smoke exploratoire — le parcours, lui, est piloté par MCP."""

# Le smoke coûte plusieurs centaines de milliers de tokens d'entrée : ce script porte les deux bornes
# que l'agent ne doit pas pouvoir contourner par une phrase — une passe par état de l'interface, et
# aucune capture dans un dépôt public qui manipule des données de demandeurs d'emploi.

import argparse
import hashlib
import json
import re
import subprocess
import sys
from pathlib import Path

from lib import attestation

# Ailleurs, un parcours de navigateur ne révèle rien que les autres niveaux ne voient déjà.
INTERFACE_PATHS = ("web/templates", "web/static", "web/routes")
# Why: hors de l'arbre de travail, donc hors de portée d'un `git add -f` comme d'un `.gitignore` oublié.
OUTPUT_ROOT = Path.home() / ".cache" / "autometa" / "smoke"
BINARY_SUFFIXES = {".png", ".jpg", ".jpeg", ".gif", ".webp", ".avif", ".pdf", ".mp4", ".webm"}
CRITERION = re.compile(r"^DOD-\d+ — ")


def git(*args: str) -> str:
    return subprocess.run(["git", *args], capture_output=True, text=True, check=True).stdout.strip()


def branch() -> str:
    return git("rev-parse", "--abbrev-ref", "HEAD")


def fingerprint() -> str:
    """Empreintes d'arbre des chemins d'interface : un rebase ou un commit de doc ne les bouge pas."""
    trees = " ".join(git("rev-parse", f"HEAD:{path}") for path in INTERFACE_PATHS)
    return hashlib.sha1(trees.encode()).hexdigest()[:12]


# Why: `--base main` par défaut était faux dès qu'un parcours partait d'une autre branche — le
# contrôle d'antériorité avait le même défaut, et il échouait ici par une trace Python. La base
# journalisée à l'ouverture du parcours existe déjà : on la lit.
def resolved_base(base: str | None) -> str:
    """La base explicite, sinon celle que le parcours a journalisée à son ouverture."""
    return base or attestation.journey_base(Path("."), branch().split("/")[-1])


def changed_since(base: str) -> list[str] | None:
    """Fichiers modifiés depuis la base, ou None quand cette base n'est pas résolvable ici."""
    done = subprocess.run(["git", "diff", "--name-only", f"{base}...HEAD"], capture_output=True, text=True, check=False)
    return done.stdout.splitlines() if done.returncode == 0 else None


def unlocatable(base: str) -> int:
    """Dit quoi faire quand la base est introuvable, au lieu de remonter une trace."""
    print(
        f"« {base} » n'est pas résolvable ici : impossible de savoir ce que ce parcours a changé.\n"
        f"  Rouvrir le parcours avec `make paved-road-start BASE=<branche>`, ou passer `--base <ref>`."
    )
    return 1


def interface_changes(base: str) -> list[str] | None:
    changed = changed_since(base)
    return None if changed is None else [path for path in changed if path.startswith(INTERFACE_PATHS)]


def criteria(path: Path) -> list[str]:
    """Les `DOD-N` de la section « Ce qui devra marcher », chacun replié sur une ligne."""
    if not path.exists():
        return []
    section = path.read_text().partition("## Ce qui devra marcher")[2].partition("\n## ")[0]
    found = []
    for line in section.splitlines():
        if CRITERION.match(line):
            found.append(line.strip())
        elif found and line.startswith(("  ", "\t")):
            found[-1] += " " + line.strip()
    return found


def stray_captures() -> list[str]:
    """Binaires que la passe laisserait au dépôt — plus tout binaire déjà suivi sous `paved-road/`."""
    pending = [line[3:] for line in git("status", "--porcelain", "-uall").splitlines()]
    paths = [entry.partition(" -> ")[2] or entry for entry in pending]
    paths += git("ls-files", "paved-road").splitlines()
    return sorted({path for path in paths if path and Path(path).suffix in BINARY_SUFFIXES})


def pass_dir() -> Path:
    """Répertoire de la passe pour l'état courant de l'interface — une passe par état."""
    return OUTPUT_ROOT / branch().replace("/", "-") / fingerprint()


# Why: une passe manquante ne bloque rien — elle dépend d'un moteur de conteneurs qui tombe, et la
# rendre bloquante prendrait le parcours en otage. Mais « quinze critères démontrés » se lit « ça
# marche » alors que quinze tests passent : la description de PR doit porter ce que personne n'a vu.
def note(base: str | None) -> int:
    """Une ligne pour la description de PR : ce que le smoke a vu de l'interface, ou n'a pas vu."""
    base = resolved_base(base)
    changed = interface_changes(base)
    if changed is None:
        return unlocatable(base)
    if not changed:
        print("Interface inchangée : rien à signaler au relecteur au sujet du smoke.")
        return 0
    recorded = pass_dir() / "passe.json"
    if not recorded.exists():
        print(
            "Aucune passe de smoke sur cette interface : les critères sont démontrés par des tests, "
            "personne n'a vu cet écran dans un navigateur."
        )
        return 0
    captures = json.loads(recorded.read_text()).get("captures", [])
    print(f"Smoke joué sur cet état de l'interface : {len(captures)} capture(s) et un rapport.")
    return 0


def plan(base: str | None, dod: Path | None) -> int:
    base = resolved_base(base)
    changed = interface_changes(base)
    if changed is None:
        return unlocatable(base)
    if not changed:
        print(
            f"Aucun chemin d'interface modifié depuis {base} : smoke non requis.\n"
            f"  Chemins surveillés : {', '.join(INTERFACE_PATHS)}."
        )
        return 0

    directory = pass_dir()
    if (directory / "passe.json").exists():
        print(
            f"Cet état de l'interface a déjà été smoké : {directory}\n"
            "  Une seule passe par PR, sur le dernier état du code. Une correction qui touche "
            "réellement l'interface changera l'empreinte et rouvrira une passe."
        )
        return 1

    directory.mkdir(parents=True, exist_ok=True)
    steps = criteria(dod or Path("paved-road", branch().split("/")[-1], "definition-of-done.md"))
    parcours = (
        "Parcours à jouer, dérivé de la Definition of Done :\n  " + "\n  ".join(steps)
        if steps
        else "Aucune Definition of Done lue : jouer le parcours que la modification rend visible."
    )
    print("Chemins d'interface modifiés :\n  " + "\n  ".join(changed))
    print(f"\nCaptures et rapport à déposer dans : {directory}\n\n{parcours}")
    return 0


def verify(directory: Path) -> int:
    stray = stray_captures()
    if stray:
        print(
            "Des binaires atteindraient le dépôt, qui est public :\n  " + "\n  ".join(stray) + "\n"
            f"  Les déplacer sous {OUTPUT_ROOT} — les captures transitent par les artefacts de CI ou "
            "un commentaire de PR, jamais par l'historique git."
        )
        return 1

    if not (directory / "rapport.md").exists():
        print(f"Passe incomplète : {directory}/rapport.md est absent.\n  Le produit du smoke est ce qui a été vu.")
        return 1

    captures = sorted(path.name for path in directory.iterdir() if path.suffix in BINARY_SUFFIXES)
    recorded = {"branche": branch(), "empreinte": fingerprint(), "captures": captures}
    (directory / "passe.json").write_text(json.dumps(recorded, ensure_ascii=False, indent=2) + "\n")
    print(f"Passe enregistrée : {len(captures)} capture(s) et un rapport dans {directory}.")
    return 0


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    commands = parser.add_subparsers(dest="command", required=True)
    opening = commands.add_parser("plan", help="ouvrir une passe si l'interface a changé")
    opening.add_argument("--base", help="ref de départ ; par défaut, la base journalisée du parcours")
    opening.add_argument("--dod", type=Path, help="Definition of Done à jouer, si elle ne porte pas le nom de branche")
    closing = commands.add_parser("verify", help="fermer la passe et refuser toute capture au dépôt")
    closing.add_argument("--dir", required=True, type=Path)
    telling = commands.add_parser("note", help="la ligne que la description de PR porte sur le smoke")
    telling.add_argument("--base", help="ref de départ ; par défaut, la base journalisée du parcours")

    args = parser.parse_args()
    if args.command == "plan":
        return plan(args.base, args.dod)
    return note(args.base) if args.command == "note" else verify(args.dir)


if __name__ == "__main__":
    sys.exit(main())
