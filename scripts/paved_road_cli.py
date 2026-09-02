"""Parcours paved road — démarrer, consulter l'état, lancer les checks, avancer."""

import argparse
import sys
from pathlib import Path

from lib import attestation

REPO = Path(".")

TEMPLATE = """# <Titre de la fonctionnalité>

## Ce que je veux

<Deux ou trois phrases. L'intention, pas la solution.>

## Ce qui devra marcher

DOD-1 — <Résultat observable, au présent, du point de vue de la personne qui s'en sert.>

## Sources lues

<Chaque source, avec la règle qui l'a déclenchée.>

## Questions ouvertes

<Ce qu'aucune lecture n'a tranché, ou « Aucune ».>

## Validation

<Validé par <nom> le <AAAA-MM-JJ>.>
"""


# Le pre-commit passe le lint et les tests, le pre-push les rejoue avant publication. Un worktree
# neuf n'a ni l'un ni l'autre : les premiers commits du parcours passaient sans rien vérifier.
HOOK_TARGETS = {"pre-commit": "hooks", "pre-push": "install-hooks"}


def prepare(repo: Path) -> None:
    """Installe les hooks que le worktree n'a pas, puis dit ce que l'environnement bloque encore."""
    for hook in attestation.missing_hooks(repo):
        target = HOOK_TARGETS[hook]
        code, output = attestation.run_command(repo, ("make", target))
        print(f"Hook {hook} — {'installé' if code == 0 else f'absent, `make {target}` a échoué'}.")
        if code != 0:
            print(output.rstrip())
    # Why: le front et le navigateur sont des notes, pas des pannes — `doctor` sort en 0 avec elles,
    # et elles ne se verraient jamais si l'ouverture n'affichait que les échecs. On retient donc
    # tout ce qui n'est pas déjà en ordre.
    _, output = attestation.run_command(repo, (sys.executable, "scripts/doctor.py"))
    for line in output.splitlines():
        if line.strip() and not line.lstrip().startswith("ok "):
            print(line)


def start(repo: Path, name: str, base: str | None) -> int:
    """Ouvre le répertoire du parcours — la definition of done reste à écrire et à faire valider."""
    path = attestation.dod_path(repo, name)
    attestation.attestations_dir(repo, name).mkdir(parents=True, exist_ok=True)
    attestation.journal_dir(repo, name).mkdir(parents=True, exist_ok=True)
    if not path.is_file():
        path.write_text(TEMPLATE)
    if base:
        attestation.record_base(repo, name, base)
    prepare(repo)
    print(f"Parcours « {name} » — état align, parti de {attestation.journey_base(repo, name)}.")
    print(f"Rédiger {path}, la faire valider, puis `make paved-road-advance`.")
    return 0


def status(repo: Path, name: str) -> int:
    """État atteint, verdict de chaque critère, et compteur d'échecs réparables."""
    journal = attestation.events(repo, name)
    state = attestation.current_state(journal)
    print(
        f"Parcours « {name} » — état {state}, parti de {attestation.journey_base(repo, name)}, "
        f"{len(journal)} événement(s) au journal."
    )
    print(
        f"Échecs de famille A enchaînés : {attestation.consecutive_repairable(journal)} (en observation, sans effet)."
    )
    path = attestation.dod_path(repo, name)
    if not path.is_file():
        print(f"Aucune definition of done : {path}")
        return 0
    filed = attestation.attestations_dir(repo, name)
    for dod, text in attestation.criteria(path.read_text()).items():
        target = filed / f"{dod}.md"
        entry = attestation.parse_attestation(target.read_text()) if target.is_file() else None
        stale = attestation.stale_paths(repo, entry.trees) if entry else []
        verdict = "non démontré" if entry is None or not entry.proven else "périmé" if stale else "démontré"
        print(f"  {dod} — {verdict} — {text[:80]}")
    for problem in attestation.verify_content(repo):
        print(f"  ! {problem}")
    return 0


def check(repo: Path, name: str, which: str | None, base: str | None) -> int:
    """Lance les checks de l'état courant, ou un seul d'entre eux."""
    if which == "dod":
        return report(attestation.verify_dod(repo, name, base), "Definition of done conforme.")
    if which == "attestations":
        return report(attestation.verify_attestations(repo, name), "Chaque critère porte une attestation à jour.")
    if which == "content":
        return report(attestation.verify_content(repo), "Rien d'autre que du markdown sous paved-road/.")
    state = attestation.current_state(attestation.events(repo, name))
    failed = 0
    for item in attestation.CHECKS[state]:
        code, output = attestation.run_command(repo, item.argv)
        print(f"[{'ok ' if code == 0 else 'ko '}] {item.name} (famille {item.family})")
        if code != 0:
            print(output.rstrip())
            print(f"       {attestation.FAMILIES[item.family]}")
            failed = 1
    return failed


def report(problems: list[str], success: str) -> int:
    for problem in problems:
        print(problem)
    if not problems:
        print(success)
    return 1 if problems else 0


def advance(repo: Path, name: str, dod: str | None, command: str | None, red: bool) -> int:
    """Journalise un rouge, prouve un critère, ou fait progresser l'état — jamais sans code de sortie réel."""
    if dod and red:
        code, mark = attestation.record_red(repo, name, dod, command)
        print(f"{dod} — rouge journalisé, `{command}` sort en {code}.")
        print(f"Empreinte du périmètre au moment du rouge : {mark}. Implémenter, committer, puis prouver.")
        return 0
    if dod:
        entry = attestation.prove(repo, name, dod, command)
        print(f"{dod} — {'démontré' if entry.proven else 'non démontré'}, `{command}` sort en {entry.exit_code}.")
        print(f"Contenu prouvé : {', '.join(entry.trees)}.")
        return 0 if entry.proven else 1
    moved, message = attestation.advance(repo, name)
    print(message)
    return 0 if moved else 1


def reprove(repo: Path, name: str) -> int:
    """Rejoue d'un coup toutes les preuves qu'un rebase ou un commit a périmées."""
    stale = attestation.stale_attestations(repo, name)
    if not stale:
        print("Aucune preuve périmée : chaque attestation décrit encore le code.")
        return 0
    failures = attestation.reprove_stale(repo, name)
    print(f"{len(stale) - len(failures)} preuve(s) rejouée(s) sur {len(stale)} périmée(s).")
    for dod, reason in failures:
        print(f"{dod} — non rejouée : {reason}")
    return 1 if failures else 0


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--feature", help="répertoire d'artefacts ; par défaut, la branche courante")
    subparsers = parser.add_subparsers(dest="verb", required=True)
    opening = subparsers.add_parser("start")
    opening.add_argument("--base", help="branche dont le parcours part ; par défaut, la branche principale publiée")
    subparsers.add_parser("status")
    subparsers.add_parser("reprove")
    verify = subparsers.add_parser("check")
    verify.add_argument("which", nargs="?", choices=["dod", "attestations", "content"])
    verify.add_argument("--base", help="référence qui délimite les commits du parcours")
    prove = subparsers.add_parser("advance")
    prove.add_argument("--dod")
    prove.add_argument("--command")
    prove.add_argument("--red", action="store_true", help="journalise l'échec attendu du critère")
    args = parser.parse_args(argv)

    name = args.feature or attestation.slug(REPO)
    if args.verb == "start":
        return start(REPO, name, args.base)
    if args.verb == "status":
        return status(REPO, name)
    if args.verb == "reprove":
        return reprove(REPO, name)
    if args.verb == "check":
        return check(REPO, name, args.which, args.base)
    if args.dod and not args.command:
        parser.error("--dod attend la commande qui le démontre : --command '…'")
    try:
        return advance(REPO, name, args.dod, args.command, args.red)
    except ValueError as error:
        print(f"{error}\nFamille A : {attestation.FAMILIES['A']}")
        return 1


if __name__ == "__main__":
    sys.exit(main())
