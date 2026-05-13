"""Cron runner for data refresh scripts."""

import argparse
import hashlib
import logging
import os
import shutil
import subprocess
import sys
import tempfile
import time
from pathlib import Path

import sentry_sdk
from sqlalchemy import select

from web.helpers import now_local, utcnow

from . import config, s3
from .database import get_db
from .models import CronRun

logger = logging.getLogger(__name__)

# Defaults
DEFAULT_TIMEOUT = 300  # 5 minutes
MAX_OUTPUT_SIZE = 50_000


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
    except (KeyError, ValueError):
        return DEFAULT_TIMEOUT


def get_schedule(meta: dict) -> str:
    return meta.get("schedule", "daily").lower()


def is_due(schedule: str) -> bool:
    if schedule == "daily":
        return True
    if schedule == "weekly":
        return now_local().weekday() == 0  # Monday
    return True


def set_cron_enabled(app_slug: str, enabled: bool) -> bool:
    """Toggle the `cron:` field in a task's metadata file.

    Checks both system (CRON.md) and app (APP.md) locations.
    Returns True if the file was updated, False if not found.
    """
    # Try system task first, then app task
    for md_path in [
        config.CRON_DIR / app_slug / "CRON.md",
        config.INTERACTIVE_DIR / app_slug / "APP.md",
    ]:
        if not md_path.exists():
            continue

        content = md_path.read_text()
        value_str = "true" if enabled else "false"

        if not content.startswith("---"):
            content = f"---\ncron: {value_str}\n---\n{content}"
            md_path.write_text(content)
            return True

        parts = content.split("---", 2)
        if len(parts) < 3:
            continue

        lines = parts[1].strip().split("\n")
        found = False
        for i, line in enumerate(lines):
            if ":" in line:
                key, _ = line.split(":", 1)
                if key.strip().lower() == "cron":
                    lines[i] = f"cron: {value_str}"
                    found = True
                    break

        if not found:
            lines.append(f"cron: {value_str}")

        content = "---\n" + "\n".join(lines) + "\n---" + parts[2]
        md_path.write_text(content)
        return True

    return False


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
    """Discover cron tasks from S3-stored interactive apps."""
    if not config.S3_BUCKET:
        return []
    tasks = []
    for slug in s3.interactive.list_directories():
        if not s3.interactive.exists(f"{slug}/cron.py"):
            continue

        # Parse APP.md metadata from S3
        md_bytes = s3.interactive.download(f"{slug}/APP.md")
        meta = parse_frontmatter_text(md_bytes.decode()) if md_bytes else {}

        tasks.append({
            "slug": slug,
            "title": meta.get("title", slug),
            "tier": "app",
            "source": "s3",
            "path": slug,  # S3 prefix, not a local path
            "cron_path": f"{slug}/cron.py",
            "enabled": is_enabled(meta),
            "timeout": get_timeout(meta),
            "schedule": get_schedule(meta),
        })

    return tasks


def discover_cron_tasks() -> list[dict]:
    """Discover all cron tasks from all tiers.

    System tasks (cron/) come first, then app tasks (data/interactive/ or S3).
    """
    tasks = discover_from_dir(config.CRON_DIR, "CRON.md", "system")
    tasks += discover_from_s3()
    return tasks


def find_task(slug: str) -> dict | None:
    for task in discover_cron_tasks():
        if task["slug"] == slug:
            return task
    return None


def prepare_s3_workdir(slug: str) -> tuple[Path, dict[str, str]]:
    workdir = Path(tempfile.mkdtemp(prefix=f"cron-{slug}-"))
    pre_hashes: dict[str, str] = {}
    for entry in s3.interactive.list_files(f"{slug}/"):
        local_name = entry["path"][len(f"{slug}/") :]
        if not local_name or ".." in local_name:
            continue
        content = s3.interactive.download(entry["path"])
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


def upload_s3_results(slug: str, workdir: Path, pre_hashes: dict[str, str]):
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
        s3.interactive.upload(f"{slug}/{rel}", content)
        uploaded += 1
    if uploaded:
        logger.info(f"Cron upload {slug}: {uploaded} uploaded, {skipped} unchanged")


def _sentry_monitor_config(task: dict) -> dict:
    """Build Sentry Crons monitor config from task metadata."""
    schedule = task.get("schedule", "daily")
    if schedule == "weekly":
        crontab = "0 6 * * 1"
    else:
        crontab = "0 6 * * *"
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

    is_s3 = task.get("source") == "s3"
    timeout = task["timeout"]
    workdir = None
    pre_hashes: dict[str, str] = {}

    started_at = utcnow()
    start_time = time.monotonic()

    env = {
        **os.environ,
        "PYTHONPATH": str(config.BASE_DIR),
    }

    try:
        if is_s3:
            workdir, pre_hashes = prepare_s3_workdir(slug)
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

        if is_s3 and status == "success" and workdir:
            upload_s3_results(slug, workdir, pre_hashes)

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

    record_run(run_result, trigger)
    return run_result


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
    except Exception as e:
        print(f"Warning: failed to record cron run: {e}", file=sys.stderr)


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
    except Exception as e:
        print(f"Warning: failed to read cron runs: {e}", file=sys.stderr)
    return runs


def get_app_runs(slug: str, limit: int = 20) -> list[dict]:
    try:
        with get_db() as session:
            rows = session.scalars(
                select(CronRun).where(CronRun.app_slug == slug).order_by(CronRun.started_at.desc()).limit(limit)
            ).all()
            return [_run_to_dict(row) for row in rows]
    # Why: reading history is best-effort; a DB error must not crash the caller.
    except Exception as e:
        print(f"Warning: failed to read app runs: {e}", file=sys.stderr)
        return []


def run_all(dry_run: bool = False) -> list[dict]:
    """Discover and run all enabled cron tasks that are due today."""
    tasks = discover_cron_tasks()
    results = []

    for task in tasks:
        if not task["enabled"]:
            if dry_run:
                print(f"  SKIP {task['slug']} (disabled)")
            continue

        if not is_due(task["schedule"]):
            if dry_run:
                print(f"  SKIP {task['slug']} (schedule: {task['schedule']}, not due)")
            continue

        if dry_run:
            sched = f" [{task['schedule']}]" if task["schedule"] != "daily" else ""
            print(f"  WOULD RUN {task['slug']}{sched} (timeout: {task['timeout']}s)")
            continue

        print(f"  Running {task['slug']}...", end=" ", flush=True)
        result = run_cron_task(task["slug"], trigger="scheduled")
        print(f"{result['status']} ({result['duration_ms']}ms)")
        results.append(result)

    return results


def main():
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
