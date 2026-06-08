"""Cron runner for data refresh scripts."""

import argparse
import datetime as dt
import hashlib
import logging
import os
import re
import shutil
import subprocess
import sys
import tempfile
import time
from pathlib import Path

import sentry_sdk
from sqlalchemy import select

from web.helpers import now_local, sanitize_for_log, utcnow
from web.s3 import S3Store

from . import alerts, config, publications, s3
from .database import get_db
from .log import setup_logging
from .models import CronRun, Dashboard, DashboardPublication

logger = logging.getLogger(__name__)

# Defaults
DEFAULT_TIMEOUT = 300  # 5 minutes
MAX_OUTPUT_SIZE = 50_000

SCHEDULE_PRESETS = {
    "daily": "0 6 * * *",
    "weekly": "0 6 * * 1",
    "monthly": "0 6 1 * *",
}
_CRONTAB_TO_CADENCE = {crontab: token for token, crontab in SCHEDULE_PRESETS.items()}


def cadence(schedule: str) -> str:
    """Reduce a stored schedule (crontab or legacy token) to a runner cadence: daily|weekly|monthly."""
    # Why: the 06:00 dispatcher only honors day-level scheduling; an unrecognized crontab runs every
    # tick (daily). The full crontab string is preserved in the DB for a future scheduler.
    if schedule in SCHEDULE_PRESETS:
        return schedule
    return _CRONTAB_TO_CADENCE.get(schedule, "daily")


def is_valid_schedule(schedule: str) -> bool:
    """A storable schedule: a known cadence token, or any 5-field crontab string."""
    return schedule in SCHEDULE_PRESETS or len(schedule.split()) == 5


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


def is_due(schedule: str) -> bool:
    reduced = cadence(schedule)
    if reduced == "weekly":
        return now_local().weekday() == 0  # Monday
    if reduced == "monthly":
        return now_local().day == 1
    return True


def next_cron_run(schedule: str, now=None):
    """Next 06:00 dispatch time (local tz) for a schedule, by its day-level cadence."""
    now = now or now_local()
    target = now.replace(hour=6, minute=0, second=0, microsecond=0)
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
    """Enable/disable a cron task. Dashboards → DB `cron_enabled`; system tasks → CRON.md."""
    with get_db() as session:
        dashboard = session.scalar(select(Dashboard).where(Dashboard.slug == app_slug))
        if dashboard is not None:
            dashboard.cron_enabled = enabled
            return True

    md_path = config.CRON_DIR / app_slug / "CRON.md"
    if not md_path.exists():
        return False

    content = md_path.read_text()
    value_str = "true" if enabled else "false"
    if not content.startswith("---"):
        md_path.write_text(f"---\ncron: {value_str}\n---\n{content}")
        return True
    parts = content.split("---", 2)
    if len(parts) < 3:
        return False
    lines = parts[1].strip().split("\n")
    for i, line in enumerate(lines):
        if ":" in line and line.split(":", 1)[0].strip().lower() == "cron":
            lines[i] = f"cron: {value_str}"
            break
    else:
        lines.append(f"cron: {value_str}")
    md_path.write_text("---\n" + "\n".join(lines) + "\n---" + parts[2])
    return True


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

        tasks.append({
            "slug": folder.name,
            "title": meta.get("title", folder.name),
            "tier": tier,
            "path": str(folder),
            "cron_path": str(cron_script),
            "enabled": is_enabled(meta),
            "timeout": get_timeout(meta),
            "schedule": get_schedule(meta),
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

    tasks = []
    for slug, title, enabled, timeout, schedule in rows:
        if not s3.interactive.exists(f"{slug}/cron.py"):
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
    for slug, pub_id, title, schedule, timeout in rows:
        prefix = f"{slug}/{pub_id}/"
        tasks.append({
            "slug": f"{slug}-{pub_id}",
            "title": title,
            "tier": "publication",
            "source": "s3-publication",
            "path": prefix,
            "cron_path": f"{prefix}cron.py",
            "enabled": True,
            "timeout": timeout,
            "schedule": schedule,
            "publication_id": pub_id,
            "dashboard_slug": slug,
        })
    return tasks


def backfill_cron_metadata(session, download) -> int:
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


def discover_cron_tasks() -> list[dict]:
    """Discover all cron tasks: system → app → publication."""
    tasks = discover_from_dir(config.CRON_DIR, "CRON.md", "system")
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


def prepare_s3_workdir(store: S3Store, store_relative_prefix: str, label: str) -> tuple[Path, dict[str, str]]:
    safe_label = re.sub(r"[^a-zA-Z0-9_-]", "", label) or "task"
    workdir = Path(tempfile.mkdtemp(prefix=f"cron-{safe_label}-"))
    pre_hashes: dict[str, str] = {}
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


def _sentry_monitor_config(task: dict) -> dict:
    """Build Sentry Crons monitor config from task metadata."""
    crontab = SCHEDULE_PRESETS[cadence(task.get("schedule", "daily"))]
    return {
        "schedule": {"type": "crontab", "value": crontab},
        "checkin_margin": 30,
        "max_runtime": task.get("timeout", DEFAULT_TIMEOUT) // 60 + 1,
        "failure_issue_threshold": 2,
        "recovery_threshold": 1,
    }


def run_cron_task(slug: str, trigger: str = "scheduled") -> dict:
    """Run a single cron task by slug.

    Returns dict with: slug, status, output, duration_ms, started_at, finished_at.
    """
    task = find_task(slug)
    if not task:
        return {
            "slug": slug,
            "status": "failure",
            "output": f"cron task not found: {slug}",
            "duration_ms": 0,
            "started_at": utcnow(),
            "finished_at": utcnow(),
        }

    monitor_slug = f"cron-{slug}"
    monitor_config = _sentry_monitor_config(task)
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

    env = {
        **os.environ,
        "PYTHONPATH": str(config.BASE_DIR),
    }

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
            cwd = str(workdir)
        else:
            cron_script = task["cron_path"]
            cwd = task["path"]

        result = subprocess.run(
            [sys.executable, cron_script],
            cwd=cwd,
            capture_output=True,
            text=True,
            timeout=timeout,
            env=env,
        )
        elapsed_ms = int((time.monotonic() - start_time) * 1000)
        finished_at = utcnow()

        output = result.stdout
        if result.stderr:
            output += "\n--- stderr ---\n" + result.stderr
        output = output[:MAX_OUTPUT_SIZE]

        status = "success" if result.returncode == 0 else "failure"

        if uses_workdir and status == "success" and workdir:
            upload_s3_results(store, store_prefix, slug, workdir, pre_hashes)
            if source == "s3-publication":
                publications.refresh(task["publication_id"])

    except subprocess.TimeoutExpired:
        elapsed_ms = int((time.monotonic() - start_time) * 1000)
        finished_at = utcnow()
        status = "timeout"
        output = f"Script timed out after {timeout}s"

    except OSError as e:
        elapsed_ms = int((time.monotonic() - start_time) * 1000)
        finished_at = utcnow()
        status = "failure"
        output = f"Error running script: {e}"

    finally:
        if workdir and workdir.exists():
            shutil.rmtree(workdir, ignore_errors=True)

    run_result = {
        "slug": slug,
        "status": status,
        "output": output,
        "duration_ms": elapsed_ms,
        "started_at": started_at,
        "finished_at": finished_at,
    }

    sentry_status = (
        sentry_sdk.crons.consts.MonitorStatus.OK if status == "success" else sentry_sdk.crons.consts.MonitorStatus.ERROR
    )
    sentry_sdk.crons.api.capture_checkin(
        monitor_slug=monitor_slug,
        status=sentry_status,
        check_in_id=check_in_id,
        duration=elapsed_ms / 1000,
        monitor_config=monitor_config,
    )

    previous_status = None
    if trigger == "scheduled":
        recent = get_app_runs(slug, limit=1)
        previous_status = recent[0]["status"] if recent else None

    record_run(run_result, trigger)

    if trigger == "scheduled":
        notify_cron_status_change(slug, status, previous_status, output)
    return run_result


def notify_cron_status_change(slug: str, status: str, previous_status: str | None, output: str) -> None:
    """Post a Slack alert when a cron newly breaks or recovers."""
    broke = status in BROKEN_STATUSES and previous_status not in BROKEN_STATUSES
    recovered = status == "success" and previous_status in BROKEN_STATUSES
    if not (broke or recovered):
        return

    if broke:
        message = f":red_circle: *Cron en échec : {slug}* ({status})"
        snippet = (output or "").strip()[:500].replace("```", "ʼʼʼ")
        if snippet:
            message += f"\n```{snippet}```"
    else:
        message = f":large_green_circle: *Cron rétabli : {slug}*"
    if config.BASE_URL:
        message += f"\n<{config.BASE_URL}/cron|Voir les crons>"

    alerts.notify_alert_channel(message)


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


def get_last_runs(limit_per_app: int = 1) -> dict[str, list[dict]]:
    runs: dict[str, list[dict]] = {}
    try:
        with get_db() as session:
            rows = session.scalars(select(CronRun).order_by(CronRun.started_at.desc())).all()
            for row in rows:
                slug = row.app_slug
                if slug not in runs:
                    runs[slug] = []
                if len(runs[slug]) < limit_per_app:
                    runs[slug].append(_run_to_dict(row))
    # Why: reading history is best-effort; a DB error must not crash the caller.
    except Exception:
        logger.exception("failed to read cron runs")
    return runs


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


def run_all(dry_run: bool = False) -> list[dict]:
    """Discover and run all enabled cron tasks that are due today."""
    tasks = discover_cron_tasks()
    results = []

    for task in tasks:
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

        result = run_cron_task(task["slug"], trigger="scheduled")
        logger.info(
            "cron.task",
            extra={
                "cron.task.name": task["slug"],
                "cron.task.status": result["status"],
                "cron.task.duration": result["duration_ms"],
            },
        )
        results.append(result)

    return results


def main():
    setup_logging(level=logging.DEBUG if config.DEBUG else logging.INFO)
    parser = argparse.ArgumentParser(description="Run cron tasks")
    parser.add_argument("--app", help="Run a specific task by slug (ignores schedule)")
    parser.add_argument("--list", action="store_true", help="List all discovered cron tasks")
    parser.add_argument("--dry-run", action="store_true", help="Show what would run without executing")
    args = parser.parse_args()

    if args.list:
        tasks = discover_cron_tasks()
        if not tasks:
            print("No cron tasks found.")
            return
        for task in tasks:
            status = "enabled" if task["enabled"] else "DISABLED"
            sched = task["schedule"]
            tier = task["tier"]
            print(f"  {task['slug']:30s} [{status}] {sched:8s} {tier:6s}  {task['cron_path']}")
        return

    if args.app:
        print(f"Running cron for {args.app}...")
        result = run_cron_task(args.app, trigger="manual")
        print(f"  Status: {result['status']} ({result['duration_ms']}ms)")
        if result["output"]:
            print(result["output"])
        return

    print("Running all cron tasks...")
    results = run_all(dry_run=args.dry_run)
    if not args.dry_run:
        ok = sum(1 for r in results if r["status"] == "success")
        fail = len(results) - ok
        print(f"Done: {ok} succeeded, {fail} failed")


if __name__ == "__main__":
    main()
