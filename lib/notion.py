"""Notion API client — read databases/pages and publish reports."""

import re
import time
from urllib.parse import quote

import httpx

from web import config

NOTION_TOKEN = config.NOTION_TOKEN
NOTION_REPORTS_DB = config.NOTION_REPORTS_DB


def is_configured() -> bool:
    return bool(NOTION_TOKEN and NOTION_REPORTS_DB)


def notion_request(method: str, endpoint: str, payload: dict | None = None) -> dict:
    headers = {
        "Authorization": f"Bearer {NOTION_TOKEN}",
        "Notion-Version": "2022-06-28",
        "Content-Type": "application/json",
    }
    url = f"https://api.notion.com/v1/{endpoint}"
    # Why: Notion limite à ~3 req/s ; on retente sur 429 (en respectant Retry-After) avant d'abandonner.
    for _ in range(4):
        resp = httpx.request(method, url, json=payload, headers=headers, timeout=30)
        if resp.status_code != 429:
            resp.raise_for_status()
            return resp.json()
        time.sleep(float(resp.headers.get("Retry-After", 1)))
    raise RuntimeError(f"Notion API rate-limited after retries: {endpoint}")


def db_id_from_url(url: str) -> str:
    """Database/page id from a Notion URL, formatted as a UUID."""
    # Why: l'id (32 hex contigus ou en UUID) est dans le chemin ; le `?v=...`/`#...` est à ignorer.
    path = url.split("?", 1)[0].split("#", 1)[0]
    matches = re.findall(
        r"[0-9a-fA-F]{8}-[0-9a-fA-F]{4}-[0-9a-fA-F]{4}-[0-9a-fA-F]{4}-[0-9a-fA-F]{12}|[0-9a-fA-F]{32}",
        path,
    )
    if not matches:
        raise ValueError(f"No Notion id found in URL: {url}")
    raw = matches[-1].replace("-", "")
    return f"{raw[:8]}-{raw[8:12]}-{raw[12:16]}-{raw[16:20]}-{raw[20:]}"


def query_database(db_id: str) -> list[dict]:
    """All rows of a Notion database (paginated)."""
    pages = []
    cursor = None
    while True:
        payload = {"page_size": 100}
        if cursor:
            payload["start_cursor"] = cursor
        data = notion_request("POST", f"databases/{db_id}/query", payload)
        pages.extend(data["results"])
        if not data.get("has_more"):
            break
        cursor = data.get("next_cursor")
    return pages


def get_block_children(block_id: str) -> list[dict]:
    """All child blocks of a block/page, recursing into nested blocks (paginated)."""
    blocks = []
    cursor = None
    while True:
        endpoint = f"blocks/{block_id}/children?page_size=100"
        if cursor:
            endpoint += f"&start_cursor={quote(cursor, safe='')}"
        data = notion_request("GET", endpoint)
        for block in data["results"]:
            blocks.append(block)
            if block.get("has_children"):
                blocks.extend(get_block_children(block["id"]))
        if not data.get("has_more"):
            break
        cursor = data.get("next_cursor")
    return blocks


def extract_text_from_rich_text(rich_text_list: list[dict]) -> str:
    return "".join(t.get("plain_text", "") for t in rich_text_list)


def extract_block_text(block: dict) -> str:
    btype = block["type"]
    bdata = block.get(btype, {})
    if "rich_text" in bdata:
        return extract_text_from_rich_text(bdata["rich_text"])
    if "text" in bdata:
        return extract_text_from_rich_text(bdata["text"])
    if btype in ("child_page", "child_database"):
        return bdata.get("title", "")
    return ""


def extract_page_title(page: dict) -> str:
    for val in page["properties"].values():
        if val["type"] == "title":
            return extract_text_from_rich_text(val.get("title", []))
    return ""


def extract_page_properties(page: dict) -> dict:
    props = {}
    for name, val in page["properties"].items():
        ptype = val["type"]
        if ptype == "title":
            props[name] = extract_text_from_rich_text(val.get("title", []))
        elif ptype == "rich_text":
            props[name] = extract_text_from_rich_text(val.get("rich_text", []))
        elif ptype == "select":
            sel = val.get("select")
            props[name] = sel["name"] if sel else None
        elif ptype == "multi_select":
            props[name] = [o["name"] for o in val.get("multi_select", [])]
        elif ptype == "date":
            d = val.get("date")
            props[name] = d["start"] if d else None
        elif ptype == "relation":
            props[name] = [r["id"] for r in val.get("relation", [])]
        elif ptype == "people":
            props[name] = [p.get("name", p.get("id", "")) for p in val.get("people", [])]
        elif ptype == "formula":
            f = val.get("formula", {})
            ftype = f.get("type")
            props[name] = f.get(ftype) if ftype else None
        else:
            props[name] = None
    return props


def parse_inline(text: str) -> list[dict]:
    results = []
    pattern = re.compile(
        r"\*\*(.+?)\*\*"  # bold
        r"|\*(.+?)\*"  # italic
        r"|`([^`]+)`"  # inline code
        r"|\[([^\]]+)\]\(([^)]+)\)"  # link
        r"|([^*`\[]+)"  # plain text
        r"|(.)"  # fallback single char
    )
    for m in pattern.finditer(text):
        bold, italic, code, link_text, link_url, plain, fallback = m.groups()
        if bold:
            results.append(rich_text(bold, bold=True))
        elif italic:
            results.append(rich_text(italic, italic=True))
        elif code:
            results.append(rich_text(code, code=True))
        elif link_text:
            results.append(rich_text(link_text, link=link_url))
        elif plain:
            results.append(rich_text(plain))
        elif fallback:
            results.append(rich_text(fallback))
    return results or [rich_text("")]


def rich_text(content: str, bold=False, italic=False, code=False, link=None) -> dict:
    content = content[:2000]
    obj = {
        "type": "text",
        "text": {"content": content},
        "annotations": {
            "bold": bold,
            "italic": italic,
            "code": code,
            "strikethrough": False,
            "underline": False,
            "color": "default",
        },
    }
    if link:
        obj["text"]["link"] = {"url": link}
    return obj


NOTION_CODE_LANG_MAP = {
    "django": "html",
    "bash": "bash",
    "python": "python",
    "javascript": "javascript",
    "html": "html",
    "mermaid": "mermaid",
    "yaml": "yaml",
    "json": "json",
    "css": "css",
    "sql": "sql",
    "shell": "bash",
    "sh": "bash",
}


def markdown_to_blocks(md: str) -> list[dict]:
    # Strip YAML frontmatter
    md = re.sub(r"^---\n.*?\n---\n", "", md, flags=re.DOTALL)

    lines = md.split("\n")
    blocks = []
    i = 0

    while i < len(lines):
        line = lines[i]

        if not line.strip():
            i += 1
            continue

        if re.match(r"^---+\s*$", line):
            blocks.append({"type": "divider", "divider": {}})
            i += 1
            continue

        heading_match = re.match(r"^(#{1,3})\s+(.*)", line)
        if heading_match:
            level = len(heading_match.group(1))
            text = heading_match.group(2).strip()
            htype = f"heading_{level}"
            blocks.append({"type": htype, htype: {"rich_text": parse_inline(text)}})
            i += 1
            continue

        code_match = re.match(r"^```(\w*)", line)
        if code_match:
            lang = code_match.group(1) or "plain text"
            notion_lang = NOTION_CODE_LANG_MAP.get(lang, lang)
            code_lines = []
            i += 1
            while i < len(lines) and not re.match(r"^```\s*$", lines[i]):
                code_lines.append(lines[i])
                i += 1
            i += 1  # skip closing ```
            code_content = "\n".join(code_lines)
            if len(code_content) > 2000:
                code_content = code_content[:1997] + "..."
            blocks.append({
                "type": "code",
                "code": {
                    "rich_text": [rich_text(code_content)],
                    "language": notion_lang,
                },
            })
            continue

        if "|" in line and re.match(r"^\s*\|", line):
            table_lines = []
            while i < len(lines) and "|" in lines[i] and lines[i].strip():
                table_lines.append(lines[i])
                i += 1
            data_lines = [line for line in table_lines if not re.match(r"^\s*\|[-:\s|]+\|\s*$", line)]
            if data_lines:
                rows = []
                for tl in data_lines:
                    cells = [c.strip() for c in tl.strip().strip("|").split("|")]
                    rows.append(cells)
                col_count = max(len(r) for r in rows)
                table_rows = []
                for row in rows:
                    while len(row) < col_count:
                        row.append("")
                    row = row[:col_count]
                    table_rows.append({
                        "type": "table_row",
                        "table_row": {
                            "cells": [parse_inline(cell) for cell in row],
                        },
                    })
                blocks.append({
                    "type": "table",
                    "table": {
                        "table_width": col_count,
                        "has_column_header": True,
                        "has_row_header": False,
                        "children": table_rows,
                    },
                })
            continue

        num_match = re.match(r"^(\d+)\.\s+(.*)", line)
        if num_match:
            blocks.append({
                "type": "numbered_list_item",
                "numbered_list_item": {"rich_text": parse_inline(num_match.group(2))},
            })
            i += 1
            continue

        bullet_match = re.match(r"^[-*]\s+(.*)", line)
        if bullet_match:
            blocks.append({
                "type": "bulleted_list_item",
                "bulleted_list_item": {"rich_text": parse_inline(bullet_match.group(1))},
            })
            i += 1
            continue

        para_lines = []
        while (
            i < len(lines) and lines[i].strip() and not re.match(r"^(#{1,3}\s|```|---|\|.*\||\d+\.\s|[-*]\s)", lines[i])
        ):
            para_lines.append(lines[i])
            i += 1
        if para_lines:
            blocks.append({
                "type": "paragraph",
                "paragraph": {"rich_text": parse_inline(" ".join(para_lines))},
            })
            continue

        i += 1

    return blocks


def publish_report(
    title: str,
    content: str,
    website: str | None = None,
    original_query: str | None = None,
    date: str | None = None,
) -> tuple[str, str]:
    """Publish markdown content to Notion. Returns (page_id, url)."""
    if not is_configured():
        raise RuntimeError("Notion not configured (NOTION_TOKEN / NOTION_REPORTS_DB)")

    # Frontmatter is the authoritative source, overrides passed DB fields.
    fm_date = None
    fm_query = None
    m = re.search(r"^date:\s*(\d{4}-\d{2}-\d{2})", content, re.MULTILINE)
    if m:
        fm_date = m.group(1)
    m = re.search(r'^original_query:\s*"?(.+?)"?\s*$', content, re.MULTILINE)
    if m:
        fm_query = m.group(1)

    date = fm_date or date
    original_query = fm_query or original_query

    properties = {
        "Titre": {"title": [{"text": {"content": title}}]},
    }
    if date:
        properties["Date de publication"] = {"date": {"start": date}}
    if website:
        properties["Produits concernés"] = {
            "multi_select": [{"name": website}],
        }
    if original_query:
        properties["Requête initiale"] = {
            "rich_text": [{"text": {"content": original_query[:2000]}}],
        }

    result = notion_request(
        "POST",
        "pages",
        {"parent": {"database_id": NOTION_REPORTS_DB}, "properties": properties},
    )
    page_id = result["id"]
    page_url = result["url"]

    blocks = markdown_to_blocks(content)
    for i in range(0, len(blocks), 100):
        batch = blocks[i : i + 100]
        notion_request("PATCH", f"blocks/{page_id}/children", {"children": batch})

    return page_id, page_url
