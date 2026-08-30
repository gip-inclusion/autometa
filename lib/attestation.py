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

# Périmètre du produit : y toucher avant d'avoir committé le contrat, c'est écrire le contrat après coup.
CONTRACT_SCOPE = ("web", "lib", "skills", "alembic")
DEFAULT_BASE = "origin/main"
STATES = ("align", "build", "prove")
OUTPUT_LIMIT = 2000
MAX_ATTESTATION_BYTES = 16 * 1024

FAMILIES = {
    "A": "réparable — corriger et relancer",
    "B": "environnement — arrêt, c'est une panne",
    "C": "question métier — retour au citizen developer",
    "D": "interdit — arrêt, la décision remonte à un humain",
}

FIELD = re.compile(r"^\*\*(?P<key>[^*]+)\*\* — (?P<value>.*)$", re.M)
TREE_ROW = re.compile(r"^\| `(?P<path>[^`]+)` \| `(?P<sha>[0-9a-f]{40})` \|$", re.M)
OUTPUT_BLOCK = re.compile(r"^```\n(?P<body>.*?)\n?^```$", re.M | re.S)
CRITERION = re.compile(r"^(?P<dod>DOD-\d+) — (?P<text>.+?)(?=\n\s*\n|\nDOD-|\Z)", re.M | re.S)
PLACEHOLDER = re.compile(r"<(?!http)[^<>\n]{3,}>")
VALIDATION = re.compile(r"Validé par .+ le \d{4}-\d{2}-\d{2}")
REVISION = re.compile(r"Révision \d{4}-\d{2}-\d{2}")
FORBIDDEN_CONTENT = re.compile(r"!\[[^\]]*\]\(|data:[a-z]+/[\w.+-]+;base64,", re.I)


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


# Why: `paths` n'existe plus que pour les dépôts jetables des tests. La ligne de commande ne
# l'expose plus depuis le 2026-08-30 : `PATHS=tests` rangeait une attestation qui n'engageait que
# `tests/`, et tout `web/` pouvait être réécrit sans périmer une seule preuve.
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


def verdict(entry: Attestation) -> str:
    """Un critère porte un verdict et un seul — aucune mention ne le nuance."""
    return "démontré." if entry.proven else "non démontré."


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


def commit_rank(repo: Path, window: str) -> dict[str, int]:
    """Rang de chaque commit de la fenêtre, du plus ancien au plus récent."""
    return {sha: rank for rank, sha in enumerate(git(repo, "rev-list", "--reverse", window).stdout.split())}


def journey_window(repo: Path, base: str) -> str | None:
    """Plage des commits que la branche ajoute, ou None quand la base n'est pas résolvable."""
    fork = git(repo, "merge-base", base, "HEAD")
    return f"{fork.stdout.strip()}..HEAD" if fork.returncode == 0 else None


def dod_antedates_code(repo: Path, name: str, base: str = DEFAULT_BASE) -> list[str]:
    """Le contrat est le premier commit du parcours — l'ordre des commits le dit, une réécriture l'efface."""
    window = journey_window(repo, base)
    if window is None:
        return []
    touched = set(git(repo, "rev-list", window, "--", *CONTRACT_SCOPE).stdout.split())
    if not touched:
        return []
    shown = dod_path(repo, name).relative_to(repo).as_posix()
    added = git(repo, "log", "--diff-filter=A", "--format=%H", "--", shown).stdout.split()
    rank = commit_rank(repo, window)
    # Why: un contrat ajouté avant la fenêtre précède tout le code de la branche. Sans ce rang
    # négatif, `rank.get` rendait None et le contrôle concluait l'inverse de la vérité dès qu'une
    # branche partait d'une base portant déjà le contrat, ou après un rebase.
    contract = rank.get(added[-1], -1) if added else None
    if contract is not None and all(rank[sha] >= contract for sha in touched):
        return []
    return [
        f"Du code est committé avant `{shown}` : le contrat s'écrit et se fait valider en premier, "
        "sinon il décrit ce qui a été fait au lieu de commander ce qui doit l'être. Ce contrôle lit "
        "l'ordre des commits : une réécriture d'historique le contourne, c'est un signal fort, pas une garantie."
    ]


def without_revision(text: str) -> str:
    """Le critère amputé de sa mention de révision — c'est lui qu'on compare à la version validée."""
    return REVISION.split(text)[0].strip()


def validation_commit(repo: Path, name: str) -> str | None:
    """Le plus ancien commit dont la definition of done porte sa ligne de validation."""
    shown = dod_path(repo, name).relative_to(repo).as_posix()
    for sha in reversed(git(repo, "log", "--format=%H", "--", shown).stdout.split()):
        blob = git(repo, "show", f"{sha}:{shown}")
        if blob.returncode == 0 and VALIDATION.search(blob.stdout):
            return sha
    return None


def frozen_criteria(repo: Path, name: str) -> list[str]:
    """Un critère validé ne se réécrit pas en silence : toute retouche porte sa révision datée."""
    sha = validation_commit(repo, name)
    if sha is None:
        return []
    shown = dod_path(repo, name).relative_to(repo).as_posix()
    validated = criteria(git(repo, "show", f"{sha}:{shown}").stdout)
    current = criteria(dod_path(repo, name).read_text())
    problems = [
        f"{dod} a disparu de « Ce qui devra marcher » depuis la validation : rétrécir la cible jusqu'à "
        f"ce que le vert soit atteignable, c'est changer de contrat sans le dire. Le remettre, ou "
        f"faire revalider la definition of done."
        for dod in validated
        if dod not in current
    ]
    return problems + [
        f"{dod} a changé depuis la validation sans porter de révision. Ajouter sous le critère une "
        f"ligne « Révision AAAA-MM-JJ — … » qui dit ce qui change et pourquoi."
        for dod, text in current.items()
        if without_revision(text) != without_revision(validated.get(dod, "")) and not REVISION.search(text)
    ]


def verify_dod(repo: Path, name: str, base: str = DEFAULT_BASE) -> list[str]:
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
    if not VALIDATION.search(text):
        problems.append(
            "Validation absente : la section « Validation » porte « Validé par <qui> le <AAAA-MM-JJ> ». "
            "Un titre de section vide ne dit pas qui a accepté ce que le travail devra produire."
        )
    problems += [f"Gabarit non rempli : {found}" for found in sorted(set(PLACEHOLDER.findall(text)))]
    return problems + frozen_criteria(repo, name) + dod_antedates_code(repo, name, base)


def verify_attestations(repo: Path, name: str) -> list[str]:
    """Un critère non démontré ne peut pas se noyer : chacun porte son verdict."""
    tracked_paths = proven_paths(repo)
    problems = [f"Modification non committée sur un chemin prouvé : {p}" for p in dirty_paths(repo, tracked_paths)]
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
        elif refusals := command_refusals(entry.command, dod, repo):
            problems.append(f"{dod} — commande de preuve irrecevable : {refusals[0]}")
        elif not entry.trees:
            problems.append(f"{dod} — attestation sans empreinte : elle ne prouve aucun contenu.")
        elif missing := sorted(set(tracked_paths) - set(entry.trees)):
            problems.append(
                f"{dod} — attestation partielle : {', '.join(missing)} n'y figure pas, donc peut être "
                f"réécrit sans que la preuve périme. Relancer la preuve."
            )
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
# `make` en est sorti le 2026-08-30 : `make test`, et même `make help`, démontraient n'importe quel
# critère, parce que le lien commande-critère ne s'applique qu'aux commandes qui lancent pytest.
ALLOWED_PROVE_PREFIXES = (
    ("uv", "run", "--frozen", "pytest"),
    ("uv", "run", "--frozen", "alembic"),
    ("uv", "run", "--frozen", "python"),
)
# Collecter n'est pas exécuter : ces drapeaux rendent 0 sans qu'aucun test ne tourne.
COLLECT_ONLY = ("--collect-only", "--co")
# Drapeaux qui détournent la collecte ou la configuration : ils chargent un plugin, retirent le test
# cité, ou font lire une configuration que la relecture de la PR ne verra pas.
DIVERTING = ("-c", "-p", "--rootdir", "--confcutdir", "--import-mode", "--deselect", "--ignore")
# La commande est recopiée verbatim dans l'attestation et dans le journal, sur un dépôt public.
CREDENTIALS = re.compile(r"://[^/\s]*:[^/\s]*@")
# Un `-k` qui ne désigne rien sort en 0 avec « 2129 deselected » : la seule marque qu'un test a
# réellement tourné est le compte de succès.
PYTEST_RAN = re.compile(r"\b\d+ passed\b")
PYTEST_FAILED = re.compile(r"\b\d+ (failed|error)")


def runs_a_file(argv: list[str]) -> bool:
    """Vrai quand `python` reçoit un fichier à exécuter, et non `-c`, `-m`, `--version` ou rien."""
    after = argv[argv.index("python") + 1 :]
    return bool(after) and not after[0].startswith("-")


def selections(argv: list[str]) -> list[str]:
    """Ce que la commande désigne explicitement : la valeur de chaque `-k`, et chaque identifiant `::`."""
    named = [value for flag, value in zip(argv, argv[1:], strict=False) if flag == "-k"]
    named += [arg[2:] for arg in argv if arg.startswith("-k") and len(arg) > 2]
    return named + [arg.split("::", 1)[1] for arg in argv if "::" in arg and not arg.startswith("-")]


def designates(selection: str, token: str) -> bool:
    """Une sélection désigne le critère si elle le nomme, sans le retrancher ni viser son homonyme."""
    return re.search(rf"{token}(?!\d)", selection.lower()) is not None and not re.search(r"\bnot\b", selection)


def outside_repository(argv: list[str]) -> list[str]:
    """Les arguments qui désignent quelque chose hors du dépôt — y compris la valeur d'un `--drapeau=`."""
    values = [arg.split("=", 1)[1] if arg.startswith("-") and "=" in arg else arg for arg in argv]
    return [value for value in values if value.startswith(("/", "../")) or "/../" in value]


def tracked(repo: Path, path: str) -> bool:
    """Vrai quand git suit ce chemin — une preuve exécute du code que la relecture peut lire."""
    return git(repo, "ls-files", "--error-unmatch", "--", path).returncode == 0


def command_refusals(command: str, dod: str, repo: Path) -> list[str]:
    """Ce qui disqualifie une commande de preuve, avant même de l'exécuter."""
    try:
        argv = shlex.split(command)
    except ValueError as erreur:
        return [f"`{command}` est illisible comme ligne de commande : {erreur}."]
    token = dod.lower().replace("-", "_")
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
    if CREDENTIALS.search(command):
        refusals.append(
            "La commande porte des identifiants en clair : elle est recopiée telle quelle dans "
            "l'attestation et dans le journal, sur un dépôt public. Passer par la configuration."
        )
    if outside := outside_repository(argv):
        refusals.append(
            f"`{outside[0]}` est hors du dépôt : une preuve n'exécute et n'écrit que ce que la "
            f"relecture de la PR peut lire."
        )
    if "python" in argv and not runs_a_file(argv):
        refusals.append(
            "`python` doit exécuter un fichier du dépôt : `-c`, `-m`, `--version` et le REPL "
            "prouvent du code que la relecture ne verra jamais."
        )
    elif not outside and "python" in argv and not tracked(repo, argv[argv.index("python") + 1]):
        refusals.append(
            f"`{argv[argv.index('python') + 1]}` n'est pas suivi par git : une preuve exécute du "
            f"code versionné, pas un fichier de travail que personne ne relira."
        )
    if "pytest" in argv and (diverting := [flag for flag in DIVERTING if flag in argv]):
        refusals.append(
            f"`{diverting[0]}` détourne la collecte ou la configuration de pytest : la preuve ne "
            f"porterait plus sur ce que le dépôt exécute."
        )
    if "pytest" in argv and not any(designates(selection, token) for selection in selections(argv)):
        refusals.append(
            f"La commande ne désigne aucun test nommé d'après {dod} : seule la valeur d'un `-k` ou un "
            f"identifiant `…::test_{token}_…` fait ce lien, pas le mot `{token}` posé ailleurs sur la "
            f"ligne. Nomme le test `test_{token}_…` et sélectionne-le."
        )
    return refusals


def scope_fingerprint(repo: Path) -> str:
    """Empreinte unique du périmètre prouvé — c'est elle qui distingue deux états du code."""
    return short_hash("\n".join(f"{path} {sha}" for path, sha in sorted(fingerprints(repo).items())))


def reds(repo: Path, name: str, dod: str) -> list[dict[str, str]]:
    """Les rouges journalisés pour ce critère, du plus ancien au plus récent."""
    return [e for e in events(repo, name) if e.get("Résultat") == "rouge" and e.get("Critère") == dod]


def red_before_green(repo: Path, name: str, dod: str) -> list[str]:
    """Le cycle exige un rouge journalisé, joué sur un code différent de celui qui rend le vert."""
    journaled = reds(repo, name, dod)
    if not journaled:
        return [
            f"{dod} n'a aucun rouge journalisé : un test qu'on n'a jamais vu échouer ne démontre pas "
            f"que c'est lui qui tient le critère. Enregistrer d'abord `make paved-road-advance "
            f"DOD={dod} RED=1 CMD='…'`, puis implémenter."
        ]
    if journaled[-1].get("Empreinte du périmètre") == scope_fingerprint(repo):
        return [
            f"{dod} : le rouge et le vert portent sur le même code — rien n'a été implémenté entre les "
            f"deux, donc le cycle n'a pas eu lieu. Écrire le code qui fait passer le test, le committer, "
            f"puis rejouer le vert."
        ]
    return []


def acceptable_proof(repo: Path, name: str, dod: str, command: str) -> dict[str, str]:
    """Contrôles communs au rouge et au vert — le critère existe, et la commande est recevable."""
    expected = criteria(dod_path(repo, name).read_text())
    if dod not in expected:
        raise ValueError(f"{dod} ne figure pas dans {dod_path(repo, name).relative_to(repo)}")
    if refusals := command_refusals(command, dod, repo):
        raise ValueError("\n".join(refusals))
    return expected


# Why: le rouge ne demande pas d'arbre propre, le vert si. On écrit le test, on le voit échouer,
# on écrit le code, et on commit les deux ensemble. L'empreinte journalisée est celle du HEAD au
# moment du rouge — c'est-à-dire du code d'avant, ce qui suffit à la distinguer de celle du vert.
def record_red(repo: Path, name: str, dod: str, command: str) -> tuple[int, str]:
    """Journalise l'échec attendu d'un critère — sans lui, `prove` refuse le vert."""
    acceptable_proof(repo, name, dod, command)
    code, output = run_command(repo, shlex.split(command))
    if code == 0:
        raise ValueError(
            f"`{command}` sort en 0 : un test qui passe avant que le code existe n'est pas un test. "
            f"Écrire le test qui échoue faute d'implémentation, puis enregistrer son rouge."
        )
    if "pytest" in shlex.split(command) and not PYTEST_FAILED.search(output):
        raise ValueError(
            f"`{command}` sort en {code} mais aucun test n'a échoué : un `-k` qui ne désigne rien "
            f"sort en 5, un fichier absent en 4. Écrire le test d'abord, puis enregistrer son rouge."
        )
    mark = scope_fingerprint(repo)
    append_event(
        repo,
        name,
        f"red {dod}",
        [
            ("État", current_state(events(repo, name))),
            ("Résultat", "rouge"),
            ("Critère", dod),
            ("Commande", f"`{command}`"),
            ("Code de sortie", str(code)),
            ("Empreinte du périmètre", mark),
        ],
    )
    return code, mark


def prove(repo: Path, name: str, dod: str, command: str) -> Attestation:
    """Exécute la commande et range l'attestation du critère — seule écriture sous attestations/."""
    expected = acceptable_proof(repo, name, dod, command)
    tracked = proven_paths(repo)
    if dirty := dirty_paths(repo, tracked):
        raise ValueError(f"Committer d'abord le code prouvé, sinon l'empreinte ne le décrit pas : {', '.join(dirty)}")
    code, output = run_command(repo, shlex.split(command))
    if code == 0 and "pytest" in shlex.split(command) and not PYTEST_RAN.search(output):
        raise ValueError(f"`{command}` sort en 0 sans qu'aucun test n'ait tourné : la preuve serait vide.")
    if code == 0 and (missing := red_before_green(repo, name, dod)):
        raise ValueError("\n".join(missing))
    entry = Attestation(
        dod=dod,
        criterion=expected[dod],
        command=command,
        exit_code=code,
        output=truncate(output),
        trees={path: tree_fingerprint(repo, path) for path in tracked},
        proven=code == 0,
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
