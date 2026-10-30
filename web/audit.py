"""Audit qualité des conversations de prod, outil local des développeurs : fichiers sous data/audit, grille versionnée."""

import collections
import datetime as dt
import json
import math
import re
from pathlib import Path
from typing import Literal

from pydantic import BaseModel, TypeAdapter, ValidationError

from lib import notion
from lib.pii import redact_nir
from lib.query import CallerType, execute_metabase_query
from lib.slack import post_message

from . import config
from .helpers import utcnow
from .redaction import EMAIL, redact, secret_kinds

AUDIT_DIR = config.DATA_DIR / "audit"
GRID = config.BASE_DIR / "plugins" / "retrospect" / "skills" / "conversations" / "grille.json"
# Même valeur que le `limit` des requêtes de messages : une page pleine en annonce une autre.
PAGE = 1000
MESSAGES_SQL = (
    "select id, conversation_id, type, timestamp, length(content) as len, left(content, 40000) as content "
    "from messages where id > {{after}} and id <= {{last}} order by id limit 1000"
)
CONTEXT_SQL = (
    "select id, conversation_id, type, timestamp, length(content) as len, left(content, 40000) as content "
    "from messages where type in ('user', 'assistant') and id > {{after}} and id <= {{first}} "
    "and conversation_id in (select distinct conversation_id from messages where id > {{first}} and id <= {{last}}) "
    "order by id limit 1000"
)
CONVERSATIONS_SQL = (
    "select id, user_id, title, forked_from, created_at from conversations where id in "
    "(select distinct conversation_id from messages where id > {{first}} and id <= {{last}})"
)
# Why: les ids suivent l'ordre d'insertion, pas les horodatages — un fork recopie l'historique avec ses dates
# d'origine. Une borne est donc le dernier id avant le premier message horodaté à partir de cet instant.
BOUND_SQL = (
    "select coalesce((select min(id) from messages where timestamp >= {{at}}::timestamptz), "
    "(select max(id) + 1 from messages), 1) - 1 as id"
)
SEVERITIES = ("CRITIQUE", "GRAVE", "MOYEN", "MINEUR")
SQL_ERROR = re.compile(
    r"does not exist|Perhaps you meant|syntax error at or near|UndefinedColumn|UndefinedTable|invalid input syntax|"
    r"operator does not exist|ProgrammingError|psycopg\.errors|sqlalchemy\.exc",
    re.I,
)
TMP_WRITE = re.compile(r"(?:>|cat >|tee )\s*(/tmp/[\w./-]+)")

# Why: la description d'un incident de données personnelles tend à citer la donnée elle-même ; les sorties diffusées
# (rapport, Slack, Notion) n'en donnent que la nature.
PERSONAL_DATA_CRITERIA = {"C15", "G35", "G37"}

Severity = Literal["CRITIQUE", "GRAVE", "MOYEN", "MINEUR"]


class AuditError(Exception):
    """Refus explicable à l'utilisateur du skill."""


class Criterion(BaseModel):
    code: str
    family: str
    definition: str
    detection: Literal["regex", "mixte", "lecture"]
    on: list[Literal["user", "assistant", "tool_use", "tool_result"]] = []
    pattern: str | None = None
    status: Literal["proposé", "actif", "retiré"] = "proposé"
    added_at: str = ""
    added_by: str = ""


class Finding(BaseModel):
    conversation_id: str
    message_id: int
    criterion: str
    cause: Literal[
        "K-doc",
        "K-outil-absent",
        "K-outil-casse",
        "K-consigne-absente",
        "K-consigne-ignoree",
        "K-plateforme",
        "K-modele",
    ]
    severity: Severity
    verification: Literal["confirmé", "partiel", "non vérifié"] = "non vérifié"
    description: str
    evidence: str
    action: str
    correction: str = ""
    run_id: int | None = None
    timestamp: str | None = None
    issue: str | None = None
    posted_at: str | None = None
    origin: Literal["audit", "extraction"] = "audit"

    @property
    def key(self) -> str:
        return f"{self.conversation_id}:{self.message_id}:{self.criterion}"


class Verdict(BaseModel):
    conversation_id: str
    verdict: Literal["propre", "problèmes mineurs", "problèmes sérieux"]
    summary: str


class OffGrid(BaseModel):
    conversation_id: str
    message_id: int | None = None
    symptom: str
    mechanism: str
    why_serious: str
    detection: str = "lecture"


class Verification(BaseModel):
    key: str
    status: Literal["confirmé", "partiel", "infirmé"]
    severity: Severity
    correction: str = ""
    note: str = ""


class AuditOutput(BaseModel):
    verdicts: list[Verdict]
    findings: list[Finding]
    off_grid: list[OffGrid] = []


class Issue(BaseModel):
    code: str = ""
    title: str
    criteria: list[str]
    signature: str
    status: Literal["ouvert", "livré", "régression", "résolu"] = "ouvert"
    action: str
    findings: list[str] = []
    occurrences: int = 0
    first_seen: str | None = None
    last_seen: str | None = None
    notion_page_id: str | None = None
    created_at: str = ""


class Lesson(BaseModel):
    code: str = ""
    title: str
    kind: Literal["knowledge", "skill", "prompt", "hook", "code"]
    target: str
    fact: str
    proposal: str
    findings: list[str]
    signature: str
    status: Literal["proposée", "acceptée", "appliquée", "vérifiée", "retirée"] = "proposée"
    created_at: str = ""
    updated_at: str = ""


class Run(BaseModel):
    id: int
    kind: Literal["daily", "weekly"]
    after_message_id: int
    last_message_id: int
    daily_runs: list[int] = []
    conversation_id: str | None = None
    started_by: str | None = None
    started_at: str
    finished_at: str | None = None
    status: Literal["ouvert", "clos", "abandonné"] = "ouvert"
    stats: dict = {}
    summary: str = ""
    posted_at: str | None = None


def read_json(path: Path, default):
    return json.loads(path.read_text()) if path.exists() else default


def write_json(path: Path, data) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(data, ensure_ascii=False, indent=1, default=str))


def run_dir(run_id: int) -> Path:
    return AUDIT_DIR / "runs" / str(run_id)


def work_dir(run_id: int) -> Path:
    return run_dir(run_id) / "work"


def load_runs() -> list[Run]:
    return sorted(
        (Run.model_validate_json(p.read_text()) for p in (AUDIT_DIR / "runs").glob("*/run.json")), key=lambda r: r.id
    )


def load_run(run_id: int) -> Run:
    path = run_dir(run_id) / "run.json"
    if not path.exists():
        raise AuditError(f"Run {run_id} introuvable.")
    return Run.model_validate_json(path.read_text())


def save_run(run: Run) -> None:
    write_json(run_dir(run.id) / "run.json", run.model_dump())


def load_findings(run_id: int) -> list[Finding]:
    return [Finding(**f) for f in read_json(run_dir(run_id) / "findings.json", [])]


def save_findings(run_id: int, findings: list[Finding]) -> None:
    write_json(run_dir(run_id) / "findings.json", [f.model_dump() for f in findings])


def all_findings() -> list[Finding]:
    return [f for run in load_runs() for f in load_findings(run.id)]


def load_criteria() -> list[Criterion]:
    """La grille versionnée, amendée par les critères proposés, activés ou retirés en local."""
    criteria = {c["code"]: c for c in read_json(GRID, [])}
    criteria.update({c["code"]: c for c in read_json(AUDIT_DIR / "criteria.json", [])})
    return [Criterion(**c) for c in criteria.values()]


def save_criteria(criteria: list[Criterion]) -> None:
    shared = {c["code"]: c for c in read_json(GRID, [])}
    write_json(AUDIT_DIR / "criteria.json", [c.model_dump() for c in criteria if c.model_dump() != shared.get(c.code)])


def load_issues() -> list[Issue]:
    return [Issue(**i) for i in read_json(AUDIT_DIR / "issues.json", [])]


def save_issues(issues: list[Issue]) -> None:
    write_json(AUDIT_DIR / "issues.json", [i.model_dump() for i in issues])


def load_lessons() -> list[Lesson]:
    return [Lesson(**i) for i in read_json(AUDIT_DIR / "lessons.json", [])]


def criterion_definitions() -> dict[str, str]:
    return {c.code: c.definition for c in load_criteria()}


def shareable(finding: Finding, definitions: dict[str, str]) -> str:
    """Ce qu'on peut diffuser d'un incident : pour des données personnelles, la nature du problème, pas la description."""
    if finding.criterion in PERSONAL_DATA_CRITERIA:
        return definitions.get(finding.criterion, finding.criterion)
    return finding.description


def next_code(codes) -> int:
    """Numéro suivant d'une série de codes lettre + nombre (S1, L2…)."""
    return 1 + max((int(code[1:]) for code in codes if code[1:].isdigit()), default=0)


def mask(text: str) -> str:
    """Secrets, NIR et adresses e-mail retirés : ce qui est stocké hors transcription."""
    return EMAIL.sub("***", redact_nir(redact(text)))


def masked[M: BaseModel](model: M) -> M:
    """Le même objet, chaque champ texte masqué un par un : masquer le JSON entier en casserait l'échappement."""
    return model.model_copy(update={k: mask(v) for k, v in model.model_dump().items() if isinstance(v, str)})


def scrub(text: str) -> str:
    """Masquage des transcriptions : secrets et NIR ; les e-mails restent, l'auditeur en a besoin."""
    return redact_nir(redact(text))


def prod_rows(sql: str, **params: int | str) -> list[dict]:
    if config.ENV.is_server:
        raise AuditError("L'audit des conversations ne tourne qu'en local, jamais sur une instance déployée.")
    # Base 19 : la base applicative de prod telle que l'instance Metabase « stats » la voit, en lecture seule.
    result = execute_metabase_query(
        instance="stats", database_id=19, sql=sql, caller=CallerType.AGENT, timeout=120, params=params
    )
    if not result.success:
        raise AuditError(f"Requête Metabase en échec : {result.error}")
    return [dict(zip(result.data["columns"], row)) for row in result.data["rows"]]


def fetch_messages(sql: str, after: int, **params: int) -> list[dict]:
    rows = []
    while True:
        page = prod_rows(sql, after=after, **params)
        rows += page
        if len(page) < PAGE:
            return rows
        after = page[-1]["id"]


def watermark() -> int | None:
    closed = [r for r in load_runs() if r.kind == "daily" and r.status == "clos"]
    return closed[-1].last_message_id if closed else None


def start(kind: str, since: dt.date | None = None, until: dt.date | None = None) -> Run:
    """Ouvre un run : fenêtre de messages depuis le filigrane (quotidien) ou runs quotidiens à synthétiser."""
    runs = load_runs()
    if opened := [r.id for r in runs if r.status == "ouvert"]:
        raise AuditError(
            f"Run {opened[0]} encore ouvert : le clore ou l'abandonner (finish) avant d'en ouvrir un autre."
        )
    daily_runs = []
    if kind == "daily":
        after = watermark()
        if after is not None and since:
            raise AuditError(f"Le filigrane fixe le début de la fenêtre (après le message {after}) : retirer --since.")
        if after is None and not since:
            raise AuditError("Premier run : donner --since (date du premier jour audité).")
        if since:
            after = prod_rows(BOUND_SQL, at=since.isoformat())[0]["id"]
        # Why: des insertions concurrentes peuvent valider un id inférieur après un id supérieur ; s'arrêter dix
        # minutes avant maintenant laisse le temps aux transactions en cours de se terminer.
        bound = until.isoformat() if until else (utcnow() - dt.timedelta(minutes=10)).isoformat()
        last = prod_rows(BOUND_SQL, at=bound)[0]["id"]
    else:
        weeklies = [r for r in runs if r.kind == "weekly" and r.status == "clos"]
        done = max((d for w in weeklies for d in w.daily_runs), default=0)
        dailies = [r for r in runs if r.kind == "daily" and r.status == "clos" and r.id > done]
        if not dailies:
            raise AuditError("Aucun run quotidien clos depuis le dernier run hebdomadaire.")
        daily_runs = [r.id for r in dailies]
        after, last = dailies[0].after_message_id, dailies[-1].last_message_id
    if last <= after:
        raise AuditError("Aucun nouveau message dans la fenêtre.")
    run = Run(
        id=runs[-1].id + 1 if runs else 1,
        kind=kind,
        after_message_id=after,
        last_message_id=last,
        daily_runs=daily_runs,
        conversation_id=config.agent_conversation_id(),
        started_by=config.agent_user_email(),
        started_at=utcnow().isoformat(),
    )
    save_run(run)
    return run


def is_fork_copy(message: dict, conv: dict) -> bool:
    """Message recopié par un fork depuis la conversation d'origine, où il a déjà été audité."""
    return bool(conv["forked_from"]) and dt.datetime.fromisoformat(
        str(message["timestamp"])
    ) < dt.datetime.fromisoformat(str(conv["created_at"]))


def parse(message: dict) -> tuple[str, str | None]:
    """Texte lisible d'un message et, pour un appel d'outil, le nom de l'outil."""
    try:
        payload = json.loads(message["content"])
    except ValueError:
        return message["content"], None
    if not isinstance(payload, dict):
        return message["content"], None
    if message["type"] == "tool_use":
        tool_input = payload.get("input") or {}
        return tool_input.get("command") or json.dumps(tool_input, ensure_ascii=False), payload.get("tool")
    output = payload.get("output", message["content"])
    if isinstance(output, dict):
        output = output.get("output", json.dumps(output, ensure_ascii=False))
    return str(output), None


def clip(text: str, head: int, tail: int = 0) -> str:
    if len(text) <= head + tail + 50:
        return text
    return text[:head] + f"\n…[{len(text) - head - tail} car. coupés]…\n" + (text[-tail:] if tail else "")


def detect(messages: list[dict], rules: list[tuple[str, set[str], re.Pattern]]) -> dict[str, list[tuple[int, str]]]:
    """Indices automatiques par critère : expressions de la grille, plus ce qui demande une séquence ou un compte."""
    hits = collections.defaultdict(list)
    after_error = False
    for m in messages:
        text, _ = parse(m)
        if kinds := secret_kinds(m["content"]):
            hits["G28"].append((m["id"], ", ".join(kinds)))
        for code, on, rx in rules:
            if m["type"] in on and (match := rx.search(text)):
                hits[code].append((m["id"], scrub(match.group(0))[:160]))
        if m["type"] == "tool_result" and SQL_ERROR.search(text):
            after_error = True
        elif m["type"] == "tool_use" and after_error:
            hits["B5"].append((m["id"], "relance après une erreur SQL"))
            after_error = False
        if m["type"] == "assistant" and m["len"] > 10000:
            hits["D20"].append((m["id"], f"{m['len']} car."))
    n_user = sum(m["type"] == "user" for m in messages)
    n_tool = sum(m["type"] == "tool_use" for m in messages)
    if messages and n_tool / max(n_user, 1) > 20:
        hits["B11"].append((messages[0]["id"], f"{n_tool} appels d'outil pour {n_user} messages utilisateur"))
    return dict(hits)


def render(conv: dict, messages: list[dict], context: list[dict], previous: list[Finding]) -> str:
    lines = [
        f"# {conv['title']}",
        f"conversation={conv['id']} utilisateur={conv['user_id']} fork_de={conv['forked_from']}",
    ]
    if context:
        lines += ["", "## Contexte : messages antérieurs, déjà audités"]
        lines += [f"\n[{m['id']}] {m['type'].upper()}\n{clip(scrub(m['content']), 1500)}" for m in context]
    if previous:
        lines += ["", "## Incidents déjà relevés sur cette conversation (ne pas les signaler à nouveau)"]
        lines += [f"- {f.key} {f.severity} : {f.description[:200]}" for f in previous]
    lines += ["", "## Messages à auditer"]
    # Why: masquer avant de couper — une coupure au milieu d'un secret laisserait une forme que le masquage ne reconnaît plus.
    for m in messages:
        text, tool = parse(m)
        head = f"[{m['id']} {str(m['timestamp'])[:19]}]"
        if m["type"] == "user":
            lines.append(f"\n## {head} USER\n{clip(scrub(m['content']), 6000, 1000)}")
        elif m["type"] == "assistant":
            lines.append(f"\n## {head} ASSISTANT\n{clip(scrub(m['content']), 12000, 2000)}")
        elif m["type"] == "tool_use":
            lines.append(f"\n### {head} TOOL_USE {tool}\n{clip(scrub(text), 3500, 500)}")
        else:
            lines.append(f"\n### {head} TOOL_RESULT (len={m['len']})\n{clip(scrub(text), 3500, 800)}")
    return scrub("\n".join(lines))


def write_batches(index: list[dict], count: int, out: Path) -> list[dict]:
    """Répartit les conversations en lots de taille comparable, les plus longues d'abord."""
    bins = [[] for _ in range(max(1, min(count, len(index))))]
    sizes = [0] * len(bins)
    for item in sorted(index, key=lambda x: -x["chars"]):
        k = sizes.index(min(sizes))
        bins[k].append(item)
        sizes[k] += item["chars"]
    batches = []
    for k, items in enumerate(bins):
        lines = [f"# Lot {k:02d} — {len(items)} conversations, {sizes[k]} caractères\n"]
        for item in items:
            lines.append(
                f"## {item['id']}\n- titre : {item['title']}\n- utilisateur : {item['user']}\n"
                f"- fichier : tx/{item['id']}.md\n- messages utilisateur={item['n_user']} appels d'outil={item['n_tool']}"
            )
            lines += [
                f"- détection `{code}` ({len(v)}) : " + " ; ".join(f"[{i}] {s}" for i, s in v[:6])
                for code, v in item["hits"].items()
            ]
            lines.append("")
        path = out / f"batch_{k:02d}.md"
        path.write_text("\n".join(lines))
        batches.append({"id": f"{k:02d}", "file": str(path), "conversations": len(items)})
    return batches


def extract(run_id: int, batches: int | None = None) -> dict:
    """Écrit transcriptions masquées, détections et lots d'un run quotidien dans son dossier de travail."""
    run = load_run(run_id)
    if run.kind != "daily" or run.status != "ouvert":
        raise AuditError(f"Run {run_id} : l'extraction ne concerne qu'un run quotidien ouvert.")
    window = {"first": run.after_message_id, "last": run.last_message_id}
    excluded = {r.conversation_id for r in load_runs() if r.conversation_id}
    convs = {c["id"]: c for c in prod_rows(CONVERSATIONS_SQL, **window) if c["id"] not in excluded}
    fetched = [
        m
        for m in fetch_messages(MESSAGES_SQL, run.after_message_id, last=run.last_message_id)
        if m["conversation_id"] in convs
    ]
    copies = {m["id"] for m in fetched if is_fork_copy(m, convs[m["conversation_id"]])}
    messages = [m for m in fetched if m["id"] not in copies]
    context = fetch_messages(CONTEXT_SQL, 0, **window) + [
        m for m in fetched if m["id"] in copies and m["type"] in ("user", "assistant")
    ]
    out = work_dir(run_id)
    (out / "tx").mkdir(parents=True, exist_ok=True)
    by_conv, context_by_conv, previous = (collections.defaultdict(list) for _ in range(3))
    for m in messages:
        by_conv[m["conversation_id"]].append(m)
    for m in context:
        context_by_conv[m["conversation_id"]].append(m)
    for f in all_findings():
        previous[f.conversation_id].append(f)
    rules = [(c.code, set(c.on), re.compile(c.pattern)) for c in load_criteria() if c.status == "actif" and c.pattern]
    writers = collections.defaultdict(set)
    for m in messages:
        if m["type"] == "tool_use":
            for path in TMP_WRITE.findall(parse(m)[0]):
                writers[path].add(m["conversation_id"])
    collisions = {path: sorted(ids) for path, ids in writers.items() if len(ids) > 1}
    index = []
    for conv in convs.values():
        conv_messages = by_conv[conv["id"]]
        if not conv_messages:
            continue
        text = render(conv, conv_messages, context_by_conv[conv["id"]][-20:], previous[conv["id"]])
        (out / "tx" / f"{conv['id']}.md").write_text(text)
        hits = detect(conv_messages, rules)
        if shared := [path for path, ids in collisions.items() if conv["id"] in ids]:
            hits["G29"] = [(conv_messages[0]["id"], f"/tmp partagé : {path}") for path in shared]
        index.append({
            "id": conv["id"],
            "user": conv["user_id"],
            "title": (conv["title"] or "")[:90],
            "chars": len(text),
            "n_user": sum(m["type"] == "user" for m in conv_messages),
            "n_tool": sum(m["type"] == "tool_use" for m in conv_messages),
            "hits": hits,
        })
    with (out / "messages.jsonl").open("w") as f:
        for m in context + messages:
            f.write(json.dumps({**m, "content": scrub(m["content"])}, default=str, ensure_ascii=False) + "\n")
    write_json(out / "convs.json", list(convs.values()))
    stats = {
        "conversations": len(index),
        "utilisateurs": len({i["user"] for i in index}),
        "messages": len(messages),
        "types": dict(collections.Counter(m["type"] for m in messages)),
        "détections": dict(collections.Counter(code for i in index for code, v in i["hits"].items() for _ in v)),
        "tmp_partagés": len(collisions),
    }
    summary = {
        "stats": stats,
        "batches": write_batches(index, batches or math.ceil(len(index) / 12), out),
        "secrets": [
            {"conversation_id": i["id"], "message_id": message_id, "kinds": kinds}
            for i in index
            for message_id, kinds in i["hits"].get("G28", [])
        ],
        "tmp_collisions": collisions,
    }
    write_json(out / "summary.json", summary)
    save_run(run.model_copy(update={"stats": stats}))
    record(run_id, AuditOutput(verdicts=[], findings=secret_findings(summary["secrets"])).model_dump_json())
    return summary


def certain_kinds(kinds: str) -> list[str]:
    """Les sortes de secret sans ambiguïté ; un paramètre d'URL nommé comme un secret reste un indice pour l'auditeur."""
    return [k for k in kinds.split(", ") if k != "paramètre d'URL sensible"]


def secret_findings(secrets: list[dict]) -> list[Finding]:
    """Un secret d'une forme sans ambiguïté est un fait établi par l'extraction : incident CRITIQUE, déjà vérifié."""
    return [
        Finding(
            conversation_id=s["conversation_id"],
            message_id=s["message_id"],
            criterion="G28",
            cause="K-plateforme",
            severity="CRITIQUE",
            verification="confirmé",
            description=f"Secret en clair dans un message persisté : {', '.join(certain)}.",
            evidence="Détection automatique à l'extraction ; valeur masquée.",
            action="Faire tourner le secret, masquer le message, corriger le chemin qui l'a exposé.",
            origin="extraction",
        )
        for s in secrets
        if (certain := certain_kinds(s["kinds"]))
    ]


def show(run_id: int, message_ids: list[int]) -> list[dict]:
    """Messages complets, masqués, tels qu'extraits pour ce run."""
    path = work_dir(run_id) / "messages.jsonl"
    if not path.exists():
        raise AuditError(f"Run {run_id} : rien d'extrait.")
    wanted = set(message_ids)
    # Why: une ligne par message, coupée sur \n seulement — json.dumps laisse U+2028 brut, splitlines() le couperait.
    return [m for m in map(json.loads, filter(None, path.read_text().split("\n"))) if m["id"] in wanted]


def record(run_id: int, payload: str) -> dict:
    """Valide et enregistre la sortie d'audit d'un run quotidien, sans doublon d'un run à l'autre."""
    run = load_run(run_id)
    if run.kind != "daily" or run.status != "ouvert":
        raise AuditError(f"Run {run_id} : on n'enregistre des incidents que dans un run quotidien ouvert.")
    output = AuditOutput.model_validate_json(payload)
    codes = {c.code for c in load_criteria()}
    errors = [f"{f.key} : critère inconnu" for f in output.findings if f.criterion not in codes]
    errors += [
        f"{f.key} : message hors de la fenêtre du run"
        for f in output.findings
        if not run.after_message_id < f.message_id <= run.last_message_id
    ]
    if errors:
        raise AuditError("\n".join(errors))
    timestamps = {m["id"]: str(m["timestamp"]) for m in show(run_id, [f.message_id for f in output.findings])}
    seen = {f.key for f in all_findings()}
    findings = load_findings(run_id)
    before = len(findings)
    for f in output.findings:
        if f.key in seen:
            continue
        seen.add(f.key)
        findings.append(masked(f).model_copy(update={"run_id": run_id, "timestamp": timestamps.get(f.message_id)}))
    save_findings(run_id, findings)
    verdicts = {v["conversation_id"]: v for v in read_json(run_dir(run_id) / "verdicts.json", [])}
    verdicts.update({v.conversation_id: masked(v).model_dump() for v in output.verdicts})
    write_json(run_dir(run_id) / "verdicts.json", list(verdicts.values()))
    off_grid = read_json(run_dir(run_id) / "off_grid.json", [])
    off_grid += [o for o in (masked(o).model_dump() for o in output.off_grid) if o not in off_grid]
    write_json(run_dir(run_id) / "off_grid.json", off_grid)
    added = len(findings) - before
    return {"enregistrés": added, "doublons": len(output.findings) - added}


def findings_for(run_id: int) -> dict:
    """Incidents et observations hors grille d'un run, ou des runs quotidiens qu'un run hebdomadaire synthétise."""
    run = load_run(run_id)
    scope = run.daily_runs if run.kind == "weekly" else [run_id]
    return {
        "findings": [{"key": f.key, **f.model_dump()} for r in scope for f in load_findings(r)],
        "off_grid": [o for r in scope for o in read_json(run_dir(r) / "off_grid.json", [])],
        "issues": [i.model_dump() for i in load_issues()],
    }


def upsert_issues(payload: str) -> list[Issue]:
    """Crée ou met à jour des problèmes systémiques et les relie à leurs incidents."""
    items = TypeAdapter(list[Issue]).validate_json(payload)
    by_key = {f.key: f for f in all_findings()}
    if unknown := [k for item in items for k in item.findings if k not in by_key]:
        raise AuditError("Incidents inconnus : " + ", ".join(unknown))
    issues = {i.code: i for i in load_issues()}
    next_number = next_code(issues)
    for item in items:
        if not item.code:
            item.code, next_number = f"S{next_number}", next_number + 1
        existing = issues.get(item.code)
        keys = sorted(set(existing.findings if existing else []) | set(item.findings))
        days = sorted(by_key[k].timestamp[:10] for k in keys if by_key[k].timestamp)
        days = sorted(filter(None, [existing.first_seen, *days, existing.last_seen] if existing else days))
        status = item.status
        if existing and existing.status == "livré" and set(keys) - set(existing.findings):
            status = "régression"
        issues[item.code] = item.model_copy(
            update={
                "findings": keys,
                "occurrences": len(keys),
                "first_seen": days[0] if days else None,
                "last_seen": days[-1] if days else None,
                "status": status,
                "notion_page_id": item.notion_page_id or (existing.notion_page_id if existing else None),
                "created_at": existing.created_at if existing else utcnow().isoformat(),
            }
        )
        for k in item.findings:
            by_key[k].issue = item.code
    save_issues(list(issues.values()))
    for run in load_runs():
        save_findings(run.id, [by_key.get(f.key, f) for f in load_findings(run.id)])
    return [issues[item.code] for item in items]


def upsert_lessons(payload: str) -> list[Lesson]:
    """Crée ou réécrit des leçons : un fait durable, sa cible et le diff proposé, adossés à des incidents ou observations."""
    items = TypeAdapter(list[Lesson]).validate_json(payload)
    known = {f.key for f in all_findings()} | {
        f"off_grid:{o['conversation_id']}:{o['message_id']}"
        for run in load_runs()
        for o in read_json(run_dir(run.id) / "off_grid.json", [])
    }
    if unknown := [k for item in items for k in item.findings if k not in known]:
        raise AuditError("Incidents inconnus : " + ", ".join(unknown))
    lessons = {lesson.code: lesson for lesson in load_lessons()}
    next_number, now = next_code(lessons), utcnow().isoformat()
    for item in items:
        if not item.code:
            item.code, next_number = f"L{next_number}", next_number + 1
        existing = lessons.get(item.code)
        lessons[item.code] = item.model_copy(
            update={
                "findings": sorted(set(existing.findings if existing else []) | set(item.findings)),
                "created_at": existing.created_at if existing else now,
                "updated_at": now,
            }
        )
    write_json(AUDIT_DIR / "lessons.json", [lesson.model_dump() for lesson in lessons.values()])
    return [lessons[item.code] for item in items]


def propose_criteria(payload: str) -> list[Criterion]:
    criteria = load_criteria()
    codes = {c.code for c in criteria}
    proposed = TypeAdapter(list[Criterion]).validate_json(payload)
    if taken := [c.code for c in proposed if c.code in codes]:
        raise AuditError("Codes déjà pris : " + ", ".join(taken))
    for c in proposed:
        c.status, c.added_at, c.added_by = "proposé", utcnow().date().isoformat(), config.agent_user_email() or "audit"
    save_criteria(criteria + proposed)
    return proposed


def set_criterion_status(code: str, status: str) -> Criterion:
    criteria = load_criteria()
    match = [c for c in criteria if c.code == code]
    if not match:
        raise AuditError(f"Critère {code} introuvable.")
    match[0].status = status
    save_criteria(criteria)
    return match[0]


def link(base_url: str, conversation_id: str) -> str:
    return f"{base_url}/explorations/{conversation_id}"


def severity_counts(findings: list[Finding]) -> str:
    counts = collections.Counter(f.severity for f in findings)
    return ", ".join(f"{counts[s]} {s}" for s in SEVERITIES if counts[s]) or "aucun incident"


def slack_messages(run_id: int, base_url: str) -> list[dict]:
    """Messages Slack d'un run, à relire avant publication. Aucun extrait de conversation, aucune mention."""
    run = load_run(run_id)
    if run.kind == "weekly":
        return [weekly_digest(run)]
    summary = read_json(work_dir(run_id) / "summary.json", {})
    authors = {c["id"]: c["user_id"] for c in read_json(work_dir(run_id) / "convs.json", [])}
    findings = load_findings(run_id)
    definitions = criterion_definitions()
    secrets = collections.defaultdict(set)
    for s in summary.get("secrets", []):
        secrets[s["conversation_id"]].update(certain_kinds(s["kinds"]))
    messages = [
        {
            "text": f":rotating_light: Secret exposé ({', '.join(sorted(kinds))}), valeur non reproduite : {link(base_url, cid)}"
        }
        for cid, kinds in secrets.items()
        if kinds
    ]
    messages += [
        {
            "text": f":warning: Correction ({f.criterion}, {f.severity}) — conversation de "
            f"{authors.get(f.conversation_id, '?')}\n{f.description[:300]}\nValeur correcte : {f.correction[:300]}\n"
            f"{link(base_url, f.conversation_id)}",
            "findings": [f.key],
        }
        for f in findings
        if f.severity in ("CRITIQUE", "GRAVE")
        and f.verification == "confirmé"
        and f.criterion in {"A1", "A2", "G30", "G31"}
        and not f.posted_at
    ]
    messages.append({
        "text": f":clipboard: Audit des conversations, run {run.id} (messages {run.after_message_id + 1} à "
        f"{run.last_message_id}) : {run.stats.get('conversations', '?')} conversations, {severity_counts(findings)}.",
        "thread": [
            f"• {f.criterion} {f.severity} — {shareable(f, definitions)[:200]} {link(base_url, f.conversation_id)}"
            for f in findings
            if f.severity in ("CRITIQUE", "GRAVE")
        ],
    })
    return messages


def weekly_digest(run: Run) -> dict:
    findings = [f for r in run.daily_runs for f in load_findings(r)]
    touched = {f.issue for f in findings if f.issue}
    issues = load_issues()
    # Why: l'absence se mesure au dernier message audité, pas à la date du jour — un audit en retard ou rejoué sur une
    # semaine passée ne doit pas déclarer absents des problèmes qu'il n'a pas encore pu revoir.
    latest = max((f.timestamp[:10] for f in all_findings() if f.timestamp), default=utcnow().date().isoformat())
    fortnight = (dt.date.fromisoformat(latest) - dt.timedelta(days=14)).isoformat()
    groups = {
        "En régression": [i for i in issues if i.status == "régression"],
        "Nouveaux": [i for i in issues if i.created_at >= run.started_at],
        "Persistants": [i for i in issues if i.code in touched and i.created_at < run.started_at],
        "Absents depuis deux semaines, à fermer": [
            i for i in issues if i.status in ("ouvert", "livré") and i.last_seen and i.last_seen < fortnight
        ],
    }
    lines = [
        f":bar_chart: Audit hebdomadaire, runs {', '.join(map(str, run.daily_runs))} : {severity_counts(findings)}."
    ]
    lines += [
        f"*{title}* : " + " ; ".join(f"{i.code} {i.title} ({i.occurrences})" for i in group)
        for title, group in groups.items()
        if group
    ]
    return {"text": "\n".join(lines)}


def post_slack(run_id: int, channel: str, base_url: str) -> int:
    """Publie les messages du run dans le canal choisi, le détail en fil de discussion ; une seule fois par run."""
    run = load_run(run_id)
    if run.posted_at:
        raise AuditError(f"Run {run_id} déjà publié le {run.posted_at}.")
    if not config.SLACK_BOT_TOKEN:
        raise AuditError("SLACK_BOT_TOKEN absent.")
    messages = slack_messages(run_id, base_url)
    for message in messages:
        ts = post_message(config.SLACK_BOT_TOKEN, channel, message["text"])
        if not ts:
            raise AuditError("Slack a refusé le message.")
        for reply in message.get("thread", []):
            post_message(config.SLACK_BOT_TOKEN, channel, reply, thread_ts=ts)
    now = utcnow().isoformat()
    posted = {k for message in messages for k in message.get("findings", [])}
    save_findings(
        run_id, [f.model_copy(update={"posted_at": now}) if f.key in posted else f for f in load_findings(run_id)]
    )
    save_run(run.model_copy(update={"posted_at": now}))
    return len(messages)


def ticket(code: str, base_url: str) -> str:
    """Le ticket Notion d'un problème systémique, en markdown."""
    issue = next((i for i in load_issues() if i.code == code), None)
    if issue is None:
        raise AuditError(f"Problème {code} introuvable.")
    keys = set(issue.findings)
    linked = sorted((f for f in all_findings() if f.key in keys), key=lambda f: SEVERITIES.index(f.severity))
    causes = collections.Counter(f.cause for f in linked)
    definitions = criterion_definitions()
    return "\n".join([
        f"# {issue.code} — {issue.title}",
        "",
        f"Statut : {issue.status} · {issue.occurrences} incidents · vu du {issue.first_seen} au {issue.last_seen}",
        f"Critères : {', '.join(issue.criteria)}",
        "",
        "## Incidents",
        *(
            f"- {f.severity} {f.criterion} — {shareable(f, definitions)[:300]} ({link(base_url, f.conversation_id)})"
            for f in linked[:20]
        ),
        "",
        "## Causes",
        *(f"- {cause} : {n}" for cause, n in causes.most_common()),
        "",
        "## Plan",
        issue.action,
        "",
        "## Critère de fin",
        f"La signature est absente des audits pendant deux semaines : `{issue.signature}`",
    ])


def finish(run_id: int, summary: str = "", abandon: bool = False) -> Run:
    """Clôt le run (le filigrane avance) ou l'abandonne (le suivant reprendra la même fenêtre)."""
    run = load_run(run_id)
    if run.status != "ouvert":
        raise AuditError(f"Run {run_id} déjà {run.status}.")
    run = run.model_copy(
        update={"status": "abandonné" if abandon else "clos", "finished_at": utcnow().isoformat(), "summary": summary}
    )
    save_run(run)
    return run


def lot_outputs(run_id: int) -> dict[str, AuditOutput]:
    """Sorties des auditeurs du run, par lot ; un fichier invalide arrête tout, avec son erreur."""
    outputs, errors = {}, []
    for path in sorted(work_dir(run_id).glob("audit_*.json")):
        try:
            outputs[path.stem.removeprefix("audit_")] = AuditOutput.model_validate_json(path.read_text())
        except ValidationError as e:
            errors.append(
                f"{path.name} : {e.error_count()} erreur(s), dont {e.errors()[0]['loc']} {e.errors()[0]['msg']}"
            )
    if errors:
        raise AuditError("\n".join(errors))
    return outputs


def verify_list(run_id: int) -> list[dict]:
    """Écrit, pour chaque lot, les incidents CRITIQUE et GRAVE à contre-vérifier (verify_NN.json)."""
    summary = []
    for lot, output in lot_outputs(run_id).items():
        serious = [f for f in output.findings if f.severity in ("CRITIQUE", "GRAVE")]
        if serious:
            write_json(work_dir(run_id) / f"verify_{lot}.json", [{"key": f.key, **f.model_dump()} for f in serious])
        summary.append({
            "lot": lot,
            "conversations": len(output.verdicts),
            "incidents": dict(collections.Counter(f.severity for f in output.findings)),
            "hors_grille": len(output.off_grid),
            "à_vérifier": len(serious),
        })
    return summary


def merge(run_id: int) -> dict:
    """Applique les contre-vérifications (verdict_NN.json) et remplace les incidents audités du run : on peut le relancer."""
    run = load_run(run_id)
    if run.posted_at or any(f.posted_at for f in load_findings(run_id)):
        raise AuditError(f"Run {run_id} déjà publié sur Slack : ses incidents ne se réécrivent plus.")
    checks = {
        v.key: v
        for path in work_dir(run_id).glob("verdict_*.json")
        for v in TypeAdapter(list[Verification]).validate_json(path.read_text())
    }
    outputs = lot_outputs(run_id)
    merged, dropped, unchecked = AuditOutput(verdicts=[], findings=[]), [], []
    for output in outputs.values():
        merged.verdicts += output.verdicts
        merged.off_grid += output.off_grid
        for f in output.findings:
            check = checks.get(f.key)
            if f.severity in ("CRITIQUE", "GRAVE") and check is None:
                unchecked.append(f.key)
            if check and check.status == "infirmé":
                dropped.append(f.key)
                continue
            # Why: seule une contre-vérification établit un incident ; ce que l'auditeur écrit de lui-même n'en vaut pas une.
            update = {"verification": "non vérifié"}
            if check:
                update = {
                    "verification": check.status,
                    "severity": check.severity,
                    "correction": check.correction or f.correction,
                }
            merged.findings.append(f.model_copy(update=update))
    audited = {f.key for output in outputs.values() for f in output.findings}
    save_findings(run_id, [f for f in load_findings(run_id) if f.origin == "extraction" or f.key not in audited])
    return {**record(run_id, merged.model_dump_json()), "infirmés": dropped, "non_vérifiés": unchecked}


def report(run_id: int, base_url: str) -> Path:
    """Rapport markdown du run, sans extrait de conversation ni adresse e-mail : rapport.md dans le dossier du run."""
    run = load_run(run_id)
    lines = weekly_report(run, base_url) if run.kind == "weekly" else daily_report(run, base_url)
    path = run_dir(run_id) / "rapport.md"
    path.write_text("\n".join(lines) + "\n")
    return path


def daily_report(run: Run, base_url: str) -> list[str]:
    findings = load_findings(run.id)
    definitions = criterion_definitions()
    summary = read_json(work_dir(run.id) / "summary.json", {})
    secrets = collections.defaultdict(set)
    for s in summary.get("secrets", []):
        secrets[s["conversation_id"]].update(certain_kinds(s["kinds"]))
    lines = [
        f"# Audit des conversations — run {run.id}",
        "",
        f"Messages {run.after_message_id + 1} à {run.last_message_id} · {run.stats.get('conversations', '?')} "
        f"conversations · {severity_counts(findings)} · run {run.status}",
    ]
    if any(secrets.values()):
        lines += ["", "## Secrets exposés", ""]
        lines += [f"- {', '.join(sorted(k))} : {link(base_url, cid)}" for cid, k in secrets.items() if k]
    serious = sorted(
        (f for f in findings if f.severity in ("CRITIQUE", "GRAVE")), key=lambda f: SEVERITIES.index(f.severity)
    )
    if serious:
        lines += ["", "## Incidents CRITIQUE et GRAVE"]
    for f in serious:
        lines += [
            "",
            f"### {f.severity} {f.criterion} — {definitions.get(f.criterion, '')[:80]}",
            "",
            shareable(f, definitions),
            "",
            f"- Vérification : {f.verification} · cause : {f.cause} · {link(base_url, f.conversation_id)}",
            f"- Action : {f.action}",
        ]
        if f.correction:
            lines.append(f"- Correction : {f.correction}")
    others = collections.Counter((f.criterion, f.severity) for f in findings if f.severity in ("MOYEN", "MINEUR"))
    if others:
        lines += ["", "## Autres incidents", "", "| Critère | MOYEN | MINEUR |", "|---|---|---|"]
        lines += [
            f"| {code} {definitions.get(code, '')[:60]} | {others[(code, 'MOYEN')]} | {others[(code, 'MINEUR')]} |"
            for code in sorted({code for code, _ in others})
        ]
    off_grid = read_json(run_dir(run.id) / "off_grid.json", [])
    if off_grid:
        lines += ["", f"## Observations hors grille ({len(off_grid)})", ""]
        lines += [f"- {o['symptom'][:200]}" for o in off_grid]
    return lines


def weekly_report(run: Run, base_url: str) -> list[str]:
    findings = [f for r in run.daily_runs for f in load_findings(r)]
    touched = {f.issue for f in findings if f.issue}
    lines = [
        f"# Audit hebdomadaire — run {run.id}",
        "",
        f"Runs quotidiens {', '.join(map(str, run.daily_runs))} · {severity_counts(findings)} · run {run.status}",
        "",
        "## Problèmes systémiques",
        "",
        "| Code | Problème | Statut | Incidents |",
        "|---|---|---|---|",
    ]
    issues = [i for i in load_issues() if i.code in touched or i.created_at >= run.started_at]
    lines += [f"| {i.code} | {i.title} | {i.status} | {i.occurrences} |" for i in issues]
    for i in issues:
        lines += ["", f"### {i.code} — {i.title}", "", i.action, "", f"Critère de fin : `{i.signature}`"]
    proposed = [c for c in load_criteria() if c.status == "proposé"]
    if proposed:
        lines += ["", "## Critères proposés", ""]
        lines += [f"- **{c.code}** ({c.detection}) : {c.definition}" for c in proposed]
    lessons = [lesson for lesson in load_lessons() if lesson.status in ("proposée", "acceptée")]
    if lessons:
        lines += ["", "## Leçons"]
    for lesson in lessons:
        lines += [
            "",
            f"### {lesson.code} — {lesson.title}",
            "",
            f"`{lesson.target}` · {lesson.status}",
            "",
            lesson.fact,
        ]
        lines += (
            ["", "```diff", lesson.proposal.rstrip(), "```"] if lesson.kind in ("knowledge", "skill", "prompt") else []
        )
    return lines


def export_notion(run_id: int, parent_url: str, base_url: str) -> str:
    """Publie le rapport du run comme sous-page de la page Notion donnée ; renvoie l'URL de la page créée."""
    if not config.NOTION_TOKEN:
        raise AuditError("NOTION_TOKEN absent.")
    path = report(run_id, base_url)
    title = path.read_text().splitlines()[0].removeprefix("# ")
    page = notion.notion_request(
        "POST",
        "pages",
        {
            "parent": {"page_id": notion.db_id_from_url(parent_url)},
            "properties": {"title": {"title": [{"text": {"content": title}}]}},
        },
    )
    blocks = notion.markdown_to_blocks(path.read_text())
    for i in range(0, len(blocks), 100):
        notion.notion_request("PATCH", f"blocks/{page['id']}/children", {"children": blocks[i : i + 100]})
    return page["url"]
