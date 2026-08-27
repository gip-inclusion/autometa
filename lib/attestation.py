"""Attestations du paved road — rattachement au contenu prouvé par empreintes d'arbre git."""

import hashlib
import os
import re
import shlex
import subprocess
import sys
from collections.abc import Iterable
from dataclasses import dataclass, field
from datetime import datetime, timezone
from pathlib import Path

from lib.pii import redact_nir

# Why: les artefacts du parcours sont committés par construction. Les inclure dans une
# empreinte invaliderait chaque attestation au moment même où on la range, et re-prouver
# produirait un nouveau commit donc une nouvelle invalidation — la boucle ne terminerait pas.
ARTIFACTS_ROOT = "paved-road"

# Why: `skills` en fait partie depuis le 27/08 — sans lui, réécrire le corps d'un SKILL.md après
# coup ne périmerait aucune preuve, alors que c'est du comportement livré comme le reste.
DEFAULT_PROVEN_PATHS = ("web", "lib", "scripts", "skills", "alembic", "tests")
STATES = ("align", "build", "prove")
OUTPUT_LIMIT = 2000
MAX_ATTESTATION_BYTES = 16 * 1024

FAMILIES = {
    "A": "réparable — corriger et relancer",
    "B": "environnement — arrêt, c'est une panne",
    "C": "question métier — retour au citizen developer",
    "D": "interdit — break-glass",
}

FIELD = re.compile(r"^\*\*(?P<key>[^*]+)\*\* — (?P<value>.*)$", re.M)
TREE_ROW = re.compile(r"^\| `(?P<path>[^`]+)` \| `(?P<sha>[0-9a-f]{40})` \|$", re.M)
OUTPUT_BLOCK = re.compile(r"^```\n(?P<body>.*?)\n?^```$", re.M | re.S)
CRITERION = re.compile(r"^(?P<dod>DOD-\d+) — (?P<text>.+?)(?=\n\s*\n|\nDOD-|\Z)", re.M | re.S)
PLACEHOLDER = re.compile(r"<(?!http)[^<>\n]{3,}>")
FORBIDDEN_CONTENT = re.compile(r"!\[[^\]]*\]\(|data:[a-z]+/[\w.+-]+;base64,", re.I)
VERDICT_MENTION = re.compile(r"démontré \((?P<mention>[^)]+)\)")


# Why: un hook git exporte GIT_DIR, GIT_WORK_TREE et GIT_INDEX_FILE. Sans les retirer, `git -C
# <ailleurs>` opère quand même sur le dépôt du hook : la suite lancée au pre-commit committait
# dans le vrai dépôt au lieu des dépôts jetables des tests. Constaté le 27/08.
GIT_ENV_INHERITED = ("GIT_DIR", "GIT_WORK_TREE", "GIT_INDEX_FILE", "GIT_OBJECT_DIRECTORY", "GIT_COMMON_DIR")


def git_env() -> dict[str, str]:
    """L'environnement courant, débarrassé de ce qu'un hook git y aurait posé."""
    return {key: value for key, value in os.environ.items() if key not in GIT_ENV_INHERITED}  # noqa: TID251


def git(repo: Path, *args: str) -> subprocess.CompletedProcess:
    """Exécute git dans le dépôt et rend le processus terminé, sans lever."""
    return subprocess.run(("git", "-C", str(repo), *args), capture_output=True, text=True, check=False, env=git_env())


def tree_fingerprint(repo: Path, path: str) -> str | None:
    """Empreinte de l'arbre git de `path` au HEAD, ou None si le chemin n'y figure pas."""
    done = git(repo, "rev-parse", f"HEAD:{path}")
    return done.stdout.strip() if done.returncode == 0 else None


def is_artifact_path(path: str) -> bool:
    """Vrai pour les chemins du parcours lui-même — attestations et journal."""
    return Path(path).parts[:1] == (ARTIFACTS_ROOT,)


def proven_paths(repo: Path, paths: Iterable[str] | None = None) -> list[str]:
    """Chemins dont l'empreinte sera enregistrée — jamais ceux du parcours lui-même."""
    candidates = list(DEFAULT_PROVEN_PATHS if paths is None else paths)
    forbidden = [path for path in candidates if is_artifact_path(path)]
    if forbidden:
        raise ValueError(f"Chemins exclus de toute attestation : {', '.join(forbidden)}")
    return [path for path in candidates if tree_fingerprint(repo, path)]


def fingerprints(repo: Path, paths: Iterable[str] | None = None) -> dict[str, str]:
    """Empreinte d'arbre de chaque chemin prouvé, au HEAD courant."""
    return {path: tree_fingerprint(repo, path) for path in proven_paths(repo, paths)}


def stale_paths(repo: Path, recorded: dict[str, str]) -> list[str]:
    """Chemins dont l'arbre a changé depuis que l'attestation les a enregistrés."""
    return sorted(path for path, sha in recorded.items() if tree_fingerprint(repo, path) != sha)


def dirty_paths(repo: Path, paths: Iterable[str]) -> list[str]:
    """Chemins prouvés portant des modifications non committées."""
    done = git(repo, "status", "--porcelain", "--", *paths)
    return sorted({line[3:].split(" -> ")[-1] for line in done.stdout.splitlines()})


def slug(repo: Path) -> str:
    """Nom du répertoire d'artefacts, tiré de la branche courante, préfixe retiré."""
    return git(repo, "rev-parse", "--abbrev-ref", "HEAD").stdout.strip().split("/")[-1]


def feature_dir(repo: Path, name: str) -> Path:
    return repo / ARTIFACTS_ROOT / name


def render_fields(title: str, pairs: Iterable[tuple[str, str]]) -> str:
    """Bloc markdown à champs — forme commune aux attestations et aux événements du journal."""
    return "\n".join([f"# {title}", "", *(f"**{key}** — {value}" for key, value in pairs), ""])


def parse_fields(text: str) -> dict[str, str]:
    return {match["key"]: match["value"].strip() for match in FIELD.finditer(text)}


@dataclass
class Attestation:
    """Preuve d'un critère : la commande lancée, son code de sortie, le contenu qu'elle prouve."""

    dod: str
    criterion: str
    command: str
    exit_code: int | None
    output: str
    trees: dict[str, str] = field(default_factory=dict)
    proven: bool = False
    not_replayable: str | None = None


def verdict(entry: Attestation) -> str:
    """Le verdict porte sa mention de non-rejeu : c'est elle que le job requis lit pour passer son tour."""
    if not entry.proven:
        return "non démontré."
    return f"démontré ({entry.not_replayable})." if entry.not_replayable else "démontré."


def render_attestation(entry: Attestation) -> str:
    return "\n".join([
        render_fields(
            entry.dod,
            [
                ("Critère", entry.criterion),
                ("Commande", f"`{entry.command}`"),
                ("Code de sortie", str(entry.exit_code)),
                ("Sortie", ""),
            ],
        ),
        "```",
        entry.output,
        "```",
        "",
        "**Contenu prouvé**",
        "",
        "| Chemin | Empreinte d'arbre |",
        "|---|---|",
        *(f"| `{path}` | `{sha}` |" for path, sha in entry.trees.items()),
        "",
        f"**Verdict** — {verdict(entry)}",
        "",
    ])


def parse_attestation(text: str) -> Attestation:
    """Lit une attestation, que sa sortie tienne dans un bloc de code ou sur une ligne."""
    fields = parse_fields(text)
    block = OUTPUT_BLOCK.search(text)
    code = fields.get("Code de sortie", "")
    return Attestation(
        dod=text.partition("\n")[0].lstrip("#").strip(),
        criterion=fields.get("Critère", ""),
        command=fields.get("Commande", "").strip("`"),
        exit_code=int(code) if code.lstrip("-").isdigit() else None,
        output=block["body"] if block else fields.get("Sortie", "").strip("`"),
        trees={match["path"]: match["sha"] for match in TREE_ROW.finditer(text)},
        proven=fields.get("Verdict", "").startswith("démontré"),
        not_replayable=(mention["mention"] if (mention := VERDICT_MENTION.search(fields.get("Verdict", ""))) else None),
    )


def criteria(dod_text: str) -> dict[str, str]:
    """Critères d'acceptation de la definition of done, par identifiant."""
    return {match["dod"]: " ".join(match["text"].split()) for match in CRITERION.finditer(dod_text)}


def truncate(output: str) -> str:
    """Fin de la sortie, bornée et débarrassée des NIR — le dépôt est public."""
    clean = redact_nir(output.strip())
    return clean if len(clean) <= OUTPUT_LIMIT else "…\n" + clean[-OUTPUT_LIMIT:]


def journal_dir(repo: Path, name: str) -> Path:
    return feature_dir(repo, name) / "journal"


def append_event(repo: Path, name: str, verb: str, pairs: list[tuple[str, str]]) -> Path:
    """Écrit un événement — un fichier par événement, jamais de conflit au rebase."""
    stamp = datetime.now(timezone.utc)
    body = render_fields(f"{stamp.isoformat(timespec='milliseconds')} — {verb}", pairs)
    target = journal_dir(repo, name) / f"{stamp.strftime('%Y%m%dT%H%M%S%fZ')}-{short_hash(body)}.md"
    target.parent.mkdir(parents=True, exist_ok=True)
    target.write_text(body)
    return target


def short_hash(text: str) -> str:
    return hashlib.sha256(text.encode()).hexdigest()[:8]


def events(repo: Path, name: str) -> list[dict[str, str]]:
    """Journal agrégé à la lecture, dans l'ordre des horodatages."""
    directory = journal_dir(repo, name)
    return [parse_fields(path.read_text()) for path in sorted(directory.glob("*.md"))] if directory.is_dir() else []


def current_state(journal: list[dict[str, str]]) -> str:
    """État atteint — `align` tant qu'aucune transition n'a été journalisée."""
    reached = [event["État"] for event in journal if event.get("Résultat") == "succès" and event.get("État") in STATES]
    return reached[-1] if reached else STATES[0]


def next_state(state: str) -> str:
    return STATES[min(STATES.index(state) + 1, len(STATES) - 1)]


def consecutive_repairable(journal: list[dict[str, str]]) -> int:
    """Échecs de famille A enchaînés depuis le dernier succès — en observation, sans effet."""
    count = 0
    for event in reversed(journal):
        if event.get("Résultat") != "échec":
            break
        if event.get("Famille") != "A":
            break
        count += 1
    return count


@dataclass(frozen=True)
class Check:
    """Un check déclare la famille de son échec — c'est elle qui commande la suite."""

    name: str
    family: str
    argv: tuple[str, ...]


SELF = (sys.executable, "scripts/paved_road_cli.py", "check")

CHECKS = {
    "align": (Check("dod", "A", (*SELF, "dod")),),
    "build": (
        Check("environment", "B", (sys.executable, "scripts/doctor.py")),
        Check("lint", "A", ("make", "lint")),
        Check("security", "A", ("make", "security")),
        Check("test", "A", ("make", "test")),
    ),
    "prove": (
        Check("content", "D", (*SELF, "content")),
        Check("attestations", "A", (*SELF, "attestations")),
    ),
}


def run_command(repo: Path, argv: Iterable[str]) -> tuple[int, str]:
    """La commande de preuve tourne dans le dépôt prouvé, pas dans celui d'un hook appelant."""
    done = subprocess.run(tuple(argv), cwd=repo, capture_output=True, text=True, check=False, env=git_env())
    return done.returncode, done.stdout + done.stderr


def dod_path(repo: Path, name: str) -> Path:
    return feature_dir(repo, name) / "definition-of-done.md"


def attestations_dir(repo: Path, name: str) -> Path:
    return feature_dir(repo, name) / "attestations"


def verify_dod(repo: Path, name: str) -> list[str]:
    """Ce qu'une machine peut constater d'une definition of done — aucune lecture n'est remplacée."""
    path = dod_path(repo, name)
    if not path.is_file():
        return [f"Definition of done absente : {path}"]
    text = path.read_text()
    found = [match["dod"] for match in CRITERION.finditer(text)]
    problems = [f"Identifiant en double : {dod}" for dod in sorted({d for d in found if found.count(d) > 1})]
    if not found:
        problems.append("Aucun critère « DOD-N — … » dans « Ce qui devra marcher ».")
    problems += [f"Section « {title} » absente." for title in ("Questions ouvertes", "Validation") if title not in text]
    problems += [f"Gabarit non rempli : {found}" for found in sorted(set(PLACEHOLDER.findall(text)))]
    return problems


def verify_attestations(repo: Path, name: str, paths: Iterable[str] | None = None) -> list[str]:
    """Un critère non démontré ne peut pas se noyer : chacun porte son verdict."""
    problems = [
        f"Modification non committée sur un chemin prouvé : {p}" for p in dirty_paths(repo, proven_paths(repo, paths))
    ]
    expected = criteria(dod_path(repo, name).read_text()) if dod_path(repo, name).is_file() else {}
    directory = attestations_dir(repo, name)
    filed = (
        {path.stem: parse_attestation(path.read_text()) for path in sorted(directory.glob("*.md"))}
        if directory.is_dir()
        else {}
    )
    for dod in expected:
        entry = filed.get(dod)
        if entry is None:
            problems.append(f"{dod} — non démontré : aucune attestation.")
        elif entry.exit_code != 0 or not entry.proven:
            problems.append(f"{dod} — non démontré : `{entry.command}` sort en {entry.exit_code}.")
        elif not entry.trees:
            problems.append(f"{dod} — attestation sans empreinte : elle ne prouve aucun contenu.")
        elif stale := stale_paths(repo, entry.trees):
            problems.append(f"{dod} — attestation périmée, {', '.join(stale)} a changé depuis. Relancer la preuve.")
    return problems + [f"{dod} — attestation sans critère correspondant." for dod in filed if dod not in expected]


def verify_content(repo: Path) -> list[str]:
    """Le dépôt est public : sous `paved-road/`, rien d'autre que du texte écrit pour être lu.

    Why: le périmètre couvre tout `paved-road/<slug>/**` depuis le 27/08, pas seulement
    `attestations/`. La rétro et les rapports de relecture sont exigés dès le palier 1, et ils
    citent l'usage réel — donc potentiellement des données de personnes, sur un dépôt public.
    """
    problems = []
    for path in sorted(p for p in (repo / ARTIFACTS_ROOT).glob("*/**/*") if p.is_file()):
        shown = path.relative_to(repo).as_posix()
        if path.suffix != ".md":
            problems.append(f"{shown} — seul du markdown est admis sous `paved-road/`.")
        elif path.stat().st_size > MAX_ATTESTATION_BYTES:
            problems.append(
                f"{shown} — {path.stat().st_size} octets : un artefact de parcours se lit, il ne stocke pas."
            )
        else:
            try:
                text = path.read_text()
            except UnicodeDecodeError:
                problems.append(f"{shown} — contenu binaire : aucune image, aucun binaire sous `paved-road/`.")
                continue
            if FORBIDDEN_CONTENT.search(text):
                problems.append(f"{shown} — image ou contenu encodé : il appartient aux artefacts de CI, pas au dépôt.")
    return problems


# Une preuve est une commande qu'un tiers peut relancer. La liste est fermée : tout le reste
# demande d'élargir cette liste dans une PR que CODEOWNERS voit passer.
ALLOWED_PROVE_PREFIXES = (
    ("uv", "run", "--frozen", "pytest"),
    ("uv", "run", "--frozen", "alembic"),
    ("uv", "run", "--frozen", "python"),
    ("make",),
)
# Collecter n'est pas exécuter : ces drapeaux rendent 0 sans qu'aucun test ne tourne.
COLLECT_ONLY = ("--collect-only", "--co")
# Un `-k` qui ne désigne rien sort en 0 avec « 2129 deselected » : la seule marque qu'un test a
# réellement tourné est le compte de succès.
PYTEST_RAN = re.compile(r"\b\d+ passed\b")
# Ces preuves-là ne se rejouent pas dans le job requis : il n'a ni navigateur, ni application
# servie, ni les accès du nightly. Le verdict porte la mention, et le contrat l'annonce d'avance.
NOT_REPLAYABLE = {"browser": "E2E", "-m browser": "E2E", "--nightly": "nightly"}


def command_refusals(command: str, dod: str) -> list[str]:
    """Ce qui disqualifie une commande de preuve, avant même de l'exécuter."""
    argv = shlex.split(command)
    refusals = []
    # Why: l'attestation range la commande sur une ligne ; une commande multi-lignes s'y relit
    # tronquée, et la preuve ne décrirait plus ce qui a tourné.
    if "\n" in command:
        refusals.append("Une commande de preuve tient sur une ligne.")
    if not any(tuple(argv[: len(prefix)]) == prefix for prefix in ALLOWED_PROVE_PREFIXES):
        autorises = ", ".join("`" + " ".join(p) + "`" for p in ALLOWED_PROVE_PREFIXES)
        refusals.append(f"`{command}` ne commence par aucune commande de preuve admise ({autorises}).")
    if collecting := [flag for flag in COLLECT_ONLY if flag in argv]:
        refusals.append(f"{collecting[0]} collecte les tests sans les exécuter : la preuve serait vide.")
    if "pytest" in argv and dod.lower().replace("-", "_") not in command.lower().replace("-", "_"):
        refusals.append(
            f"La commande ne sélectionne aucun test nommé d'après {dod} : un test vert au hasard "
            f"ne démontre pas ce critère. Nomme le test `test_{dod.lower().replace('-', '_')}_…`."
        )
    return refusals


def replay_exemption(command: str) -> str | None:
    """La mention à porter au verdict quand la preuve ne peut pas être rejouée par le job requis."""
    return next((mention for motif, mention in NOT_REPLAYABLE.items() if motif in command), None)


def prove(repo: Path, name: str, dod: str, command: str, paths: Iterable[str] | None = None) -> Attestation:
    """Exécute la commande et range l'attestation du critère — seule écriture sous attestations/."""
    expected = criteria(dod_path(repo, name).read_text())
    if dod not in expected:
        raise ValueError(f"{dod} ne figure pas dans {dod_path(repo, name).relative_to(repo)}")
    tracked = proven_paths(repo, paths)
    if dirty := dirty_paths(repo, tracked):
        raise ValueError(f"Committer d'abord le code prouvé, sinon l'empreinte ne le décrit pas : {', '.join(dirty)}")
    if refusals := command_refusals(command, dod):
        raise ValueError("\n".join(refusals))
    code, output = run_command(repo, shlex.split(command))
    if code == 0 and "pytest" in shlex.split(command) and not PYTEST_RAN.search(output):
        raise ValueError(f"`{command}` sort en 0 sans qu'aucun test n'ait tourné : la preuve serait vide.")
    entry = Attestation(
        dod=dod,
        criterion=expected[dod],
        command=command,
        exit_code=code,
        output=truncate(output),
        trees={path: tree_fingerprint(repo, path) for path in tracked},
        proven=code == 0,
        not_replayable=replay_exemption(command),
    )
    target = attestations_dir(repo, name) / f"{dod}.md"
    target.parent.mkdir(parents=True, exist_ok=True)
    target.write_text(render_attestation(entry))
    append_event(
        repo,
        name,
        f"prove {dod}",
        [
            ("État", current_state(events(repo, name))),
            ("Résultat", "succès" if code == 0 else "échec"),
            ("Critère", dod),
            ("Commande", f"`{command}`"),
            ("Code de sortie", str(code)),
        ],
    )
    return entry


def last_line(output: str) -> str:
    lines = [line for line in redact_nir(output).splitlines() if line.strip()]
    return lines[-1][:200] if lines else "(aucune sortie)"


def advance(repo: Path, name: str) -> tuple[bool, str]:
    """Fait progresser l'état, et seulement d'après des codes de sortie réels."""
    journal = events(repo, name)
    state = current_state(journal)
    for check in CHECKS[state]:
        code, output = run_command(repo, check.argv)
        if code == 0:
            continue
        repairable = consecutive_repairable(journal) + 1 if check.family == "A" else 0
        append_event(
            repo,
            name,
            "advance",
            [
                ("État", state),
                ("Résultat", "échec"),
                ("Check", check.name),
                ("Code de sortie", str(code)),
                ("Famille", check.family),
                ("Réponse", FAMILIES[check.family]),
                ("Échecs A consécutifs", str(repairable)),
                ("Détail", last_line(output)),
            ],
        )
        return False, f"{state} — `{check.name}` sort en {code}. Famille {check.family} : {FAMILIES[check.family]}."
    reached = next_state(state)
    append_event(
        repo,
        name,
        "advance",
        [
            ("État", reached),
            ("Résultat", "succès"),
            ("Depuis", state),
            ("Checks", ", ".join(check.name for check in CHECKS[state])),
            ("Échecs A consécutifs", "0"),
        ],
    )
    return True, f"{state} → {reached}." if reached != state else "prove — parcours démontré."
