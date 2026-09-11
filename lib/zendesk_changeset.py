"""Reviewable, revertible batches of Zendesk Guide article edits, persisted on S3 without any DB table."""

import difflib
import gzip
import json
import logging
import re
from collections.abc import Callable
from datetime import datetime
from typing import Any, Optional

from web import s3

from .zendesk import Article, ZendeskAPI, ZendeskError

logger = logging.getLogger(__name__)

Transform = Callable[[str, str], tuple[str, str]]

__all__ = ["plan", "replace", "apply", "revert", "show", "list_changesets", "export_articles"]


def slugify(text: str) -> str:
    return re.sub(r"[^a-z0-9]+", "-", text.lower()).strip("-")[:40] or "changeset"


def content(article: Article) -> dict:
    return {"title": article.title, "body": article.body, "updated_at": article.updated_at}


def read_json(path: str) -> Optional[Any]:
    raw = s3.zendesk.download(path)
    if raw is None:
        return None
    if path.endswith(".gz"):
        raw = gzip.decompress(raw)
    return json.loads(raw)


def write_json(path: str, data: Any) -> None:
    raw = json.dumps(data, ensure_ascii=False, indent=1).encode()
    if path.endswith(".gz"):
        raw = gzip.compress(raw)
    if not s3.zendesk.upload(path, raw):
        raise RuntimeError(f"S3 upload failed for {path}")


def article_diff(before: dict, after: dict, article: dict) -> str:
    lines = [f"## {article['title']} (#{article['id']})", article["html_url"], ""]
    if before["title"] != after["title"]:
        lines += [f"Titre : {before['title']!r} → {after['title']!r}", ""]
    body = difflib.unified_diff(
        before["body"].splitlines(), after["body"].splitlines(), "avant", "après", lineterm="", n=1
    )
    lines += ["```diff", *body, "```", ""]
    return "\n".join(lines)


def plan(
    articles: list[Article], transform: Transform, label: str, params: Optional[dict] = None, **notes: Any
) -> Optional[dict]:
    """Snapshot before/after for every article the transform changes; None when nothing changes."""
    before, after, entries = {}, {}, []
    for article in articles:
        title, body = transform(article.title, article.body)
        if (title, body) == (article.title, article.body):
            continue
        before[str(article.id)] = content(article)
        after[str(article.id)] = {"title": title, "body": body}
        added = sum(1 for line in difflib.ndiff(article.body.splitlines(), body.splitlines()) if line.startswith("+ "))
        entries.append({"id": article.id, "title": article.title, "html_url": article.html_url, "lines_changed": added})
    if not entries:
        return None
    changeset_id = f"{datetime.now().strftime('%Y-%m-%d-%H%M')}-{slugify(label)}"
    manifest = {
        "id": changeset_id,
        "label": label,
        "status": "planned",
        "created_at": datetime.now().isoformat(timespec="seconds"),
        "params": params or {},
        "articles": entries,
        "scanned": len(articles),
        **notes,
    }
    prefix = f"changesets/{changeset_id}"
    write_json(f"{prefix}/before.json.gz", before)
    write_json(f"{prefix}/after.json.gz", after)
    diff = "\n".join(article_diff(before[str(e["id"])], after[str(e["id"])], e) for e in entries)
    s3.zendesk.upload(f"{prefix}/diff.md", f"# {label}\n\n{diff}".encode(), "text/markdown; charset=utf-8")
    write_json(f"{prefix}/manifest.json", manifest)
    return {**manifest, "diff_url": s3.zendesk.get_url(f"{prefix}/diff.md", expires_in=86400)}


def split_markup(body: str) -> list[str]:
    """Alternate visible-text and tag segments; odd indexes are tags."""
    return re.split(r"(<[^>]*>)", body)


def replace(
    api: ZendeskAPI,
    pattern: str,
    replacement: str,
    regex: bool = False,
    include_markup: bool = False,
    articles: Optional[list[Article]] = None,
    label: Optional[str] = None,
) -> Optional[dict]:
    """Plan a search-and-replace over titles and the visible text of bodies; tags and attributes only on request."""
    if not pattern:
        raise ValueError("texte cherché vide")
    compiled = re.compile(pattern if regex else re.escape(pattern))
    sub = replacement if regex else replacement.replace("\\", r"\\")

    def transform(title: str, body: str) -> tuple[str, str]:
        segments = split_markup(body)
        new_body = "".join(
            compiled.sub(sub, seg) if include_markup or i % 2 == 0 else seg for i, seg in enumerate(segments)
        )
        return compiled.sub(sub, title), new_body

    if articles is None:
        articles = api.list_articles()
    markup_hits = {
        a.id: hits for a in articles if (hits := sum(len(compiled.findall(seg)) for seg in split_markup(a.body)[1::2]))
    }
    structure_hits = [
        {"kind": kind, "id": item["id"], "name": item["name"]}
        for kind, items in (("section", api.list_sections()), ("category", api.list_categories()))
        for item in items
        if compiled.search(item["name"])
    ]
    params = {"pattern": pattern, "replacement": replacement, "regex": regex, "include_markup": include_markup}
    return plan(
        articles,
        transform,
        label or f"remplacer {pattern}",
        params,
        markup_hits=markup_hits,
        structure_hits=structure_hits,
    )


def load(changeset_id: str, *expected_status: str) -> dict:
    manifest = read_json(f"changesets/{changeset_id}/manifest.json")
    if manifest is None:
        raise ValueError(f"changeset {changeset_id} introuvable")
    if manifest["status"] not in expected_status:
        raise ValueError(f"changeset {changeset_id} est {manifest['status']}, attendu {' ou '.join(expected_status)}")
    return manifest


def set_status(manifest: dict, status: str) -> None:
    manifest["status"] = status
    write_json(f"changesets/{manifest['id']}/manifest.json", manifest)


def write_guarded(api: ZendeskAPI, ids: list[str], expected: dict, target: dict, report_path: str) -> dict:
    """Write target where live content still equals expected, skip or log otherwise; checkpointed after each article."""
    report: dict[str, Any] = read_json(report_path) or {"written": {}, "skipped": [], "errors": []}
    done = set(report["written"]) | {str(x["id"]) for x in report["skipped"] + report["errors"]}
    for article_id in ids:
        if article_id in done:
            continue
        try:
            current = api.get_article(int(article_id))
            if (current.title, current.body) != (expected[article_id]["title"], expected[article_id]["body"]):
                report["skipped"].append({
                    "id": int(article_id),
                    "reason": "modifié entre-temps",
                    "expected_updated_at": expected[article_id].get("updated_at"),
                    "updated_at": current.updated_at,
                })
                continue
            stored = api.update_article_content(current.id, target[article_id]["title"], target[article_id]["body"])
            report["written"][article_id] = content(stored)
        except ZendeskError as exc:
            logger.warning("Zendesk article %s skipped: %s", article_id, exc)
            report["errors"].append({"id": int(article_id), "error": str(exc)})
        write_json(report_path, report)
    return report


def apply(api: ZendeskAPI, changeset_id: str) -> dict:
    """Apply a planned changeset; articles edited since the plan are skipped, never overwritten. Resumes an interrupted run."""
    manifest = load(changeset_id, "planned", "applying")
    prefix = f"changesets/{changeset_id}"
    before, after = read_json(f"{prefix}/before.json.gz"), read_json(f"{prefix}/after.json.gz")
    set_status(manifest, "applying")
    report = write_guarded(api, list(before), before, after, f"{prefix}/applied.json")
    set_status(manifest, "applied")
    return summary(manifest, report)


def revert(api: ZendeskAPI, changeset_id: str) -> dict:
    """Restore the pre-changeset content of every article the apply actually wrote, with the same guard."""
    manifest = load(changeset_id, "applied", "applying")
    prefix = f"changesets/{changeset_id}"
    before, applied = read_json(f"{prefix}/before.json.gz"), read_json(f"{prefix}/applied.json")
    set_status(manifest, "reverting")
    report = write_guarded(api, list(applied["written"]), applied["written"], before, f"{prefix}/reverted.json")
    set_status(manifest, "reverted")
    return summary(manifest, report)


def summary(manifest: dict, report: dict) -> dict:
    return {
        "id": manifest["id"],
        "status": manifest["status"],
        "written": len(report["written"]),
        "skipped": report["skipped"],
        "errors": report["errors"],
    }


def show(changeset_id: str) -> dict:
    prefix = f"changesets/{changeset_id}"
    manifest = read_json(f"{prefix}/manifest.json")
    if manifest is None:
        raise ValueError(f"changeset {changeset_id} introuvable")
    applied = read_json(f"{prefix}/applied.json") or {"written": {}, "skipped": [], "errors": []}
    done = set(applied["written"]) | {str(x["id"]) for x in applied["skipped"] + applied["errors"]}
    return {
        **manifest,
        "diff_url": s3.zendesk.get_url(f"{prefix}/diff.md", expires_in=86400),
        "applied": applied,
        "remaining": [e for e in manifest["articles"] if str(e["id"]) not in done],
        "reverted": read_json(f"{prefix}/reverted.json"),
    }


def list_changesets() -> list[dict]:
    """Manifests of every changeset, newest first."""
    manifests = [read_json(f"changesets/{d}/manifest.json") for d in s3.zendesk.list_directories("changesets/")]
    return sorted((m for m in manifests if m), key=lambda m: m["id"], reverse=True)


def export_articles(api: ZendeskAPI) -> dict:
    """Dump every article's raw payload to S3, gzipped; returns path, count and a presigned URL."""
    articles = api.list_articles()
    path = f"exports/{datetime.now().strftime('%Y-%m-%dT%H-%M')}-articles.json.gz"
    write_json(path, [a.raw for a in articles])
    return {"path": path, "count": len(articles), "url": s3.zendesk.get_url(path, expires_in=86400)}
