"""Vérifie qu'une modification du produit s'appuie sur une Definition of Done démontrée."""

import argparse
import shlex
import subprocess
import sys
from dataclasses import dataclass
from pathlib import Path

from lib import attestation

# Le paved road est requis si et seulement si le diff touche ces répertoires. Ailleurs —
# dépendances, docs/, knowledge/ — il est neutre : un check exigé sur toutes les PR gèlerait
# le dépôt, un check jamais exigé se contournerait en n'écrivant pas de Definition of Done.
PERIMETRE = ("web/", "lib/", "skills/", "alembic/")
ARTEFACTS = Path("paved-road")
BREAK_GLASS = "break-glass"

# Le code de sortie ne distingue pas un test rouge d'un service absent, et la réponse
# n'est pas la même : sur B, réessayer brûle du temps sans rien corriger.
INDISPONIBILITE = ("Connection refused", "could not connect", "Temporary failure in name resolution")

FAMILLES = {
    "A": "réparable — l'agent reprend le travail",
    "B": "environnement — arrêt immédiat, c'est une panne",
    "C": "question métier — retour au citizen developer",
    "D": "interdit — break-glass",
}


@dataclass
class Echec:
    famille: str
    phrase: str
    critere: str = ""


def fichiers_modifies(base: str) -> list[str]:
    diff = subprocess.run(["git", "diff", "--name-only", f"{base}...HEAD"], capture_output=True, text=True, check=True)
    return diff.stdout.split()


def dossiers_de_parcours(fichiers: list[str]) -> list[Path]:
    """Les répertoires `paved-road/<slug>/` que la branche ajoute ou modifie."""
    return sorted({
        ARTEFACTS / Path(f).relative_to(ARTEFACTS).parts[0] for f in fichiers if f.startswith("paved-road/")
    })


def empreinte_courante(chemin: str) -> str | None:
    """None quand le chemin n'existe plus dans l'arbre courant."""
    resultat = subprocess.run(["git", "rev-parse", f"HEAD:{chemin}"], capture_output=True, text=True, check=False)
    return resultat.stdout.strip() if resultat.returncode == 0 else None


def verifier_critere(dossier: Path, identifiant: str) -> list[Echec]:
    chemin = dossier / "attestations" / f"{identifiant}.md"
    if not chemin.exists():
        return [Echec("A", f"{identifiant} n'a pas d'attestation : rien ne démontre ce critère.", identifiant)]

    preuve = attestation.parse_attestation(chemin.read_text())
    if not preuve.proven:
        return [Echec("A", f"{identifiant} est journalisé « non démontré ».", identifiant)]

    perimees = [
        Echec(
            "A",
            f"{identifiant} a été prouvé sur un `{prouve}` qui a changé depuis : la preuve est périmée.",
            identifiant,
        )
        for prouve, empreinte in preuve.trees.items()
        if empreinte_courante(prouve) != empreinte
    ]
    if perimees:
        return perimees

    # Une preuve jouée dans un navigateur ou en nightly ne se rejoue pas ici : ce job n'a ni
    # l'un ni l'autre. La rejouer la ferait échouer pour une raison qui n'est pas le code, et
    # rendrait la PR infusionnable dès que ce check est requis.
    if preuve.not_replayable:
        return []

    # Ailleurs, la CI ne fait pas confiance au journal : elle rejoue la commande avec le même
    # exécuteur que `prove` — même découpage, même environnement — et compare les codes de sortie.
    code, sortie = attestation.run_command(Path.cwd(), shlex.split(preuve.command))
    if code == preuve.exit_code:
        return []

    if any(motif in sortie for motif in INDISPONIBILITE):
        return [
            Echec(
                "B",
                f"Le rejeu de {identifiant} n'a atteint ni Postgres ni Redis : ce n'est pas le code qui "
                "est en cause, c'est l'environnement.",
                identifiant,
            )
        ]
    return [
        Echec(
            "A",
            f"{identifiant} annonce un code de sortie {preuve.exit_code}, le rejeu renvoie {code}.",
            identifiant,
        )
    ]


def verifier_parcours(dossier: Path) -> tuple[dict[str, str], list[Echec]]:
    definition = dossier / "definition-of-done.md"
    if not definition.exists():
        return {}, [Echec("C", f"`{dossier}` n'a pas de `definition-of-done.md` : rien ne dit ce qui devait marcher.")]

    texte = definition.read_text()
    attendus = attestation.criteria(texte)
    if not attendus:
        return {}, [Echec("C", f"`{definition}` ne déclare aucun critère `DOD-N`.")]

    echecs = []
    if "## Questions ouvertes" not in texte:
        echecs.append(Echec("C", f"`{definition}` n'a pas de section « Questions ouvertes »."))

    # Le dépôt est public et le produit manipule des données sur des demandeurs d'emploi :
    # sous `attestations/`, uniquement le texte structuré que produit la commande d'avancement.
    echecs += [
        Echec("D", f"`{intrus}` n'est pas un fichier d'attestation, et le dépôt est public.")
        for intrus in sorted((dossier / "attestations").glob("*"))
        if intrus.suffix != ".md"
    ]

    for identifiant in sorted(attendus):
        echecs += verifier_critere(dossier, identifiant)
    return attendus, echecs


def tableau(dossier: Path, attendus: dict[str, str], echecs: list[Echec]) -> str:
    en_echec = {echec.critere for echec in echecs}
    lignes = [f"## {dossier.name}", "", "| Critère | Ce qui devait marcher | Verdict |", "|---|---|---|"]
    lignes += [
        f"| {identifiant} | {enonce} | {'**non démontré**' if identifiant in en_echec else 'démontré'} |"
        for identifiant, enonce in sorted(attendus.items())
    ]
    return "\n".join(lignes)


def rapport(fichiers: list[str], labels: list[str]) -> tuple[str, int]:
    concernes = [f for f in fichiers if f.startswith(PERIMETRE)]
    if not concernes:
        return "Cette PR ne touche ni `web/`, ni `lib/`, ni `skills/`, ni `alembic/` : rien à démontrer ici.", 0

    if BREAK_GLASS in labels:
        couverts = "\n".join(f"- `{f}`" for f in concernes)
        return (
            f"Un humain a posé le label `{BREAK_GLASS}` : le paved road est levé sur cette PR, et "
            f"cette dispense est journalisée ici.\n\nModifications couvertes :\n{couverts}"
        ), 0

    dossiers = dossiers_de_parcours(fichiers)
    if not dossiers:
        concernes_listes = "\n".join(f"- `{f}`" for f in concernes)
        return (
            "# Ce qui devait marcher\n\n"
            "Cette PR modifie le produit sans Definition of Done. Personne ne peut donc juger si c'est "
            "le bon travail : il manque l'accord écrit qui dit ce qui devra marcher à la fin.\n\n"
            f"Fichiers concernés :\n{concernes_listes}\n\n"
            f"**Famille C** — {FAMILLES['C']}."
        ), 1

    sections = ["# Ce qui devait marcher\n"]
    echecs: list[Echec] = []
    for dossier in dossiers:
        attendus, propres = verifier_parcours(dossier)
        echecs += propres
        if attendus:
            sections.append(tableau(dossier, attendus, propres))

    if not echecs:
        sections.append("Tous les critères sont démontrés, et la CI les a rejoués elle-même.")
        return "\n\n".join(sections), 0

    sections.append("## Ce qui bloque\n")
    sections += [f"- {echec.phrase}\n  **Famille {echec.famille}** — {FAMILLES[echec.famille]}." for echec in echecs]
    return "\n\n".join(sections), 1


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--base", default="origin/main", help="référence de comparaison du diff")
    parser.add_argument("--label", action="append", default=[], help="label posé sur la PR")
    arguments = parser.parse_args()

    texte, code = rapport(fichiers_modifies(arguments.base), arguments.label)
    print(texte)
    return code


if __name__ == "__main__":
    sys.exit(main())
