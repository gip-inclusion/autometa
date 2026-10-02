"""Reviewable, revertible batches of Zendesk article or macro edits, persisted on S3 without any DB table."""

import copy
import difflib
import gzip
import json
import logging
import re
from collections.abc import Callable
from datetime import datetime
from typing import Any, Optional

from web import s3

from .zendesk import Article, Macro, ZendeskAPI, ZendeskError

logger = logging.getLogger(__name__)

Transform = Callable[[str, str], tuple[str, str]]

__all__ = ["plan", "plan_items", "replace", "apply", "revert", "show", "list_changesets", "export_articles", "export"]

MARKUP = r"""<!--.*?-->|<(?:[^>"']|"[^"]*"|'[^']*')*>"""


def slugify(text: str) -> str:
    return re.sub(r"[^a-z0-9]+", "-", text.lower()).strip("-")[:40] or "changeset"


def content(item: Article | Macro) -> dict:
    """Editable fields of an article or a macro, plus updated_at for the record."""
    if isinstance(item, Macro):
        fields = {"title": item.title, "description": item.description, "active": item.active}
        return {**fields, "actions": item.actions, "updated_at": item.updated_at}
    return {"title": item.title, "body": item.body, "updated_at": item.updated_at}


def editable(entry: dict) -> dict:
    return {k: v for k, v in entry.items() if k != "updated_at"}


def fetch(api: ZendeskAPI, kind: str, item_id: str) -> Optional[dict]:
    """Live content of one item; None for a macro deleted in Zendesk."""
    if kind == "articles":
        return content(api.get_article(int(item_id)))
    try:
        return content(api.get_macro(int(item_id)))
    except ZendeskError as exc:
        if exc.status_code != 404:
            raise
        return None


def store(api: ZendeskAPI, kind: str, item_id: str, fields: dict) -> dict:
    """Write one item; returns its content exactly as Zendesk stored it."""
    if kind == "articles":
        return api.update_article_content(int(item_id), fields["title"], fields["body"])
    return content(api.update_macro(int(item_id), **fields))


def paragraphs(html: str) -> list[str]:
    return re.sub(r"(</(?:p|li|ul|ol|div|h\d|blockquote|table|tr)>|<br\s*/?>)", "\\1\n", html).splitlines()


def render(kind: str, fields: dict) -> list[str]:
    """Diffable lines of everything but the title, one paragraph per line for HTML replies."""
    if kind == "articles":
        return fields["body"].splitlines()
    lines = [f"Description : {fields['description']}", f"Active : {'oui' if fields['active'] else 'non'}"]
    for action in fields["actions"]:
        if action["field"] == "comment_value_html":
            lines += [f"{action['field']} :", *paragraphs(action["value"])]
        else:
            lines.append(f"{action['field']} : {action['value']}")
    return lines


def read_json(path: str) -> Optional[Any]:
    """Parsed object, None when absent; raises when S3 is unreachable rather than mistaking it for absence."""
    raw = s3.zendesk.download(path)
    if raw is None:
        if s3.zendesk.head(path) != {"exists": False}:
            raise RuntimeError(f"S3 read failed for {path}")
        return None
    if path.endswith(".gz"):
        raw = gzip.decompress(raw)
    return json.loads(raw)


def write_bytes(path: str, raw: bytes, content_type: Optional[str] = None) -> None:
    if not s3.zendesk.upload(path, raw, content_type):
        raise RuntimeError(f"S3 upload failed for {path}")


def write_json(path: str, data: Any) -> None:
    raw = json.dumps(data, ensure_ascii=False, indent=1).encode()
    write_bytes(path, gzip.compress(raw) if path.endswith(".gz") else raw)


def item_diff(kind: str, before: dict, after: dict, entry: dict) -> str:
    lines = [f"## {entry['title']} (#{entry['id']})", entry["html_url"], ""]
    if before["title"] != after["title"]:
        lines += [f"Titre : {before['title']!r} → {after['title']!r}", ""]
    body = difflib.unified_diff(render(kind, before), render(kind, after), "avant", "après", lineterm="", n=1)
    lines += ["```diff", *body, "```", ""]
    return "\n".join(lines)


def plan(
    articles: list[Article], transform: Transform, label: str, params: Optional[dict] = None, **notes: Any
) -> Optional[dict]:
    """Snapshot before/after for every article the transform of (title, body) changes; None when nothing changes."""

    def fields_transform(fields: dict) -> dict:
        return dict(zip(("title", "body"), transform(fields["title"], fields["body"])))

    return plan_items("articles", articles, fields_transform, label, params, **notes)


def plan_items(
    kind: str,
    items: list[Article] | list[Macro],
    transform: Callable[[dict], dict],
    label: str,
    params: Optional[dict] = None,
    **notes: Any,
) -> Optional[dict]:
    """Snapshot before/after for every item whose editable fields the transform changes; None when nothing changes."""
    before, after, entries = {}, {}, []
    for item in items:
        old = content(item)
        new = transform(copy.deepcopy(editable(old)))
        if new == editable(old):
            continue
        before[str(item.id)] = old
        after[str(item.id)] = new
        added = sum(1 for line in difflib.ndiff(render(kind, old), render(kind, new)) if line.startswith("+ "))
        changed = added + (old["title"] != new["title"])
        entries.append({"id": item.id, "title": item.title, "html_url": item.html_url, "lines_changed": changed})
    if not entries:
        return None
    changeset_id = f"{datetime.now().strftime('%Y-%m-%d-%H%M%S')}-{slugify(label)}"
    prefix = f"changesets/{changeset_id}"
    if read_json(f"{prefix}/manifest.json") is not None:
        raise RuntimeError(f"changeset {changeset_id} existe déjà")
    manifest = {
        "id": changeset_id,
        "label": label,
        "status": "planned",
        "kind": kind,
        "created_at": datetime.now().isoformat(timespec="seconds"),
        "params": params or {},
        "articles": entries,
        "scanned": len(items),
        **notes,
    }
    write_json(f"{prefix}/before.json.gz", before)
    write_json(f"{prefix}/after.json.gz", after)
    diff = "\n".join(item_diff(kind, before[str(e["id"])], after[str(e["id"])], e) for e in entries)
    header = "\n".join(f"- {k} : {v!r}" for k, v in (params or {}).items())
    write_bytes(
        f"{prefix}/diff.md",
        f"# {label}\n\nPorte sur : {kind}\n\n{header}\n\n{diff}".encode(),
        "text/markdown; charset=utf-8",
    )
    write_json(f"{prefix}/manifest.json", manifest)
    return {**manifest, "diff_url": s3.zendesk.get_url(f"{prefix}/diff.md", expires_in=86400)}


def split_markup(body: str, protected: str = MARKUP) -> list[str]:
    """Alternate visible-text and protected segments (tags with quoted attributes, comments); odd indexes are protected."""
    return re.split(f"({protected})", body, flags=re.DOTALL)


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


def with_kind(manifest: dict) -> dict:
    """Changesets planned before macros existed carry no kind: they are all article changesets."""
    return {"kind": "articles", **manifest}


def load(changeset_id: str, *expected_status: str) -> dict:
    """Manifest of a changeset, refused unless its status is one of expected_status (any when none given)."""
    manifest = read_json(f"changesets/{changeset_id}/manifest.json")
    if manifest is None:
        raise ValueError(f"changeset {changeset_id} introuvable")
    if expected_status and manifest["status"] not in expected_status:
        raise ValueError(f"changeset {changeset_id} est {manifest['status']}, attendu {' ou '.join(expected_status)}")
    return with_kind(manifest)


def set_status(manifest: dict, status: str) -> None:
    manifest["status"] = status
    write_json(f"changesets/{manifest['id']}/manifest.json", manifest)


def settled(report: dict) -> set[str]:
    """Articles a run will not touch again: written, or skipped by the guard. Errors are retried."""
    return set(report["written"]) | {str(x["id"]) for x in report["skipped"]}


def resolve_pending(api: ZendeskAPI, kind: str, report: dict, expected: dict, report_path: str) -> None:
    """Settle the item whose PUT was in flight when a run died: written unless its content is still the expected one."""
    item_id = report.get("pending")
    if item_id is None:
        return
    current = fetch(api, kind, item_id)
    if current is not None and editable(current) != editable(expected[item_id]):
        report["written"][item_id] = current
        report["errors"] = [e for e in report["errors"] if str(e["id"]) != item_id]
    report["pending"] = None
    write_json(report_path, report)


def write_guarded(api: ZendeskAPI, kind: str, ids: list[str], expected: dict, target: dict, report_path: str) -> dict:
    """Write target where live content still equals expected, skip or log otherwise; checkpointed after each item."""
    report: dict[str, Any] = read_json(report_path) or {"written": {}, "skipped": [], "errors": [], "pending": None}
    resolve_pending(api, kind, report, expected, report_path)
    done = settled(report)
    report["errors"] = []
    for item_id in ids:
        if item_id in done:
            continue
        try:
            current = fetch(api, kind, item_id)
            if current is None or editable(current) != editable(expected[item_id]):
                report["skipped"].append({
                    "id": int(item_id),
                    "title": expected[item_id]["title"],
                    "reason": "supprimé entre-temps" if current is None else "modifié entre-temps",
                    "expected_updated_at": expected[item_id].get("updated_at"),
                    "updated_at": current and current["updated_at"],
                })
                continue
            # Why: the intent is checkpointed before the PUT so that a write whose acknowledgement is lost
            # (crash, or an error on the response) is still found and revertible on the next run.
            report["pending"] = item_id
            write_json(report_path, report)
            report["written"][item_id] = store(api, kind, item_id, editable(target[item_id]))
            report["pending"] = None
        except ZendeskError as exc:
            logger.warning("Zendesk %s %s skipped: %s", kind, item_id, exc)
            report["errors"].append({"id": int(item_id), "title": expected[item_id]["title"], "error": str(exc)})
            resolve_pending(api, kind, report, expected, report_path)
        write_json(report_path, report)
    return report


def apply(api: ZendeskAPI, changeset_id: str) -> dict:
    """Apply a planned changeset; items edited or deleted since the plan are skipped, never overwritten. Resumes."""
    manifest = load(changeset_id, "planned", "applying")
    prefix = f"changesets/{changeset_id}"
    before, after = read_json(f"{prefix}/before.json.gz"), read_json(f"{prefix}/after.json.gz")
    set_status(manifest, "applying")
    report = write_guarded(api, manifest["kind"], list(before), before, after, f"{prefix}/applied.json")
    if not report["errors"]:
        set_status(manifest, "applied")
    return summary(manifest, report)


def revert(api: ZendeskAPI, changeset_id: str) -> dict:
    """Restore the pre-changeset content of every item the apply actually wrote, with the same guard."""
    manifest = load(changeset_id, "applied", "applying", "reverting")
    prefix = f"changesets/{changeset_id}"
    before, applied = read_json(f"{prefix}/before.json.gz"), read_json(f"{prefix}/applied.json")
    set_status(manifest, "reverting")
    resolve_pending(api, manifest["kind"], applied, before, f"{prefix}/applied.json")
    report = write_guarded(
        api, manifest["kind"], list(applied["written"]), applied["written"], before, f"{prefix}/reverted.json"
    )
    if not report["errors"]:
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
    manifest = load(changeset_id)
    applied = read_json(f"{prefix}/applied.json") or {"written": {}, "skipped": [], "errors": [], "pending": None}
    return {
        **manifest,
        "diff_url": s3.zendesk.get_url(f"{prefix}/diff.md", expires_in=86400),
        "applied": applied,
        "remaining": [e for e in manifest["articles"] if str(e["id"]) not in settled(applied)],
        "reverted": read_json(f"{prefix}/reverted.json"),
    }


def list_changesets() -> list[dict]:
    """Manifests of every changeset, newest first."""
    manifests = [read_json(f"changesets/{d}/manifest.json") for d in s3.zendesk.list_directories("changesets/")]
    return sorted((with_kind(m) for m in manifests if m), key=lambda m: m["id"], reverse=True)


def export(name: str, payloads: list[dict]) -> dict:
    """Dump raw payloads to S3, gzipped; returns path, count and a presigned URL."""
    path = f"exports/{datetime.now().strftime('%Y-%m-%dT%H-%M')}-{name}.json.gz"
    write_json(path, payloads)
    return {"path": path, "count": len(payloads), "url": s3.zendesk.get_url(path, expires_in=86400)}


def export_articles(api: ZendeskAPI) -> dict:
    """Dump every article's raw payload to S3, gzipped; returns path, count and a presigned URL."""
    return export("articles", [a.raw for a in api.list_articles()])
