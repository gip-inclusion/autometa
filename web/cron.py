"""Cron utilities — discovery, recording, alerting. Scheduling is handled by flows/serve.py."""

import hashlib
import logging
import tempfile
from pathlib import Path

from sqlalchemy import select

from . import alerts, config, s3
from .database import get_db
from .models import CronRun, Dashboard

logger = logging.getLogger(__name__)

DEFAULT_TIMEOUT = 300
MAX_OUTPUT_SIZE = 50_000
BROKEN_STATUSES = {"failure", "timeout"}


def _sanitize_for_log(value: str) -> str:
    return value.replace("\r", "").replace("\n", "")


def parse_frontmatter_text(content: str) -> dict:
    """Parse YAML front-matter from a string."""
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
    """Parse YAML front-matter from a markdown file."""
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


def set_cron_enabled(app_slug: str, enabled: bool) -> bool:
    """Toggle the `cron:` field in a task's metadata file."""
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
    """Discover cron tasks for apps flagged `has_cron` in DB; metadata from S3 APP.md."""
    if not config.S3_BUCKET:
        return []

    with get_db() as session:
        rows = session.execute(
            select(Dashboard.slug, Dashboard.title)
            .where(Dashboard.has_cron, ~Dashboard.is_archived)
            .order_by(Dashboard.slug)
        ).all()

    tasks = []
    for slug, title in rows:
        if not s3.interactive.exists(f"{slug}/cron.py"):
            logger.warning("Dashboard %s has has_cron=true but no cron.py on S3", slug)
            continue

        md_bytes = s3.interactive.download(f"{slug}/APP.md")
        meta = parse_frontmatter_text(md_bytes.decode()) if md_bytes else {}

        tasks.append({
            "slug": slug,
            "title": title,
            "tier": "app",
            "source": "s3",
            "path": slug,
            "cron_path": f"{slug}/cron.py",
            "enabled": is_enabled(meta),
            "timeout": get_timeout(meta),
            "schedule": get_schedule(meta),
        })

    return tasks


def discover_cron_tasks() -> list[dict]:
    """Discover all cron tasks — system tasks (cron/) first, then app tasks (S3)."""
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
        local_name = entry["path"][len(f"{slug}/"):]
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


def upload_s3_results(slug: str, workdir: Path, pre_hashes: dict[str, str]) -> None:
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
        logger.info(
            "Cron upload %s: %d uploaded, %d unchanged",
            _sanitize_for_log(slug),
            uploaded,
            skipped,
        )


def record_run(result: dict, trigger: str) -> None:
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
    except Exception:
        # Why: recording is best-effort; a DB error must not crash the cron runner
        logger.warning("Failed to record cron run for %s", result.get("slug"))


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
    except Exception:
        # Why: reading history is best-effort; a DB error must not crash the caller
        logger.warning("Failed to read cron runs")
    return runs


def get_app_runs(slug: str, limit: int = 20) -> list[dict]:
    try:
        with get_db() as session:
            rows = session.scalars(
                select(CronRun).where(CronRun.app_slug == slug).order_by(CronRun.started_at.desc()).limit(limit)
            ).all()
            return [_run_to_dict(row) for row in rows]
    except Exception:
        # Why: reading history is best-effort; a DB error must not crash the caller
        logger.warning("Failed to read app runs for %s", slug)
        return []


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
