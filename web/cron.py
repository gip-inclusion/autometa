"""Cron runner for data refresh scripts."""

import argparse
import collections
import datetime as dt
import hashlib
import logging
import os
import re
import shutil
import signal
import subprocess
import sys
import tempfile
import threading
import time
from collections.abc import Callable
from pathlib import Path

import sentry_sdk
from botocore.exceptions import BotoCoreError, ClientError
from sqlalchemy import JSON, Column, DateTime, Integer, MetaData, Table, delete, func, select, text
from sqlalchemy.dialects.postgresql import insert as pg_insert
from sqlalchemy.exc import SQLAlchemyError
from sqlalchemy.orm import Session

from lib import dashboard_api
from web.helpers import now_local, sanitize_for_log, utcnow
from web.s3 import S3Store

from . import alerts, config, publications, s3
from .database import get_db
from .db import get_engine
from .log import setup_logging
from .models import CronRun, CronTaskState, Dashboard, DashboardPublication
from .publications import list_publications
from .sentry import init_sentry

logger = logging.getLogger(__name__)

# Defaults
DEFAULT_TIMEOUT = 300  # 5 minutes
MAX_OUTPUT_SIZE = 50_000
MAX_LOGGED_LINES = 20_000

SCHEDULE_PRESETS = {
    "daily": "0 6 * * *",
    "weekly": "0 6 * * 1",
    "monthly": "0 6 1 * *",
}
_CRONTAB_TO_CADENCE = {crontab: token for token, crontab in SCHEDULE_PRESETS.items()}

DASHBOARD_BATCH = "tableaux-internes"
# Why: partagées en externe, les publications ont leur propre lot, sans budget — une publication
# cassée doit se voir chaque jour, pas être sautée parce qu'un TDB interne a mangé le temps.
PUBLICATION_BATCH = "tableaux-publies"
# Heure UTC à laquelle cron.json démarre chaque lot. Sentry attend le check-in à cette heure-là :
# la déduire de la cadence ferait manquer leur créneau aux lots qui ne partent pas à 06:00.
BATCH_HOURS = {"synchros": 2, "maintenance": 6, "tableaux-internes": 6, "tableaux-publies": 6, "xl": 6}
FACADE_AUDIT_SCHEMA = "dashboard_storage"


def cadence(schedule: str) -> str:
    """Reduce a stored schedule (crontab or cadence token) to a runner cadence: daily|weekly|monthly."""
    # Why: the 06:00 dispatcher only honors day-level scheduling. is_valid_schedule restricts stored
    # values to the three presets; this daily fallback only guards legacy or backfilled rows.
    if schedule in SCHEDULE_PRESETS:
        return schedule
    return _CRONTAB_TO_CADENCE.get(schedule, "daily")


def is_valid_schedule(schedule: str) -> bool:
    """A storable schedule: a cadence token (daily|weekly|monthly) or its exact preset crontab."""
    # Why: the 06:00 dispatcher only honors these three cadences. Accepting an arbitrary crontab would
    # store a schedule that silently runs daily — reject it until a real scheduler lands.
    return schedule in SCHEDULE_PRESETS or schedule in _CRONTAB_TO_CADENCE


# Cron statuses that count as "broken" for Slack alerts
BROKEN_STATUSES = {"failure", "timeout"}


def parse_frontmatter_text(content: str) -> dict:
    """Parse YAML front-matter from a string.

    Returns dict of key-value pairs. Returns {} if no front-matter.
    """
    if not content.startswith("---"):
        return {}

    parts = content.split("---", 2)
    if len(parts) < 3:
        return {}

    meta = {}
    for line in parts[1].strip().split("\n"):
        if ":" in line:
            key, value = line.split(":", 1)
            meta[key.strip().lower()] = value.strip()
    return meta


def parse_frontmatter(md_path: Path) -> dict:
    """Parse YAML front-matter from a markdown file.

    Returns dict of key-value pairs. Returns {} if no front-matter.
    """
    try:
        content = md_path.read_text()
    except OSError:
        return {}

    return parse_frontmatter_text(content)


def is_enabled(meta: dict) -> bool:
    return meta.get("cron", "true").lower() not in ("false", "no", "0", "off")


def get_timeout(meta: dict) -> int:
    try:
        return int(meta["timeout"])
    except KeyError, ValueError:
        return DEFAULT_TIMEOUT


def get_schedule(meta: dict) -> str:
    return meta.get("schedule", "daily").lower()


def get_batch(meta: dict) -> str | None:
    """Le lot déclaré par la tâche. Chaque lot est une ligne de cron.json, donc un conteneur."""
    return meta.get("batch", "").strip().lower() or None


def is_due(schedule: str) -> bool:
    reduced = cadence(schedule)
    if reduced == "weekly":
        return now_local().weekday() == 0  # Monday
    if reduced == "monthly":
        return now_local().day == 1
    return True


def next_cron_run(schedule: str, now=None):
    """Prochain départ des lots de tableaux de bord, en UTC comme la planification Scalingo, selon la cadence."""
    now = now or utcnow()
    target = now.replace(hour=BATCH_HOURS[DASHBOARD_BATCH], minute=0, second=0, microsecond=0)
    reduced = cadence(schedule)
    if reduced == "weekly":
        days_ahead = (0 - target.weekday()) % 7
        if days_ahead == 0 and now >= target:
            days_ahead = 7
        return target + dt.timedelta(days=days_ahead)
    if reduced == "monthly":
        first_this = target.replace(day=1)
        if now < first_this:
            return first_this
        if target.month == 12:
            return first_this.replace(year=target.year + 1, month=1)
        return first_this.replace(month=target.month + 1)
    if now >= target:
        return target + dt.timedelta(days=1)
    return target


def set_cron_enabled(app_slug: str, enabled: bool) -> bool:
    """Enable/disable a cron task. Dashboards → `dashboards.cron_enabled`; system tasks → `cron_task_states`."""
    with get_db() as session:
        dashboard = session.scalar(select(Dashboard).where(Dashboard.slug == app_slug))
        if dashboard is not None:
            dashboard.cron_enabled = enabled
            return True

        task_dir = config.CRON_DIR / app_slug
        if not (task_dir / "cron.py").exists():
            return False

        # Why: CRON.md est baké dans l'image — l'y écrire ne survivrait pas au déploiement suivant.
        # Revenir au défaut du dépôt efface l'exception, sans quoi le front-matter serait gelé.
        if enabled == is_enabled(parse_frontmatter(task_dir / "CRON.md")):
            session.execute(delete(CronTaskState).where(CronTaskState.slug == app_slug))
        else:
            session.merge(CronTaskState(slug=app_slug, enabled=enabled, updated_at=utcnow()))
        return True


def stored_task_states() -> dict[str, bool]:
    """État d'activation des tâches système enregistré en base, par slug."""
    # Why: une base injoignable ne doit pas empêcher les tâches système de tourner — le
    # front-matter reprend la main, comme avant que l'état ne vive en base.
    try:
        with get_db() as session:
            return dict(session.execute(select(CronTaskState.slug, CronTaskState.enabled)).all())
    except SQLAlchemyError as e:
        logger.warning("cron : état d'activation illisible, front-matter utilisé (%s)", e)
        return {}


def discover_from_dir(base_dir: Path, md_name: str, tier: str) -> list[dict]:
    """Discover cron tasks from a directory."""
    tasks = []
    if not base_dir.exists():
        return tasks

    for folder in sorted(base_dir.iterdir()):
        if not folder.is_dir():
            continue
        cron_script = folder / "cron.py"
        if not cron_script.exists():
            continue

        meta = parse_frontmatter(folder / md_name)
        batch = get_batch(meta)
        if batch is None:
            # Why: un lot fourre-tout absorbait toute tâche muette, tableaux de bord compris, et
            # personne ne voyait la chaîne grandir. Un lot non déclaré est désormais une erreur.
            raise ValueError(f"cron {folder.name}: aucun batch déclaré dans {md_name}")

        tasks.append({
            "slug": folder.name,
            "title": meta.get("title", folder.name),
            "tier": tier,
            "path": str(folder),
            "cron_path": str(cron_script),
            "enabled": is_enabled(meta),
            "timeout": get_timeout(meta),
            "schedule": get_schedule(meta),
            "batch": batch,
        })

    return tasks


def discover_from_s3() -> list[dict]:
    """Cron tasks for apps flagged `has_cron`; cron metadata from the DB row, script presence from S3."""
    if not config.S3_BUCKET:
        return []

    with get_db() as session:
        rows = session.execute(
            select(
                Dashboard.slug,
                Dashboard.title,
                Dashboard.cron_enabled,
                Dashboard.cron_timeout,
                Dashboard.cron_schedule,
            )
            .where(Dashboard.has_cron, ~Dashboard.is_archived)
            .order_by(Dashboard.slug)
        ).all()

    if not rows:
        return []

    # Why: one list_objects_v2 over the bucket beats one HeadObject per dashboard — discovery
    # runs on every cron pass, and a per-slug exists() check floods S3 calls (and DEBUG logs).
    cron_slugs = {
        entry["path"].rsplit("/", 1)[0]
        for entry in s3.interactive.list_files("", raise_errors=True)
        if entry["path"].endswith("/cron.py")
    }

    tasks = []
    for slug, title, enabled, timeout, schedule in rows:
        if slug not in cron_slugs:
            logger.warning("Dashboard %s has has_cron=true but no cron.py on S3", slug)
            continue

        tasks.append({
            "slug": slug,
            "title": title,
            "tier": "app",
            "source": "s3",
            "path": slug,
            "cron_path": f"{slug}/cron.py",
            "enabled": enabled,
            "timeout": timeout,
            "schedule": schedule,
            "batch": DASHBOARD_BATCH,
        })

    return tasks


def discover_publications() -> list[dict]:
    """Tasks for active, non-paused publications; schedule/timeout from parent dashboard."""
    if not config.S3_BUCKET:
        return []
    with get_db() as session:
        rows = session.execute(
            select(
                DashboardPublication.dashboard_slug,
                DashboardPublication.publication_id,
                Dashboard.title,
                Dashboard.cron_schedule,
                Dashboard.cron_timeout,
                Dashboard.cron_enabled,
            )
            .join(Dashboard, Dashboard.slug == DashboardPublication.dashboard_slug)
            .where(
                DashboardPublication.snapshot_has_cron,
                DashboardPublication.unpublished_at.is_(None),
                DashboardPublication.refresh_paused_at.is_(None),
            )
            .order_by(DashboardPublication.dashboard_slug, DashboardPublication.publication_id)
        ).all()

    tasks = []
    for slug, pub_id, title, schedule, timeout, enabled in rows:
        prefix = f"{slug}/{pub_id}/"
        tasks.append({
            "slug": f"{slug}-{pub_id}",
            "title": title,
            "tier": "publication",
            "source": "s3-publication",
            "path": prefix,
            "cron_path": f"{prefix}cron.py",
            "enabled": enabled,
            "timeout": timeout,
            "schedule": schedule,
            "batch": PUBLICATION_BATCH,
            "publication_id": pub_id,
            "dashboard_slug": slug,
        })
    return tasks


def backfill_cron_metadata(session: Session, download: Callable[[str], bytes | None]) -> int:
    """One-time: copy schedule/timeout/enabled from each has_cron dashboard's S3 APP.md into its row."""
    updated = 0
    for dashboard in session.scalars(select(Dashboard).where(Dashboard.has_cron)):
        raw = download(f"{dashboard.slug}/APP.md")
        if raw is None:
            continue
        meta = parse_frontmatter_text(raw.decode())
        dashboard.cron_schedule = SCHEDULE_PRESETS.get(get_schedule(meta), SCHEDULE_PRESETS["daily"])
        dashboard.cron_timeout = get_timeout(meta)
        dashboard.cron_enabled = is_enabled(meta)
        updated += 1
    return updated


def run_cron_backfill() -> int:
    """One-time operator entry point: backfill cron metadata from S3 APP.md, committing on success."""
    with get_db() as session:
        return backfill_cron_metadata(session, s3.interactive.download)


def discover_system_tasks() -> list[dict]:
    """Tâches du dossier cron/, leur activation stockée l'emportant sur leur front-matter."""
    tasks = discover_from_dir(config.CRON_DIR, "CRON.md", "system")
    stored = stored_task_states()
    for task in tasks:
        task["enabled"] = stored.get(task["slug"], task["enabled"])
    return tasks


def discover_cron_tasks() -> list[dict]:
    """Discover all cron tasks: system → app → publication."""
    tasks = discover_system_tasks()
    tasks += discover_from_s3()
    tasks += discover_publications()
    return tasks


def find_task(slug: str) -> dict | None:
    # Why: discovery order (system → app → publication) means an app slug of shape
    # "{dashboard}-{6 chars}" would shadow a same-named publication composite. Risk is
    # near-zero (would require an app slug to collide with a real publication id);
    # documented here so future readers know first-match-wins is intentional.
    for task in discover_cron_tasks():
        if task["slug"] == slug:
            return task
    return None


def read_cron_script(task: dict) -> str | None:
    """Return the cron.py source for a task — from S3 for app tasks, else the local file."""
    if task.get("source") == "s3":
        content = s3.interactive.download(task["cron_path"])
        return content.decode(errors="replace") if content is not None else None
    path = Path(task["cron_path"])
    return path.read_text() if path.exists() else None


def facade_violations_by_slug(tasks: list[dict]) -> dict[str, list[str]]:
    """Modules applicatifs importés hors de la façade par les cron.py de tableaux de bord."""
    found = {}
    # Why: les crons système (config.CRON_DIR) sont du code applicatif, pas des tableaux de bord —
    # la façade ne les contraint pas.
    for task in (t for t in tasks if t.get("source") in ("s3", "s3-publication")):
        source = read_cron_script(task)
        if source is None:
            continue
        try:
            violations = dashboard_api.facade_violations(source)
        # Why: un cron.py illisible échouera à l'exécution ; la découverte, elle, doit continuer.
        except SyntaxError:
            logger.warning("cron %s: cron.py unparsable, facade not checked", sanitize_for_log(task["slug"]))
            continue
        if violations:
            found[task["slug"]] = violations
    return found


def log_facade_violations(slug: str, script: Path) -> None:
    """Le cron.py est déjà sur disque au moment de l'exécution : le lire ne coûte aucun appel S3."""
    try:
        violations = dashboard_api.facade_violations(script.read_text(errors="replace"))
    except (SyntaxError, OSError) as e:
        logger.debug("cron %s: facade not checked (%s)", sanitize_for_log(slug), e)
        return
    if violations:
        logger.warning("cron %s imports outside the facade: %s", sanitize_for_log(slug), ", ".join(violations))


_facade_metadata = MetaData(schema=FACADE_AUDIT_SCHEMA)
facade_audit_state = Table(
    "facade_audit_state",
    _facade_metadata,
    Column("id", Integer, primary_key=True),
    Column("slugs", JSON),
    Column("reported_at", DateTime(timezone=True)),
)


def last_reported_slugs() -> list[str] | None:
    """Ensemble signalé au dernier passage, ou None quand rien n'a encore été journalisé."""
    try:
        eng = get_engine()
        with eng.connect() as conn:
            if not eng.dialect.has_table(conn, "facade_audit_state", schema=FACADE_AUDIT_SCHEMA):
                return None
            row = conn.execute(select(facade_audit_state).where(facade_audit_state.c.id == 1)).mappings().first()
    except SQLAlchemyError as e:
        logger.warning("audit façade : lecture de l'état précédent impossible (%s)", e)
        return None
    return row["slugs"] if row else None


def record_reported_slugs(slugs: list[str]) -> None:
    """Un état non écrit ne fait que réémettre l'alerte demain : il ne doit pas faire échouer l'audit."""
    try:
        eng = get_engine()
        with eng.begin() as conn:
            conn.execute(text("CREATE SCHEMA IF NOT EXISTS " + FACADE_AUDIT_SCHEMA))
        _facade_metadata.create_all(eng)
        payload = {"id": 1, "slugs": slugs, "reported_at": utcnow()}
        statement = pg_insert(facade_audit_state).values(payload)
        statement = statement.on_conflict_do_update(
            index_elements=["id"], set_={"slugs": slugs, "reported_at": utcnow()}
        )
        with eng.begin() as conn:
            conn.execute(statement)
    except SQLAlchemyError as e:
        logger.warning("audit façade : état non enregistré, l'alerte repartira au prochain passage (%s)", e)


# Why: un canal où le même message revient tous les jours cesse d'être lu, et ce sont les échecs RPE
# et runner qui s'y noient. Seul un changement de la liste vaut une alerte.
def report_facade_violations(tasks: list[dict], notify: bool) -> dict[str, list[str]]:
    """En observation : journalise, et n'alerte que quand l'ensemble des non conformes change."""
    found = facade_violations_by_slug(tasks)
    for slug, modules in sorted(found.items()):
        logger.warning("cron %s imports outside the facade: %s", sanitize_for_log(slug), ", ".join(modules))
    if not notify:
        return found
    slugs = sorted(found)
    known = last_reported_slugs()
    if known is not None and sorted(known) == slugs:
        return found
    if slugs:
        listing = "\n".join(f"• `{slug}` — {', '.join(modules)}" for slug, modules in sorted(found.items()))
        alerts.notify_alert_channel(
            f":warning: *{len(found)} tableau(x) de bord importent hors de `{dashboard_api.FACADE}`*\n"
            f"Observation : la planification n'est pas encore refusée.\n{listing}"
        )
    elif known:
        alerts.notify_alert_channel(
            f":white_check_mark: *Plus aucun tableau de bord n'importe hors de `{dashboard_api.FACADE}`.*"
        )
    record_reported_slugs(slugs)
    return found


def prepare_s3_workdir(store: S3Store, store_relative_prefix: str, label: str) -> tuple[Path, dict[str, str]]:
    safe_label = re.sub(r"[^a-zA-Z0-9_-]", "", label) or "task"
    workdir = Path(tempfile.mkdtemp(prefix=f"cron-{safe_label}-"))
    pre_hashes: dict[str, str] = {}
    try:
        for entry in store.list_files(store_relative_prefix):
            local_name = entry["path"][len(store_relative_prefix) :]
            if not local_name or ".." in local_name:
                continue
            content = store.download(entry["path"])
            if content is not None:
                local_file = (workdir / local_name).resolve()
                try:
                    local_file.relative_to(workdir.resolve())
                except ValueError:
                    continue
                local_file.parent.mkdir(parents=True, exist_ok=True)
                local_file.write_bytes(content)
                pre_hashes[local_name] = hashlib.md5(content, usedforsecurity=False).hexdigest()
    # Why: the caller only learns the workdir on return — on failure, nobody else can remove it.
    except BaseException:
        remove_workdir(workdir)
        raise
    return workdir, pre_hashes


def upload_s3_results(
    store: S3Store, store_relative_prefix: str, label: str, workdir: Path, pre_hashes: dict[str, str]
):
    uploaded = skipped = 0
    workdir_resolved = workdir.resolve()
    for path in workdir.rglob("*"):
        if not path.is_file():
            continue
        try:
            path.resolve().relative_to(workdir_resolved)
        except ValueError:
            continue
        rel = str(path.relative_to(workdir))
        content = path.read_bytes()
        if pre_hashes.get(rel) == hashlib.md5(content, usedforsecurity=False).hexdigest():
            skipped += 1
            continue
        store.upload(f"{store_relative_prefix}{rel}", content)
        uploaded += 1
    if uploaded:
        logger.info(
            "Cron upload %s: %d uploaded, %d unchanged",
            sanitize_for_log(label),
            uploaded,
            skipped,
        )


def combine_output(stdout: str, stderr: str) -> str:
    """La fin des deux flux dans la limite de MAX_OUTPUT_SIZE, stderr gardant la moitié du budget."""
    if not stderr:
        return stdout[-MAX_OUTPUT_SIZE:]
    separator = "\n--- stderr ---\n"
    # Why: ce qui explique un échec est à la fin — la stacktrace pour stderr, les dernières
    # lignes exécutées pour stdout.
    tail = (separator + stderr[-(MAX_OUTPUT_SIZE // 2) :])[-MAX_OUTPUT_SIZE:]
    budget = MAX_OUTPUT_SIZE - len(tail)
    return (stdout[-budget:] if budget else "") + tail


def drain_task_stream(pipe, slug: str, stream: str) -> str:
    """Log every line as the task emits it; keep only the tail that fits the run's output budget."""
    kept = collections.deque()
    size = 0
    lines = 0
    for raw in pipe:
        line = raw.rstrip("\n")
        lines += 1
        # Why: une tâche qui déraille en imprimant des millions de lignes paierait son bruit en
        # ingestion Datadog ; le run en garde la fin, les logs en gardent le début.
        if lines <= MAX_LOGGED_LINES:
            logger.info(
                "%s",
                sanitize_for_log(line),
                extra={"cron.task.name": sanitize_for_log(slug), "cron.task.stream": stream},
            )
        kept.append(line)
        size += len(line) + 1
        while size > MAX_OUTPUT_SIZE // 2:
            size -= len(kept.popleft()) + 1
    if lines > MAX_LOGGED_LINES:
        logger.warning(
            "cron %s: %s tronqué, %d lignes non journalisées",
            sanitize_for_log(slug),
            stream,
            lines - MAX_LOGGED_LINES,
        )
    return "\n".join(kept)


def collect_task_stream(pipe, slug: str, stream: str, collected: dict[str, str]) -> None:
    """Draine un tuyau ; le dépôt du résultat vaut preuve que le drainage est allé jusqu'à l'EOF."""
    collected[stream] = drain_task_stream(pipe, slug, stream)


def drained(thread: threading.Thread, collected: dict[str, str], slug: str, stream: str) -> str:
    """Ce qu'un drainage a collecté, sans jamais attendre plus que le délai de grâce."""
    # Why: un descendant qui a hérité des tuyaux les garde ouverts après la mort de la tâche ; sans
    # borne, l'attente de l'EOF fige le lot entier bien au-delà du timeout.
    thread.join(timeout=5)
    if thread.is_alive():
        logger.warning("cron %s: %s toujours ouvert après la fin de la tâche", sanitize_for_log(slug), stream)
    return collected.get(stream, "")


def run_task_process(command: list[str], cwd: str, env: dict, timeout: int, slug: str) -> tuple[int | None, str, str]:
    """Run a task with its output streamed to the container logs; returncode is None on timeout."""
    # Why: pas de `with` sur le Popen — sa sortie de bloc ferme les tuyaux, et ce close() réclame le
    # verrou que le thread de drainage détient pendant sa lecture bloquée. Le conteneur y reste.
    process = subprocess.Popen(
        command,
        cwd=cwd,
        env=env,
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
        text=True,
        errors="replace",
        start_new_session=True,
    )
    # Why: le pgid se lit tant que la tâche n'est pas moissonnée — après le `wait()`, le pid peut
    # désigner un groupe sans rapport et le SIGKILL partirait à côté.
    pgid = os.getpgid(process.pid)
    collected: dict[str, str] = {}
    # Why: des threads daemon, jamais un pool — à la sortie de l'interpréteur, un drainage coincé sur
    # un tuyau qu'aucun EOF ne viendra fermer retiendrait indéfiniment un thread non daemon.
    out = threading.Thread(target=collect_task_stream, args=(process.stdout, slug, "stdout", collected), daemon=True)
    err = threading.Thread(target=collect_task_stream, args=(process.stderr, slug, "stderr", collected), daemon=True)
    out.start()
    err.start()

    try:
        returncode = process.wait(timeout=timeout)
    except subprocess.TimeoutExpired:
        returncode = None
    # Why: même une tâche qui réussit peut laisser un processus d'arrière-plan tenant les tuyaux ;
    # tuer le groupe dans tous les cas est la seule façon de rendre un EOF aux drainages.
    kill_process_group(pgid, process)
    if returncode is None:
        process.wait()

    stdout = drained(out, collected, slug, "stdout")
    stderr = drained(err, collected, slug, "stderr")
    if len(collected) == 2:
        # Why: un tuyau qu'un drainage lit encore ne se ferme pas — on abandonne ses descripteurs,
        # ils partiront avec le processus plutôt que de le figer.
        process.stdout.close()
        process.stderr.close()
    return returncode, stdout, stderr


def kill_process_group(pgid: int, process: subprocess.Popen) -> None:
    """Tue la tâche et sa descendance — `process.kill()` laisserait les petits-enfants tourner."""
    try:
        os.killpg(pgid, signal.SIGKILL)
    except ProcessLookupError, PermissionError:
        process.kill()


def sentry_monitor_config(task: dict) -> dict:
    """Build Sentry Crons monitor config from task metadata."""
    minute, _, days = SCHEDULE_PRESETS[cadence(task.get("schedule", "daily"))].split(" ", 2)
    crontab = f"{minute} {BATCH_HOURS.get(task.get('batch'), 6)} {days}"
    return {
        "schedule": {"type": "crontab", "value": crontab},
        "checkin_margin": 30,
        "max_runtime": task.get("timeout", DEFAULT_TIMEOUT) // 60 + 1,
        "failure_issue_threshold": 2,
        "recovery_threshold": 1,
    }


def batch_monitor_config(batch: str, tasks: list[dict], budget: int | None) -> dict:
    """Moniteur Sentry d'un lot : un conteneur tué laisse son check-in ouvert, que Sentry passe en échec."""
    timeouts = [task["timeout"] for task in tasks if task["batch"] == batch]
    runtime = min(sum(timeouts), budget + max(timeouts, default=0)) if budget else sum(timeouts)
    return {
        "schedule": {"type": "crontab", "value": f"0 {BATCH_HOURS.get(batch, 6)} * * *"},
        "checkin_margin": 30,
        "max_runtime": runtime // 60 + 1,
        "failure_issue_threshold": 1,
        "recovery_threshold": 1,
    }


def run_cron_task(slug: str, trigger: str = "scheduled") -> dict:
    """Resolve a task by slug and run it."""
    started_at = utcnow()
    try:
        task = find_task(slug)
    except (ClientError, BotoCoreError) as e:
        # Why: la découverte liste S3. Hors de tout try, une secousse tuait le conteneur sans
        # laisser la moindre ligne en base — un run lancé dont rien ne revient jamais.
        logger.exception("cron %s : découverte S3 impossible", sanitize_for_log(slug))
        return record_unexpected_failure(slug, started_at, e, trigger)
    if not task:
        return {
            "slug": slug,
            "status": "failure",
            "output": f"cron task not found: {slug}",
            "duration_ms": 0,
            "started_at": utcnow(),
            "finished_at": utcnow(),
        }
    try:
        return execute_task(task, trigger)
    except Exception as e:
        # Why: un run manuel qui lève doit laisser la même trace qu'un run planifié.
        logger.exception("cron %s crashed", sanitize_for_log(slug))
        return record_unexpected_failure(slug, started_at, e, trigger)


def run_task_and_publications(slug: str, trigger: str = "manual") -> list[dict]:
    """Rejoue une tâche puis, si c'est un tableau de bord, chacune de ses publications actives."""
    try:
        task = find_task(slug)
    except ClientError, BotoCoreError:
        # Why: run_cron_task retrouvera la même panne et l'enregistrera ; ici il s'agit seulement
        # de ne pas chercher des publications qu'on ne saura de toute façon pas rattacher.
        logger.exception("cron %s : découverte S3 impossible", sanitize_for_log(slug))
        task = None
    results = [run_cron_task(slug, trigger)]
    if task and task.get("source") == "s3":
        for pub in list_publications(slug, active_only=True):
            if pub.get("snapshot_has_cron") and not pub.get("refresh_paused_at"):
                results.append(run_cron_task(f"{slug}-{pub['publication_id']}", trigger))
    return results


def execute_task(task: dict, trigger: str = "scheduled") -> dict:
    """Run an already-discovered task; callers with the task dict skip re-discovery."""
    slug = task["slug"]
    monitor_slug = f"cron-{slug}"
    monitor_config = sentry_monitor_config(task)
    check_in_id = sentry_sdk.crons.api.capture_checkin(
        monitor_slug=monitor_slug,
        status=sentry_sdk.crons.consts.MonitorStatus.IN_PROGRESS,
        monitor_config=monitor_config,
    )

    source = task.get("source")
    uses_workdir = source in ("s3", "s3-publication")
    timeout = task["timeout"]
    workdir = None
    pre_hashes: dict[str, str] = {}

    started_at = utcnow()
    start_time = time.monotonic()
    status = "failure"

    # Why: transmission de l'environnement complet au sous-processus, pas une lecture de
    # configuration — seul SCALINGO_API_TOKEN est retiré. Il ouvre `POST /v1/apps/<app>/run`, donc
    # l'exécution de commandes arbitraires en production, et les cron.py de tableaux de bord sont
    # écrits par l'agent et stockés hors dépôt : aucun diff ne les relit.
    env = {k: v for k, v in os.environ.items() if k != "SCALINGO_API_TOKEN"}  # noqa: TID251
    env["PYTHONPATH"] = str(config.BASE_DIR)

    if source == "s3":
        store = s3.interactive
        store_prefix = f"{slug}/"
    elif source == "s3-publication":
        store = s3.publications
        store_prefix = f"{task['dashboard_slug']}/{task['publication_id']}/"

    try:
        if uses_workdir:
            workdir, pre_hashes = prepare_s3_workdir(store, store_prefix, slug)
            cron_script = str(workdir / "cron.py")
            log_facade_violations(slug, workdir / "cron.py")
            cwd = str(workdir)
        else:
            cron_script = task["cron_path"]
            cwd = task["path"]

        returncode, stdout, stderr = run_task_process([sys.executable, cron_script], cwd, env, timeout, slug)
        elapsed_ms = int((time.monotonic() - start_time) * 1000)
        finished_at = utcnow()

        if returncode is None:
            stderr = f"{stderr}\nScript timed out after {timeout}s".lstrip()
        output = combine_output(stdout, stderr)
        error = stderr or stdout
        if uses_workdir and returncode == 0 and workdir:
            upload_s3_results(store, store_prefix, slug, workdir, pre_hashes)
        status = {0: "success", None: "timeout"}.get(returncode, "failure")

    except (OSError, ClientError, BotoCoreError) as e:
        elapsed_ms = int((time.monotonic() - start_time) * 1000)
        finished_at = utcnow()
        status = "failure"
        output = error = combine_output("", f"Error running script: {e}")

    finally:
        if workdir and workdir.exists():
            remove_workdir(workdir)
        sentry_sdk.crons.api.capture_checkin(
            monitor_slug=monitor_slug,
            status=sentry_sdk.crons.consts.MonitorStatus.OK
            if status == "success"
            else sentry_sdk.crons.consts.MonitorStatus.ERROR,
            check_in_id=check_in_id,
            duration=time.monotonic() - start_time,
            monitor_config=monitor_config,
        )

    run_result = {
        "slug": slug,
        "status": status,
        "output": output,
        "duration_ms": elapsed_ms,
        "started_at": started_at,
        "finished_at": finished_at,
    }

    previous_status = None
    if trigger == "scheduled":
        recent = get_app_runs(slug, limit=1)
        previous_status = recent[0]["status"] if recent else None

    record_run(run_result, trigger)

    if trigger == "scheduled":
        notify_cron_status_change(slug, status, previous_status, error, repeat=source == "s3-publication")

    if source == "s3-publication" and status == "success":
        try:
            publications.refresh(task["publication_id"])
        except SQLAlchemyError:
            logger.exception("cron %s: publication refresh failed", sanitize_for_log(slug))
    return run_result


def notify_cron_status_change(
    slug: str, status: str, previous_status: str | None, error: str, *, repeat: bool = False
) -> None:
    """Post a Slack alert when a cron breaks (every run if `repeat`, else only newly) or recovers."""
    broke = status in BROKEN_STATUSES and (repeat or previous_status not in BROKEN_STATUSES)
    recovered = status == "success" and previous_status in BROKEN_STATUSES
    if not (broke or recovered):
        return

    if broke:
        message = f":red_circle: *Cron en échec : {slug}* ({status})"
        snippet = (error or "").strip()[-500:].replace("```", "ʼʼʼ")
        if snippet:
            message += f"\n```{snippet}```"
    else:
        message = f":large_green_circle: *Cron rétabli : {slug}*"
    if config.BASE_URL:
        message += f"\n<{config.BASE_URL}/cron|Voir les crons>"

    alerts.notify_alert_channel(message)


def record_unexpected_failure(slug: str, started_at: dt.datetime, exc: Exception, trigger: str) -> dict:
    """Enregistre une tâche qui a levé : sans ça, son échec ne laisse aucune trace."""
    finished_at = utcnow()
    result = {
        "slug": slug,
        "status": "failure",
        "output": combine_output("", f"Unexpected error: {exc!r}"),
        "duration_ms": int((finished_at - started_at).total_seconds() * 1000),
        "started_at": started_at,
        "finished_at": finished_at,
    }
    record_run(result, trigger)
    return result


def remove_workdir(workdir: Path) -> None:
    """Un répertoire qui survit à sa suppression recrée la fuite que le nettoyage devait fermer."""
    shutil.rmtree(workdir, ignore_errors=True)
    if workdir.exists():
        logger.warning("cron : répertoire de travail non supprimé (%s)", workdir)


def record_run(result: dict, trigger: str):
    try:
        with get_db() as session:
            session.add(
                CronRun(
                    app_slug=result["slug"],
                    started_at=result["started_at"],
                    finished_at=result["finished_at"],
                    status=result["status"],
                    output=result["output"],
                    duration_ms=result["duration_ms"],
                    trigger=trigger,
                )
            )
    # Why: recording is best-effort; a DB error must not crash the cron runner.
    except Exception:
        logger.exception("failed to record cron run")


def _run_to_dict(run: CronRun) -> dict:
    return {
        "id": run.id,
        "app_slug": run.app_slug,
        "started_at": run.started_at,
        "finished_at": run.finished_at,
        "status": run.status,
        "output": run.output,
        "duration_ms": run.duration_ms,
        "trigger": run.trigger,
    }


def get_last_runs(slug: str | None = None) -> dict[str, dict]:
    """Latest run per app slug, without the output text."""
    stmt = (
        select(
            CronRun.id,
            CronRun.app_slug,
            CronRun.started_at,
            CronRun.finished_at,
            CronRun.status,
            CronRun.duration_ms,
            CronRun.trigger,
        )
        .distinct(CronRun.app_slug)
        .order_by(CronRun.app_slug, CronRun.started_at.desc(), CronRun.id.desc())
    )
    if slug:
        stmt = stmt.where(CronRun.app_slug == slug)
    try:
        with get_db() as session:
            return {row.app_slug: row._asdict() for row in session.execute(stmt)}
    # Why: reading history is best-effort; a DB error must not crash the caller.
    except Exception:
        logger.exception("failed to read cron runs")
        return {}


def get_app_runs(slug: str, limit: int = 20) -> list[dict]:
    try:
        with get_db() as session:
            rows = session.scalars(
                select(CronRun).where(CronRun.app_slug == slug).order_by(CronRun.started_at.desc()).limit(limit)
            ).all()
            return [_run_to_dict(row) for row in rows]
    # Why: reading history is best-effort; a DB error must not crash the caller.
    except Exception:
        logger.exception("failed to read app runs")
        return []


def facade_audit() -> list[str]:
    """Mesure la migration vers la façade : combien de TDB tournent, combien restent à migrer."""
    with get_db() as session:
        active = session.scalar(select(func.count()).select_from(Dashboard).where(~Dashboard.is_archived))
    found = facade_violations_by_slug(discover_cron_tasks())
    lines = [f"{active} tableaux de bord actifs, {len(found)} importent hors de {dashboard_api.FACADE}."]
    lines += [f"  {slug:30s} {', '.join(modules)}" for slug, modules in sorted(found.items())]
    return lines


def run_all(dry_run: bool = False, *, batch: str, budget: int | None = None) -> list[dict]:
    """Run the enabled tasks of one batch that are due today, within an optional time budget."""
    try:
        tasks = discover_cron_tasks()
    except (ClientError, BotoCoreError, SQLAlchemyError) as e:
        # Why: la découverte des tableaux de bord lit S3 *et* la base ; une panne de l'une ou de
        # l'autre ne prive que les tableaux de bord. Les tâches système, elles, peuvent tourner —
        # mais l'amputation du lot doit s'annoncer au lieu de passer pour un succès.
        logger.exception("cron : découverte des tableaux de bord impossible, seules les tâches système tournent")
        alerts.notify_alert_channel(
            f":red_circle: *Découverte des crons amputée* — {e.__class__.__name__}. "
            "Seules les tâches système tournent aujourd'hui ; aucun tableau de bord n'est rafraîchi."
        )
        tasks = discover_system_tasks()
    results = []
    started = time.monotonic()
    dropped = []
    if not dry_run:
        monitor_config = batch_monitor_config(batch, tasks, budget)
        check_in_id = sentry_sdk.crons.api.capture_checkin(
            monitor_slug=f"lot-{batch}",
            status=sentry_sdk.crons.consts.MonitorStatus.IN_PROGRESS,
            monitor_config=monitor_config,
        )

    for task in tasks:
        if task["batch"] != batch:
            if dry_run:
                logger.info("SKIP %s (batch %s)", task["slug"], task["batch"])
            continue

        if not task["enabled"]:
            if dry_run:
                logger.info("SKIP %s (disabled)", task["slug"])
            continue

        if not is_due(task["schedule"]):
            if dry_run:
                logger.info("SKIP %s (schedule: %s, not due)", task["slug"], task["schedule"])
            continue

        if dry_run:
            logger.info(
                "WOULD RUN %s [%s] (timeout: %ss)",
                task["slug"],
                task["schedule"],
                task["timeout"],
            )
            continue

        if budget and time.monotonic() - started >= budget:
            dropped.append(task["slug"])
            now = utcnow()
            record_run(
                {
                    "slug": task["slug"],
                    "status": "skipped",
                    "output": f"Lot {batch} au-delà de son budget de {budget}s",
                    "duration_ms": 0,
                    "started_at": now,
                    "finished_at": now,
                },
                "scheduled",
            )
            continue

        started_at = utcnow()
        try:
            result = execute_task(task, trigger="scheduled")
        except Exception as e:
            # Why: une tâche qui lève ne doit pas priver les suivantes du lot de leur exécution.
            logger.exception("cron %s crashed", sanitize_for_log(task["slug"]))
            result = record_unexpected_failure(task["slug"], started_at, e, "scheduled")
        logger.info(
            "cron.task",
            extra={
                "cron.task.name": task["slug"],
                "cron.task.status": result["status"],
                "cron.task.duration": result["duration_ms"],
            },
        )
        results.append(result)

    if dropped:
        logger.warning("cron : lot %s amputé de %d tâche(s)", sanitize_for_log(batch), len(dropped))
        alerts.notify_alert_channel(
            f":hourglass: *Lot `{batch}` au-delà de son budget de {budget}s* — "
            f"{len(dropped)} tâche(s) non exécutée(s) : " + ", ".join(f"`{slug}`" for slug in dropped)
        )

    if not dry_run:
        sentry_sdk.crons.api.capture_checkin(
            monitor_slug=f"lot-{batch}",
            status=sentry_sdk.crons.consts.MonitorStatus.ERROR if dropped else sentry_sdk.crons.consts.MonitorStatus.OK,
            check_in_id=check_in_id,
            duration=time.monotonic() - started,
            monitor_config=monitor_config,
        )
    return results


def main():
    setup_logging(level=logging.DEBUG if config.DEBUG else logging.INFO)
    init_sentry()
    parser = argparse.ArgumentParser(description="Run cron tasks")
    parser.add_argument("--app", help="Run a specific task by slug (ignores schedule)")
    parser.add_argument("--batch", help="Batch to run")
    parser.add_argument("--list", action="store_true", help="List all discovered cron tasks")
    parser.add_argument("--dry-run", action="store_true", help="Show what would run without executing")
    parser.add_argument("--facade-audit", action="store_true", help="Count dashboards importing outside the facade")
    parser.add_argument("--budget", type=int, help="Durée maximale du lot, en secondes")
    args = parser.parse_args()

    if not (args.facade_audit or args.list or args.app or args.batch):
        parser.error("--batch is required unless --list, --app or --facade-audit is given")

    if args.facade_audit:
        for line in facade_audit():
            print(line)
        return

    if args.list:
        tasks = discover_cron_tasks()
        if not tasks:
            print("No cron tasks found.")
            return
        for task in tasks:
            status = "enabled" if task["enabled"] else "DISABLED"
            sched = task["schedule"]
            tier = task["tier"]
            print(f"  {task['slug']:30s} [{status}] {sched:8s} {tier:6s} {task['batch']:8s} {task['cron_path']}")
        return

    if args.app:
        print(f"Running cron for {args.app}...")
        for result in run_task_and_publications(args.app, trigger="manual"):
            print(f"  {result['slug']}: {result['status']} ({result['duration_ms']}ms)")
            if result["output"]:
                print(result["output"])
        return

    print("Running all cron tasks...")
    results = run_all(dry_run=args.dry_run, batch=args.batch, budget=args.budget)
    if not args.dry_run:
        ok = sum(1 for r in results if r["status"] == "success")
        fail = len(results) - ok
        print(f"Done: {ok} succeeded, {fail} failed")


if __name__ == "__main__":
    main()
