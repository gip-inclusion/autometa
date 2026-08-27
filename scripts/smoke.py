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


def interface_changes(base: str) -> list[str]:
    changed = git("diff", "--name-only", f"{base}...HEAD").splitlines()
    return [path for path in changed if path.startswith(INTERFACE_PATHS)]


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


def plan(base: str, dod: Path | None) -> int:
    changed = interface_changes(base)
    if not changed:
        print(
            f"Aucun chemin d'interface modifié depuis {base} : smoke non requis.\n"
            f"  Chemins surveillés : {', '.join(INTERFACE_PATHS)}."
        )
        return 0

    directory = OUTPUT_ROOT / branch().replace("/", "-") / fingerprint()
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
    opening.add_argument("--base", default="main")
    opening.add_argument("--dod", type=Path, help="Definition of Done à jouer, si elle ne porte pas le nom de branche")
    closing = commands.add_parser("verify", help="fermer la passe et refuser toute capture au dépôt")
    closing.add_argument("--dir", required=True, type=Path)

    args = parser.parse_args()
    return plan(args.base, args.dod) if args.command == "plan" else verify(args.dir)


if __name__ == "__main__":
    sys.exit(main())
