"""Route GET /selftest : checks services ; HTML consomme le flux text/plain par SNAPSHOT_SEP."""

import asyncio
import json
import logging
import subprocess
import time
from dataclasses import dataclass
from typing import Callable

import requests
from fastapi import APIRouter, Request
from fastapi.responses import HTMLResponse, StreamingResponse

from lib.sources import list_instances

from . import config

logger = logging.getLogger(__name__)

SELFTEST_TIMEOUT_SEC = 3


router = APIRouter()

SNAPSHOT_SEP = "\n---\n"


def _first_accept(accept: str) -> str:
    if not accept or not accept.strip():
        return "*/*"
    return accept.split(",")[0].strip().split(";")[0].strip().lower()


def _selftest_page_html() -> str:
    sep = json.dumps(SNAPSHOT_SEP)
    return f"""<!DOCTYPE html>
<html lang="fr">
<head>
<meta charset="utf-8">
<meta name="viewport" content="width=device-width, initial-scale=1">
<title>Autometa selftest</title>
<style>
body {{ font-family: system-ui, sans-serif; margin: 1rem; }}
pre {{ white-space: pre-wrap; word-break: break-word; margin: 0; }}
</style>
</head>
<body>
<pre id="out">Chargement…</pre>
<script>
(async () => {{
  const SEP = {sep};
  const pre = document.getElementById("out");
  const r = await fetch("/selftest", {{ headers: {{ Accept: "text/plain" }} }});
  if (!r.ok) {{ pre.textContent = "HTTP " + r.status; return; }}
  const dec = new TextDecoder();
  const reader = r.body.getReader();
  let buf = "";
  while (true) {{
    const {{ done, value }} = await reader.read();
    if (value) buf += dec.decode(value, {{ stream: true }});
    const parts = buf.split(SEP);
    buf = parts.pop() ?? "";
    for (const p of parts) {{
      const t = p.replace(/^\\n+|\\n+$/g, "");
      if (t) pre.textContent = t;
    }}
    if (done) break;
  }}
  const tail = buf.replace(/^\\n+|\\n+$/g, "");
  if (tail) pre.textContent = tail;
}})();
</script>
</body>
</html>"""


@dataclass
class Check:
    name: str
    ok: bool
    detail: str = ""
    duration_ms: int = 0


def _probe(name: str, fn: Callable[[], tuple[bool, str]]) -> Check:
    t0 = time.monotonic()
    try:
        ok, detail = fn()
        return Check(name, ok, detail, int((time.monotonic() - t0) * 1000))
    # Why: probes check arbitrary external services; any error is a valid "check failed" result.
    except Exception as exc:
        logger.debug("selftest probe %s failed: %s", name, exc)
        return Check(name, False, str(exc)[:120], int((time.monotonic() - t0) * 1000))


def _fmt(check: Check) -> str:
    icon = "\u2705" if check.ok else "\u274c"
    line = f"{icon} {check.name}"
    if check.detail:
        line += f"  \u2014  {check.detail}"
    if check.duration_ms:
        line += f"  ({check.duration_ms}ms)"
    return line


def _fmt_pending(name: str) -> str:
    return f"[PENDING]  {name}"


def _render_snapshot(names: list[str], results: list[Check | None]) -> str:
    total = len(names)
    done = [c for c in results if c is not None]
    passed = sum(1 for c in done if c.ok)
    failed = sum(1 for c in done if not c.ok)
    pending_n = sum(1 for c in results if c is None)

    header = f"Autometa selftest  —  {passed}/{total} OK"
    if pending_n:
        header += f"  ({pending_n} pending)"
    elif failed:
        header += f"  ({failed} failed)"

    lines = [header, ""]
    for i, name in enumerate(names):
        c = results[i]
        lines.append(_fmt(c) if c is not None else _fmt_pending(name))
    lines.append("")
    return "\n".join(lines)


def _check_postgresql() -> tuple[bool, str]:
    from sqlalchemy import text

    from .db import get_db

    with get_db() as session:
        ok = session.scalar(text("SELECT 1"))
    return (ok == 1, "")


def _check_admin_users() -> tuple[bool, str]:
    from sqlalchemy import select

    from .db import get_db
    from .models import Conversation

    n = len(config.ADMIN_USERS)
    if not n:
        return (False, "ADMIN_USERS is empty")

    with get_db() as session:
        found = session.scalar(
            select(Conversation.user_id).where(Conversation.user_id.in_(list(config.ADMIN_USERS))).limit(1)
        )
    if found:
        return (True, f"{n} configured, at least 1 active")
    return (True, f"{n} configured (none active yet)")


def _check_task_runner() -> tuple[bool, str]:
    from .runner import runner

    running = len(runner._running)
    return (True, f"{running} running on worker {runner._worker_id}")


def _check_redis() -> tuple[bool, str]:
    import time

    import redis

    from . import config

    t0 = time.monotonic()
    r = redis.from_url(config.REDIS_URL)
    r.ping()
    latency_ms = int((time.monotonic() - t0) * 1000)
    r.close()
    return (True, f"ping {latency_ms}ms")


def _check_conversation_roundtrip() -> tuple[bool, str]:
    from sqlalchemy import delete

    from .database import store
    from .db import get_db
    from .models import Conversation, Message

    conv = store.create_conversation(user_id="selftest@localhost")
    store.add_message(conv.id, "user", "selftest ping")
    msgs = store.get_messages(conv.id)
    ok = len(msgs) >= 1
    with get_db() as session:
        session.execute(delete(Message).where(Message.conversation_id == conv.id))
        session.execute(delete(Conversation).where(Conversation.id == conv.id))
    return (ok, "create/write/read/delete OK")


def _check_claude_cli() -> tuple[bool, str]:
    """`claude --version` from repo root + one folder name per `skills/<name>/SKILL.md`."""
    result = subprocess.run(
        [config.CLAUDE_CLI, "--version"],
        cwd=str(config.BASE_DIR),
        capture_output=True,
        text=True,
        timeout=SELFTEST_TIMEOUT_SEC,
    )
    if result.returncode != 0:
        return (False, (result.stderr or result.stdout).strip()[:120])
    cli_line = result.stdout.strip().split("\n")[0][:80]

    skills_root = config.BASE_DIR / "skills"
    if not skills_root.is_dir():
        return (False, f"{cli_line}; skills/ missing")
    names = sorted(p.name for p in skills_root.iterdir() if p.is_dir() and (p / "SKILL.md").is_file())
    if not names:
        return (False, f"{cli_line}; no skills/*/SKILL.md")

    tail = ", ".join(names)
    if len(tail) > 90:
        tail = tail[:87] + "..."
    return (True, f"{cli_line}; {len(names)} skills: {tail}")


def _check_claude_status_page() -> tuple[bool, str]:
    url = "https://status.claude.com/api/v2/summary.json"
    resp = requests.get(url, timeout=5, headers={"Accept": "application/json"})
    if resp.status_code != 200:
        return (False, f"HTTP {resp.status_code}")
    try:
        data = resp.json()
    except json.JSONDecodeError:
        return (False, "invalid JSON")
    status = data.get("status") or {}
    indicator = status.get("indicator") or ""
    description = (status.get("description") or "").strip() or indicator or "unknown"
    components = data.get("components") or []
    non_op = [c["name"] for c in components if c.get("status") != "operational"]
    if indicator == "none" and not non_op:
        return (True, description)
    extra = ", ".join(non_op[:8])
    if len(non_op) > 8:
        extra += f", +{len(non_op) - 8} more"
    msg = f"{description} ({extra})" if extra else description
    return (False, msg[:240])


def _check_claude_code_ping() -> tuple[bool, str]:
    result = subprocess.run(
        [
            config.CLAUDE_CLI,
            "--print",
            "-p",
            "Reply with exactly the single word: pong",
        ],
        capture_output=True,
        text=True,
        timeout=30,
        cwd=str(config.BASE_DIR),
    )
    if result.returncode != 0:
        err = (result.stderr or result.stdout or "").strip()[:120]
        return (False, err or "non-zero exit")
    if "pong" in result.stdout.lower():
        return (True, "API OK")
    return (False, "no pong in output")


def _check_s3() -> tuple[bool, str]:
    if not config.USE_S3:
        return (False, "not configured (USE_S3=false)")
    from . import s3

    filename = "apps-list.json"
    if not s3.file_exists(filename):
        return (False, f"object not found: {filename}")
    return (True, f"bucket={config.S3_BUCKET} object {filename}")


def _check_matomo() -> tuple[bool, str]:
    from lib.query import get_matomo

    api = get_matomo("inclusion")
    resp = requests.get(
        f"https://{api.url}/index.php",
        params={
            "module": "API",
            "method": "API.getMatomoVersion",
            "format": "json",
            "token_auth": api.token,
        },
        timeout=SELFTEST_TIMEOUT_SEC,
    )
    resp.raise_for_status()
    version = resp.json().get("value", "?")[:40]
    return (True, f"v{version}")


def _check_metabase_instance(instance: str) -> tuple[bool, str]:
    from lib.sources import get_source_config

    cfg = get_source_config("metabase", instance)
    url = cfg["url"].rstrip("/") + "/api/health"
    resp = requests.get(url, timeout=SELFTEST_TIMEOUT_SEC)
    if resp.status_code == 200:
        return (True, "healthy")
    return (False, f"HTTP {resp.status_code}")


def _check_notion() -> tuple[bool, str]:
    token = config.NOTION_TOKEN
    if not token:
        return (False, "NOTION_TOKEN not set")
    resp = requests.get(
        "https://api.notion.com/v1/users/me",
        headers={
            "Authorization": f"Bearer {token}",
            "Notion-Version": "2022-06-28",
        },
        timeout=SELFTEST_TIMEOUT_SEC,
    )
    if resp.status_code == 200:
        return (True, f"bot: {resp.json().get('name', 'ok')}")
    return (False, f"HTTP {resp.status_code}")


def _check_grist() -> tuple[bool, str]:
    api_key = config.GRIST_API_KEY
    doc_id = config.GRIST_WEBINAIRES_DOC_ID
    if not api_key or not doc_id:
        return (False, "GRIST_API_KEY or DOC_ID not set")
    resp = requests.get(
        f"https://grist.numerique.gouv.fr/api/docs/{doc_id}/tables",
        headers={"Authorization": f"Bearer {api_key}"},
        timeout=SELFTEST_TIMEOUT_SEC,
    )
    if resp.status_code == 200:
        n = len(resp.json().get("tables", []))
        return (True, f"{n} tables")
    return (False, f"HTTP {resp.status_code}")


def _check_livestorm() -> tuple[bool, str]:
    api_key = config.LIVESTORM_API_KEY
    if not api_key:
        return (False, "LIVESTORM_API_KEY not set")
    resp = requests.get(
        "https://api.livestorm.co/v1/ping",
        headers={"Authorization": api_key},
        timeout=SELFTEST_TIMEOUT_SEC,
    )
    if resp.status_code == 200:
        return (True, "reachable")
    return (False, f"HTTP {resp.status_code}")


def _check_slack() -> tuple[bool, str]:
    token = config.SLACK_BOT_TOKEN
    if not token:
        return (False, "SLACK_BOT_TOKEN not set")
    resp = requests.head(
        "https://slack.com/api/auth.test",
        headers={"Authorization": f"Bearer {token}"},
        timeout=SELFTEST_TIMEOUT_SEC,
    )
    if resp.status_code == 200:
        return (True, "API reachable")
    return (False, f"HTTP {resp.status_code}")


def _check_specs() -> list[tuple[str, Callable[[], tuple[bool, str]]]]:
    specs: list[tuple[str, Callable[[], tuple[bool, str]]]] = [
        ("PostgreSQL", _check_postgresql),
        ("Admin users", _check_admin_users),
        ("Redis", _check_redis),
        ("Task Runner", _check_task_runner),
        ("Conversation roundtrip", _check_conversation_roundtrip),
        ("Claude CLI", _check_claude_cli),
        ("Claude status page", _check_claude_status_page),
        ("Claude Code API ping", _check_claude_code_ping),
        ("S3", _check_s3),
        ("Matomo", _check_matomo),
    ]
    for inst in list_instances("metabase"):
        specs.append((f"Metabase ({inst})", lambda i=inst: _check_metabase_instance(i)))
    specs += [
        ("Notion", _check_notion),
        ("Grist", _check_grist),
        ("Livestorm", _check_livestorm),
        ("Slack", _check_slack),
    ]
    return specs


def _run_all_checks() -> list[Check]:
    return [_probe(name, fn) for name, fn in _check_specs()]


async def _run_checks_streaming():
    specs = _check_specs()
    names = [n for n, _ in specs]
    results: list[Check | None] = [None] * len(names)

    async def one(i: int, name: str, fn: Callable[[], tuple[bool, str]]) -> tuple[int, Check]:
        return i, await asyncio.to_thread(_probe, name, fn)

    pending = {asyncio.create_task(one(i, name, fn)) for i, (name, fn) in enumerate(specs)}

    yield _render_snapshot(names, results)

    while pending:
        done, pending = await asyncio.wait(pending, return_when=asyncio.FIRST_COMPLETED)
        for task in done:
            idx, check = task.result()
            results[idx] = check
            yield _render_snapshot(names, results)


@router.get("/selftest")
async def selftest(request: Request):
    if _first_accept(request.headers.get("accept", "")) == "text/html":
        return HTMLResponse(_selftest_page_html())

    async def body():
        async for chunk in _run_checks_streaming():
            yield chunk + SNAPSHOT_SEP

    return StreamingResponse(body(), media_type="text/plain; charset=utf-8")
