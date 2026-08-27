"""Ligne de base du paved road — coût, durée et frictions, calculés sur les données déjà collectées."""

import logging
import statistics
import subprocess
import tomllib
from collections import Counter, defaultdict
from datetime import datetime, timedelta, timezone

import httpx
from sqlalchemy import func, select

from web import config
from web.cron import BROKEN_STATUSES
from web.db import get_db
from web.models import Conversation, CronRun, UsageEvent

logger = logging.getLogger(__name__)

REPO = "gip-inclusion/autometa"
# L'API GitHub plafonne la pagination à 1000 éléments par requête.
MAX_PAGES = 10

TOKEN_COLUMNS = (
    "usage_input_tokens",
    "usage_output_tokens",
    "usage_cache_creation_tokens",
    "usage_cache_read_tokens",
)

# Why: `conv_type` ne vaut que `exploration`, `knowledge` ou `report` — rien n'identifie un parcours
# paved road. `pr_url IS NOT NULL` est le seul proxy disponible, et il est biaisé : à écrire en clair.
PROXY_CAVEAT = (
    "Proxy : une « fonctionnalité » est ici une conversation dont `pr_url` est non nul. `conv_type` ne "
    "connaît que `exploration`, `knowledge` et `report` : rien ne distingue aujourd'hui une conversation "
    "paved road d'une exploration ordinaire. Ce proxy ne retient que les parcours ayant abouti à une PR, "
    "donc il **surestime le succès** et sous-estime le coût moyen — les abandons sont invisibles."
)


def distribution(values: list[float]) -> dict:
    """Effectif, médiane et maximum d'une série."""
    if not values:
        return {"count": 0, "median": None, "max": None}
    return {"count": len(values), "median": statistics.median(values), "max": max(values)}


def feature_runs(session, since: datetime) -> list[dict]:
    """Conversations ayant produit une PR sur la fenêtre — durée, tokens et nombre de tours."""
    turns = (
        select(UsageEvent.conversation_id, func.count().label("turns"))
        .where(UsageEvent.kind == "turn")
        .group_by(UsageEvent.conversation_id)
        .subquery()
    )
    rows = session.execute(
        select(Conversation, func.coalesce(turns.c.turns, 0))
        .outerjoin(turns, turns.c.conversation_id == Conversation.id)
        .where(Conversation.pr_url.is_not(None), Conversation.created_at >= since)
        .order_by(Conversation.created_at)
    ).all()
    return [
        {
            "id": conv.id,
            "title": conv.title,
            "pr_url": conv.pr_url,
            "minutes": (conv.updated_at - conv.created_at).total_seconds() / 60,
            "turns": turn_count,
            "tokens": {column: getattr(conv, column) for column in TOKEN_COLUMNS},
            "tokens_total": sum(getattr(conv, column) for column in TOKEN_COLUMNS),
        }
        for conv, turn_count in rows
    ]


def human_takeovers(session, since: datetime) -> dict:
    """Fréquence des reprises humaines — signalements, motifs et demandes de réponse."""
    rows = session.execute(
        select(
            Conversation.pr_url,
            Conversation.flagged_at,
            Conversation.flag_reason,
            Conversation.needs_response,
        ).where(Conversation.created_at >= since)
    ).all()
    return {
        "conversations": len(rows),
        "with_pr": sum(1 for row in rows if row.pr_url),
        "flagged": sum(1 for row in rows if row.flagged_at is not None),
        "needs_response": sum(1 for row in rows if row.needs_response),
        "flag_reasons": Counter(row.flag_reason for row in rows if row.flagged_at is not None).most_common(),
    }


def dashboard_health(session, since: datetime) -> list[dict]:
    """Santé des tableaux de bord par semaine ISO — exécutions, échecs et durée médiane."""
    rows = session.execute(
        select(CronRun.started_at, CronRun.status, CronRun.duration_ms).where(CronRun.started_at >= since)
    ).all()
    by_week = defaultdict(list)
    for row in rows:
        year, week, _ = row.started_at.isocalendar()
        by_week[f"{year}-S{week:02d}"].append(row)

    weeks = []
    for week, runs in sorted(by_week.items()):
        durations = [run.duration_ms for run in runs if run.duration_ms is not None]
        weeks.append({
            "week": week,
            "runs": len(runs),
            "failed": sum(1 for run in runs if run.status in BROKEN_STATUSES),
            "median_duration_ms": statistics.median(durations) if durations else None,
        })
    return weeks


def github_get(path: str, params: dict, key: str | None = None) -> list[dict]:
    """Un appel à l'API GitHub sur le dépôt ; `key` déballe les réponses enveloppées."""
    headers = {"Authorization": f"Bearer {config.GITHUB_TOKEN}", "Accept": "application/vnd.github+json"}
    response = httpx.get(f"https://api.github.com/repos/{REPO}{path}", params=params, headers=headers, timeout=30)
    response.raise_for_status()
    payload = response.json()
    return payload[key] if key else payload


def github_pages(path: str, params: dict, key: str | None = None):
    """Itère les pages d'un endpoint GitHub jusqu'à épuisement, ou jusqu'à MAX_PAGES."""
    for page in range(1, MAX_PAGES + 1):
        items = github_get(path, {**params, "per_page": 100, "page": page}, key)
        yield from items
        if len(items) < 100:
            return
    logger.warning("github_pages: %s tronqué à %d pages", path, MAX_PAGES)


def gate_noise(since: datetime) -> dict:
    """Bruit des gates — échecs par job CI et part des PR mergées ayant échoué au moins une fois."""
    # Why: interroger workflow par workflow garde chaque requête sous le plafond de 1000 runs que
    # `/actions/runs` atteint silencieusement sur une fenêtre de 90 jours.
    created = f">={since.date().isoformat()}"
    runs = []
    for workflow in github_get("/actions/workflows", {"per_page": 100}, "workflows"):
        runs += github_pages(
            f"/actions/workflows/{workflow['id']}/runs",
            {"created": created, "exclude_pull_requests": "true"},
            "workflow_runs",
        )

    # Why: le `name` d'un run est unique par déclencheur (« PR #149 ») pour les workflows dynamiques ;
    # seul le `path` identifie le workflow lui-même.
    workflows = Counter(run["path"] for run in runs)
    failed_runs = [run for run in runs if run["conclusion"] == "failure"]

    jobs = Counter()
    for run in failed_runs:
        for job in github_get(f"/actions/runs/{run['id']}/jobs", {"per_page": 100}, "jobs"):
            if job["conclusion"] == "failure":
                jobs[(run["path"], job["name"])] += 1

    merged = []
    for pull in github_pages("/pulls", {"state": "closed", "sort": "updated", "direction": "desc"}):
        if datetime.fromisoformat(pull["updated_at"]) < since:
            break
        if pull["merged_at"]:
            merged.append(pull)

    branches_with_failure = {run["head_branch"] for run in failed_runs}
    return {
        "runs": len(runs),
        "failed_runs": len(failed_runs),
        "by_workflow": [
            {"workflow": path, "runs": total, "failed": sum(1 for run in failed_runs if run["path"] == path)}
            for path, total in workflows.most_common()
        ],
        "by_job": [
            {"workflow": workflow, "job": job, "failures": count, "workflow_runs": workflows[workflow]}
            for (workflow, job), count in jobs.most_common()
        ],
        "merged_pulls": len(merged),
        "merged_pulls_with_failure": sum(1 for pull in merged if pull["head"]["ref"] in branches_with_failure),
    }


def git_output(*args: str) -> str:
    return subprocess.run(["git", *args], capture_output=True, text=True, check=True).stdout


def coverage_floors_at(sha: str) -> tuple[float | None, float | None]:
    """Les deux planchers `fail_under` déclarés dans pyproject.toml à une révision donnée."""
    tools = tomllib.loads(git_output("show", f"{sha}:pyproject.toml")).get("tool", {})
    return (
        tools.get("coverage", {}).get("report", {}).get("fail_under"),
        tools.get("diff_cover", {}).get("fail_under"),
    )


def coverage_floor_drift(since: datetime) -> list[dict]:
    """Changements des planchers de couverture (globale et diff) sur la fenêtre, valeur d'entrée incluse."""
    day = since.date().isoformat()
    commits = git_output("log", "-1", f"--until={day}", "--format=%H %aI", "--", "pyproject.toml").splitlines()
    commits += git_output("log", "--reverse", f"--since={day}", "--format=%H %aI", "--", "pyproject.toml").splitlines()

    drift = []
    previous = None
    for line in commits:
        sha, authored_at = line.split()
        floors = coverage_floors_at(sha)
        if floors != previous:
            drift.append({"date": authored_at[:10], "sha": sha[:8], "coverage": floors[0], "diff_cover": floors[1]})
            previous = floors
    return drift


def collect(days: int = 90) -> dict:
    """Tous les indicateurs de la ligne de base sur les `days` derniers jours."""
    since = datetime.now(timezone.utc) - timedelta(days=days)
    with get_db() as session:
        runs = feature_runs(session, since)
        takeovers = human_takeovers(session, since)
        health = dashboard_health(session, since)
    return {
        "days": days,
        "since": since,
        "feature_runs": runs,
        "duration_minutes": distribution([run["minutes"] for run in runs]),
        "tokens_total": distribution([run["tokens_total"] for run in runs]),
        "turns": distribution([run["turns"] for run in runs]),
        "tokens_by_column": {column: sum(run["tokens"][column] for run in runs) for column in TOKEN_COLUMNS},
        "human_takeovers": takeovers,
        "dashboard_health": health,
        "coverage_floor_drift": coverage_floor_drift(since),
        "gate_noise": gate_noise(since) if config.GITHUB_TOKEN else None,
    }


def table(headers: list[str], rows: list[list]) -> list[str]:
    """Un tableau Markdown, ou une mention explicite quand la série est vide."""
    if not rows:
        return ["_Aucune donnée sur la fenêtre._"]
    head = ["| " + " | ".join(headers) + " |", "|" + "|".join(["---"] * len(headers)) + "|"]
    return head + ["| " + " | ".join("—" if cell is None else str(cell) for cell in row) + " |" for row in rows]


def number(value: float | None) -> str:
    return "—" if value is None else f"{value:,.1f}".replace(",", " ")


def render_gate_noise(noise: dict | None) -> list[str]:
    """Section « bruit des gates » ; l'absence de jeton GitHub est dite, pas masquée."""
    if noise is None:
        return ["_`GITHUB_TOKEN` absent : indicateur non calculé._"]
    merged, retried = noise["merged_pulls"], noise["merged_pulls_with_failure"]
    share = f"{100 * retried / merged:.0f} %" if merged else "—"
    return [
        f"{noise['runs']} exécutions de workflow, dont {noise['failed_runs']} en échec. "
        f"{retried} des {merged} PR mergées ont connu au moins un échec ({share}).",
        "",
        *table(
            ["workflow", "exécutions", "échecs"],
            [[row["workflow"], row["runs"], row["failed"]] for row in noise["by_workflow"]],
        ),
        "",
        *table(
            ["workflow", "job", "échecs", "taux"],
            [
                [row["workflow"], row["job"], row["failures"], f"{100 * row['failures'] / row['workflow_runs']:.0f} %"]
                for row in noise["by_job"]
            ],
        ),
    ]


def render(baseline: dict) -> str:
    """Rend la ligne de base en Markdown."""
    takeovers = baseline["human_takeovers"]
    lines = [
        f"# Ligne de base du paved road — {baseline['days']} derniers jours",
        "",
        f"Fenêtre : depuis le {baseline['since'].date().isoformat()}. "
        "Sources : base applicative, API GitHub, historique git. Aucune collecte nouvelle.",
        "",
        PROXY_CAVEAT,
        "",
        "## 1. Coût et durée par fonctionnalité",
        "",
        *table(
            ["indicateur", "effectif", "médiane", "maximum"],
            [
                [label, series["count"], number(series["median"]), number(series["max"])]
                for label, series in (
                    ("durée (minutes)", baseline["duration_minutes"]),
                    ("tokens (total)", baseline["tokens_total"]),
                    ("tours", baseline["turns"]),
                )
            ],
        ),
        "",
        *table(
            ["colonne de tokens", "cumul sur la fenêtre"],
            [[column, total] for column, total in baseline["tokens_by_column"].items()],
        ),
        "",
        "## 2. Fréquence des reprises humaines",
        "",
        *table(
            ["indicateur", "valeur"],
            [
                ["conversations créées", takeovers["conversations"]],
                ["dont avec PR", takeovers["with_pr"]],
                ["signalées (`flagged_at`)", takeovers["flagged"]],
                ["en attente de réponse (`needs_response`)", takeovers["needs_response"]],
            ],
        ),
        "",
        *table(["motif de signalement", "occurrences"], [list(item) for item in takeovers["flag_reasons"]]),
        "",
        "## 3. Bruit des gates",
        "",
        *render_gate_noise(baseline["gate_noise"]),
        "",
        "## 4. Santé des tableaux de bord",
        "",
        *table(
            ["semaine", "exécutions", "échecs", "durée médiane (ms)"],
            [
                [row["week"], row["runs"], row["failed"], row["median_duration_ms"]]
                for row in baseline["dashboard_health"]
            ],
        ),
        "",
        "## 5. Dérive du plancher de couverture",
        "",
        *table(
            ["date", "commit", "`coverage.report`", "`diff_cover`"],
            [[row["date"], row["sha"], row["coverage"], row["diff_cover"]] for row in baseline["coverage_floor_drift"]],
        ),
        "",
    ]
    return "\n".join(lines)
