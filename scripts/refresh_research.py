#!/usr/bin/env python3
"""Incremental sync + embed for Notion 'Connaissance du terrain' databases.

Combines sync_notion_research.py and embed_notion_research.py into a single
incremental pipeline:

1. Query each Notion database for pages
2. Compare last_edited_time to detect new/changed/deleted pages
3. Only re-fetch blocks for changed pages
4. Rebuild chunks, but preserve embeddings for unchanged chunk text
5. Only embed new/changed chunks locally with sentence-transformers

Usage:
    python scripts/refresh_research.py
    python scripts/refresh_research.py --full     # force full rebuild
    python scripts/refresh_research.py --db data/notion_research.db
"""

import argparse
import hashlib
import json
import os
import sqlite3
import sys
import time
import urllib.error
import urllib.request
from collections import Counter
from datetime import datetime
from pathlib import Path

import numpy as np
from dotenv import load_dotenv

load_dotenv(Path(__file__).parent.parent / ".env")

NOTION_TOKEN = os.getenv("NOTION_TOKEN")
DEFAULT_DB_PATH = Path(__file__).parent.parent / "data" / "notion_research.db"

MODEL_NAME = "Qwen/Qwen3-Embedding-0.6B"
CHUNK_THRESHOLD = 5
CHUNK_TARGET_CHARS = 400
CHUNK_MAX_CHARS = 1500

DATABASES = {
    "entretiens": {
        "id": "28d5f321-b604-8101-a7e9-f2f705cbb2c3",
        "name": "Entretiens et actions de recherche",
    },
    "thematiques": {
        "id": "28d5f321-b604-80dc-923a-dfad38e4592c",
        "name": "Thématiques de recherche",
    },
    "segments": {
        "id": "28d5f321-b604-8094-8a13-cbe09f2810bf",
        "name": "Segments",
    },
    "profils": {
        "id": "1885f321-b604-817a-ad43-d8ea18689279",
        "name": "Profils (Cibles précises)",
    },
    "hypotheses": {
        "id": "28d5f321-b604-81de-86db-eaf2ee71e29d",
        "name": "Hypothèses et questions qu'on se pose",
    },
    "conclusions": {
        "id": "28d5f321-b604-80fb-aa4b-f92b13dd0993",
        "name": "Conclusions",
    },
}

HEADERS = {
    "Authorization": f"Bearer {NOTION_TOKEN}",
    "Notion-Version": "2022-06-28",
    "Content-Type": "application/json",
}

# Rate limiting
REQUEST_INTERVAL = 0.34  # ~3 req/s
_last_request_time = 0.0
_request_count = 0


# =============================================================================
# Notion API helpers (from sync_notion_research.py)
# =============================================================================

def _rate_limited_request(url, data=None, method="GET", max_retries=5):
    global _last_request_time, _request_count
    for attempt in range(max_retries):
        elapsed = time.time() - _last_request_time
        if elapsed < REQUEST_INTERVAL:
            time.sleep(REQUEST_INTERVAL - elapsed)
        req = urllib.request.Request(url, headers=HEADERS, method=method)
        if data:
            req.data = json.dumps(data).encode("utf-8")
        _last_request_time = time.time()
        _request_count += 1
        try:
            with urllib.request.urlopen(req, timeout=30) as resp:
                return json.loads(resp.read().decode("utf-8"))
        except urllib.error.HTTPError as e:
            if e.code == 429:
                retry_after = int(e.headers.get("Retry-After", 1))
                print(f"  Rate limited, waiting {retry_after}s...")
                time.sleep(retry_after)
                continue
            body = e.read().decode("utf-8")[:200]
            print(f"  HTTP {e.code}: {body}")
            raise
    raise RuntimeError(f"Max retries exceeded for {url}")


def query_database(db_id):
    pages = []
    cursor = None
    while True:
        payload = {"page_size": 100}
        if cursor:
            payload["start_cursor"] = cursor
        data = _rate_limited_request(
            f"https://api.notion.com/v1/databases/{db_id}/query",
            data=payload,
            method="POST",
        )
        pages.extend(data["results"])
        if not data.get("has_more"):
            break
        cursor = data.get("next_cursor")
    return pages


def get_block_children(block_id):
    blocks = []
    cursor = None
    while True:
        url = f"https://api.notion.com/v1/blocks/{block_id}/children?page_size=100"
        if cursor:
            url += f"&start_cursor={cursor}"
        data = _rate_limited_request(url)
        for block in data["results"]:
            blocks.append(block)
            if block.get("has_children"):
                blocks.extend(get_block_children(block["id"]))
        if not data.get("has_more"):
            break
        cursor = data.get("next_cursor")
    return blocks


def extract_text_from_rich_text(rich_text_list):
    return "".join(t.get("plain_text", "") for t in rich_text_list)


def extract_block_text(block):
    btype = block["type"]
    bdata = block.get(btype, {})
    if "rich_text" in bdata:
        return extract_text_from_rich_text(bdata["rich_text"])
    if "text" in bdata:
        return extract_text_from_rich_text(bdata["text"])
    if btype == "child_page":
        return bdata.get("title", "")
    if btype == "child_database":
        return bdata.get("title", "")
    return ""


def extract_page_title(page):
    for _name, val in page["properties"].items():
        if val["type"] == "title":
            return extract_text_from_rich_text(val.get("title", []))
    return ""


def extract_page_properties(page):
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
            props[name] = [
                p.get("name", p.get("id", "")) for p in val.get("people", [])
            ]
        elif ptype == "formula":
            f = val.get("formula", {})
            ftype = f.get("type")
            props[name] = f.get(ftype) if ftype else None
        elif ptype == "rollup":
            props[name] = None
        else:
            props[name] = None
    return props


# =============================================================================
# Chunking helpers (from embed_notion_research.py)
# =============================================================================

def get_page_block_texts(conn, page_id):
    rows = conn.execute(
        "SELECT text_content FROM blocks WHERE page_id = ? ORDER BY position",
        (page_id,),
    ).fetchall()
    return [r["text_content"] for r in rows if r["text_content"] and r["text_content"].strip()]


def resolve_relation_names(conn, page_id, property_name):
    rows = conn.execute(
        """
        SELECT p.title FROM relations r
        JOIN pages p ON p.id = r.target_page_id
        WHERE r.source_page_id = ? AND r.property_name = ?
        """,
        (page_id, property_name),
    ).fetchall()
    return [r["title"] for r in rows if r["title"]]


def build_page_context(conn, page):
    page_id = page["id"]
    parts = [f"[{page['database_name']}]"]
    for prop in ["Thématiques", "Cible générale", "Cibles précises", "Hypothèses", "Conclusions"]:
        names = resolve_relation_names(conn, page_id, prop)
        if names:
            parts.append(f"{prop}: {', '.join(names)}")
    props = json.loads(page["properties_json"])
    for key in ["Type", "Métier", "Structure"]:
        if props.get(key):
            parts.append(f"{key}: {props[key]}")
    parents = resolve_relation_names(conn, page_id, "Contexte de l'observation")
    if parents:
        parts.append(f"Contexte: {', '.join(parents)}")
    return "\n".join(parts)


def _split_text(text, max_chars):
    if len(text) <= max_chars:
        return [text]
    pieces = []
    while text:
        if len(text) <= max_chars:
            pieces.append(text)
            break
        cut = text.rfind("\n", 0, max_chars)
        if cut < max_chars // 2:
            cut = text.rfind(" ", 0, max_chars)
        if cut < max_chars // 2:
            cut = max_chars
        pieces.append(text[:cut].rstrip())
        text = text[cut:].lstrip()
    return pieces


def build_chunks(conn):
    pages = conn.execute(
        "SELECT id, database_key, database_name, title, properties_json FROM pages"
    ).fetchall()
    chunks = []
    for page in pages:
        page_id = page["id"]
        title = page["title"] or ""
        context = build_page_context(conn, page)
        header = f"{title}\n{context}"
        block_texts = get_page_block_texts(conn, page_id)
        body_budget = CHUNK_MAX_CHARS - len(header) - 10
        if body_budget < 100:
            body_budget = 100

        if len(block_texts) <= CHUNK_THRESHOLD:
            body = "\n".join(block_texts)
            for i, piece in enumerate(_split_text(body, body_budget)):
                text = f"{header}\n{piece}".strip()
                if text:
                    chunks.append({
                        "page_id": page_id,
                        "chunk_index": i,
                        "text": text,
                        "database_key": page["database_key"],
                    })
        else:
            current_chunk_texts = []
            current_chars = 0
            chunk_idx = 0
            for block_text in block_texts:
                if len(block_text) > body_budget:
                    if current_chunk_texts:
                        body = "\n".join(current_chunk_texts)
                        text = f"{header}\n---\n{body}".strip()
                        chunks.append({
                            "page_id": page_id,
                            "chunk_index": chunk_idx,
                            "text": text,
                            "database_key": page["database_key"],
                        })
                        chunk_idx += 1
                        current_chunk_texts = []
                        current_chars = 0
                    for piece in _split_text(block_text, body_budget):
                        text = f"{header}\n---\n{piece}".strip()
                        chunks.append({
                            "page_id": page_id,
                            "chunk_index": chunk_idx,
                            "text": text,
                            "database_key": page["database_key"],
                        })
                        chunk_idx += 1
                    continue
                current_chunk_texts.append(block_text)
                current_chars += len(block_text)
                if current_chars >= CHUNK_TARGET_CHARS:
                    body = "\n".join(current_chunk_texts)
                    text = f"{header}\n---\n{body}".strip()
                    chunks.append({
                        "page_id": page_id,
                        "chunk_index": chunk_idx,
                        "text": text,
                        "database_key": page["database_key"],
                    })
                    chunk_idx += 1
                    current_chunk_texts = []
                    current_chars = 0
            if current_chunk_texts:
                body = "\n".join(current_chunk_texts)
                text = f"{header}\n---\n{body}".strip()
                chunks.append({
                    "page_id": page_id,
                    "chunk_index": chunk_idx,
                    "text": text,
                    "database_key": page["database_key"],
                })
    return chunks


def text_hash(text):
    return hashlib.sha256(text.encode("utf-8")).hexdigest()[:16]


def embedding_to_blob(vec):
    return vec.astype(np.float32).tobytes()


# =============================================================================
# Schema
# =============================================================================

def ensure_schema(conn):
    """Create tables if they don't exist (idempotent)."""
    conn.executescript("""
        CREATE TABLE IF NOT EXISTS pages (
            id TEXT PRIMARY KEY,
            database_key TEXT NOT NULL,
            database_name TEXT NOT NULL,
            title TEXT,
            properties_json TEXT,
            url TEXT,
            created_time TEXT,
            last_edited_time TEXT
        );

        CREATE TABLE IF NOT EXISTS blocks (
            id TEXT PRIMARY KEY,
            page_id TEXT NOT NULL REFERENCES pages(id),
            type TEXT NOT NULL,
            text_content TEXT,
            position INTEGER,
            parent_block_id TEXT,
            FOREIGN KEY (page_id) REFERENCES pages(id)
        );

        CREATE TABLE IF NOT EXISTS relations (
            source_page_id TEXT NOT NULL,
            property_name TEXT NOT NULL,
            target_page_id TEXT NOT NULL,
            FOREIGN KEY (source_page_id) REFERENCES pages(id)
        );

        CREATE TABLE IF NOT EXISTS sync_meta (
            key TEXT PRIMARY KEY,
            value TEXT
        );

        CREATE VIRTUAL TABLE IF NOT EXISTS pages_fts USING fts5(
            page_id, title, properties_text
        );

        CREATE VIRTUAL TABLE IF NOT EXISTS blocks_fts USING fts5(
            block_id, text_content
        );
    """)
    # Migrate FTS tables from content-linked to standalone (if needed)
    fts_sql = conn.execute("SELECT sql FROM sqlite_master WHERE name = 'pages_fts'").fetchone()
    if fts_sql and "content='pages'" in (fts_sql[0] or ""):
        print("  Migrating FTS tables to standalone schema...")
        conn.executescript("""
            DROP TABLE IF EXISTS pages_fts;
            DROP TABLE IF EXISTS blocks_fts;
            CREATE VIRTUAL TABLE pages_fts USING fts5(page_id, title, properties_text);
            CREATE VIRTUAL TABLE blocks_fts USING fts5(block_id, text_content);
        """)
        # Repopulate pages_fts from existing data
        for page in conn.execute("SELECT id, title, properties_json FROM pages").fetchall():
            props = json.loads(page[2]) if page[2] else {}
            parts = []
            for k, v in props.items():
                if v is None:
                    continue
                if isinstance(v, list):
                    if v and all(isinstance(x, str) and len(x) == 36 for x in v):
                        continue
                    parts.append(f"{k}: {', '.join(str(x) for x in v)}")
                else:
                    parts.append(f"{k}: {v}")
            conn.execute(
                "INSERT INTO pages_fts (page_id, title, properties_text) VALUES (?, ?, ?)",
                (page[0], page[1], "\n".join(parts)),
            )
        # Repopulate blocks_fts
        for block in conn.execute("SELECT id, text_content FROM blocks WHERE text_content IS NOT NULL AND text_content != ''").fetchall():
            conn.execute(
                "INSERT INTO blocks_fts (block_id, text_content) VALUES (?, ?)",
                (block[0], block[1]),
            )
        conn.commit()
        print("  FTS migration complete.")

    # Create chunks table if it doesn't exist (new DB)
    if not conn.execute("SELECT name FROM sqlite_master WHERE type='table' AND name='chunks'").fetchone():
        conn.execute("""
            CREATE TABLE chunks (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                page_id TEXT NOT NULL,
                chunk_index INTEGER NOT NULL,
                text TEXT NOT NULL,
                text_hash TEXT NOT NULL,
                database_key TEXT NOT NULL,
                embedding BLOB,
                FOREIGN KEY (page_id) REFERENCES pages(id)
            )
        """)
        conn.execute("CREATE INDEX IF NOT EXISTS idx_chunks_hash ON chunks(text_hash)")
        conn.commit()

    # Add text_hash column if missing (upgrading from old schema)
    cols = [r[1] for r in conn.execute("PRAGMA table_info(chunks)").fetchall()]
    if "text_hash" not in cols:
        conn.execute("ALTER TABLE chunks ADD COLUMN text_hash TEXT NOT NULL DEFAULT ''")
        conn.commit()
        # Backfill hashes for existing chunks so we can reuse their embeddings
        rows = conn.execute("SELECT id, text FROM chunks WHERE text_hash = ''").fetchall()
        if rows:
            print(f"  Migrating: computing text_hash for {len(rows)} existing chunks...")
            for row in rows:
                h = hashlib.sha256(row["text"].encode("utf-8")).hexdigest()[:16]
                conn.execute("UPDATE chunks SET text_hash = ? WHERE id = ?", (h, row["id"]))
            conn.commit()
            print(f"  Done.")
    conn.commit()


# =============================================================================
# Sync phase
# =============================================================================

def sync_pages(conn, full=False):
    """Sync pages from Notion. Returns set of page IDs that changed."""
    # Load existing page timestamps
    existing = {}
    try:
        for row in conn.execute("SELECT id, last_edited_time FROM pages"):
            existing[row["id"]] = row["last_edited_time"]
    except sqlite3.OperationalError:
        pass  # Table might not exist yet

    all_notion_ids = set()
    changed_ids = set()
    stats = {"new": 0, "updated": 0, "unchanged": 0, "deleted": 0}

    for db_key, db_info in DATABASES.items():
        db_id = db_info["id"]
        db_name = db_info["name"]
        print(f"\n--- {db_name} ---")

        pages = query_database(db_id)
        print(f"  {len(pages)} pages from Notion")

        db_new = db_updated = db_unchanged = 0

        for page in pages:
            page_id = page["id"]
            all_notion_ids.add(page_id)
            last_edited = page.get("last_edited_time")
            title = extract_page_title(page)
            props = extract_page_properties(page)

            is_changed = full or page_id not in existing or existing[page_id] != last_edited

            if not is_changed:
                db_unchanged += 1
                continue

            if page_id in existing:
                db_updated += 1
            else:
                db_new += 1
            changed_ids.add(page_id)

            # Upsert page
            conn.execute(
                "INSERT OR REPLACE INTO pages (id, database_key, database_name, title, properties_json, url, created_time, last_edited_time) VALUES (?, ?, ?, ?, ?, ?, ?, ?)",
                (page_id, db_key, db_name, title,
                 json.dumps(props, ensure_ascii=False),
                 page.get("url"), page.get("created_time"), last_edited),
            )

            # Update FTS
            conn.execute("DELETE FROM pages_fts WHERE page_id = ?", (page_id,))
            props_text_parts = []
            for k, v in props.items():
                if v is None:
                    continue
                if isinstance(v, list):
                    if v and all(isinstance(x, str) and len(x) == 36 for x in v):
                        continue
                    props_text_parts.append(f"{k}: {', '.join(str(x) for x in v)}")
                else:
                    props_text_parts.append(f"{k}: {v}")
            conn.execute(
                "INSERT INTO pages_fts (page_id, title, properties_text) VALUES (?, ?, ?)",
                (page_id, title, "\n".join(props_text_parts)),
            )

            # Update relations
            conn.execute("DELETE FROM relations WHERE source_page_id = ?", (page_id,))
            for prop_name, prop_val in props.items():
                if isinstance(prop_val, list) and prop_val and all(
                    isinstance(v, str) and len(v) == 36 for v in prop_val
                ):
                    for target_id in prop_val:
                        conn.execute(
                            "INSERT INTO relations (source_page_id, property_name, target_page_id) VALUES (?, ?, ?)",
                            (page_id, prop_name, target_id),
                        )

            # Fetch blocks for changed pages
            try:
                blocks = get_block_children(page_id)
            except Exception as e:
                print(f"  Warning: failed to fetch blocks for '{title[:50]}': {e}")
                blocks = []

            # Clear old blocks and their FTS entries
            old_block_ids = [r[0] for r in conn.execute("SELECT id FROM blocks WHERE page_id = ?", (page_id,)).fetchall()]
            for bid in old_block_ids:
                conn.execute("DELETE FROM blocks_fts WHERE block_id = ?", (bid,))
            conn.execute("DELETE FROM blocks WHERE page_id = ?", (page_id,))
            for pos, block in enumerate(blocks):
                text = extract_block_text(block)
                conn.execute(
                    "INSERT INTO blocks (id, page_id, type, text_content, position, parent_block_id) VALUES (?, ?, ?, ?, ?, ?)",
                    (block["id"], page_id, block["type"], text, pos,
                     block.get("parent", {}).get("block_id")),
                )
                if text.strip():
                    conn.execute(
                        "INSERT INTO blocks_fts (block_id, text_content) VALUES (?, ?)",
                        (block["id"], text),
                    )

        print(f"  {db_new} new, {db_updated} updated, {db_unchanged} unchanged")
        stats["new"] += db_new
        stats["updated"] += db_updated
        stats["unchanged"] += db_unchanged

    # Delete pages removed from Notion
    existing_ids = set(existing.keys())
    deleted_ids = existing_ids - all_notion_ids
    if deleted_ids:
        for pid in deleted_ids:
            old_block_ids = [r[0] for r in conn.execute("SELECT id FROM blocks WHERE page_id = ?", (pid,)).fetchall()]
            for bid in old_block_ids:
                conn.execute("DELETE FROM blocks_fts WHERE block_id = ?", (bid,))
            conn.execute("DELETE FROM blocks WHERE page_id = ?", (pid,))
            conn.execute("DELETE FROM relations WHERE source_page_id = ?", (pid,))
            conn.execute("DELETE FROM chunks WHERE page_id = ?", (pid,))
            conn.execute("DELETE FROM pages_fts WHERE page_id = ?", (pid,))
            conn.execute("DELETE FROM pages WHERE id = ?", (pid,))
        stats["deleted"] = len(deleted_ids)
        print(f"\n  Deleted {len(deleted_ids)} pages removed from Notion")

    conn.commit()
    return changed_ids, stats


# =============================================================================
# Embed phase
# =============================================================================

def rebuild_and_embed(conn, changed_page_ids, full=False):
    """Rebuild chunks and embed only what changed."""
    print("\nBuilding chunks...")
    t0 = time.time()
    new_chunks = build_chunks(conn)
    print(f"  {len(new_chunks)} chunks built in {time.time() - t0:.1f}s")

    db_counts = Counter(c["database_key"] for c in new_chunks)
    for db_key, count in db_counts.most_common():
        print(f"  {db_key}: {count} chunks")

    # Load existing chunk text_hash → embedding mapping
    old_embeddings = {}  # text_hash → embedding blob
    if not full:
        try:
            for row in conn.execute("SELECT text_hash, embedding FROM chunks WHERE text_hash != '' AND embedding IS NOT NULL"):
                old_embeddings[row["text_hash"]] = row["embedding"]
        except sqlite3.OperationalError:
            pass
    print(f"  {len(old_embeddings)} existing embeddings in cache")

    # Compute hashes and figure out which chunks need embedding
    for chunk in new_chunks:
        chunk["text_hash"] = text_hash(chunk["text"])

    # For pages that didn't change, we can also reuse by hash match.
    # For pages that DID change, the chunk text might still be the same
    # (e.g. a property changed but block text didn't), so hash-match covers that.
    to_embed = []
    reused = 0
    for chunk in new_chunks:
        if chunk["text_hash"] in old_embeddings:
            chunk["embedding_blob"] = old_embeddings[chunk["text_hash"]]
            reused += 1
        else:
            to_embed.append(chunk)

    print(f"  {reused} embeddings reused, {len(to_embed)} to compute")

    # Embed new chunks
    if to_embed:
        try:
            from sentence_transformers import SentenceTransformer
        except ImportError:
            print(f"\n  sentence-transformers not installed, skipping embedding for {len(to_embed)} chunks")
            print("  Install with: pip install sentence-transformers")
            print("  (chunks will be stored without embeddings)")
            for chunk in to_embed:
                chunk["embedding_blob"] = None
            to_embed = []  # skip the embedding loop below

    if to_embed:
        print(f"\nLoading {MODEL_NAME}...")
        t1 = time.time()
        model = SentenceTransformer(MODEL_NAME)
        print(f"  Model loaded in {time.time() - t1:.1f}s")

        batch_size = 16
        print(f"Embedding {len(to_embed)} chunks (batch_size={batch_size})...")
        t2 = time.time()
        texts = [c["text"] for c in to_embed]
        all_embeddings = []

        for i in range(0, len(texts), batch_size):
            batch = texts[i : i + batch_size]
            embeddings = model.encode(batch, show_progress_bar=False)
            all_embeddings.append(embeddings)
            done = min(i + batch_size, len(texts))
            if done % 100 == 0 or done == len(texts):
                elapsed = time.time() - t2
                rate = done / elapsed if elapsed > 0 else 0
                print(f"  {done}/{len(texts)} ({rate:.1f} chunks/s)")

        all_embeddings = np.vstack(all_embeddings)
        embed_time = time.time() - t2
        print(f"  Done in {embed_time:.1f}s ({len(to_embed)/embed_time:.1f} chunks/s)")

        for i, chunk in enumerate(to_embed):
            chunk["embedding_blob"] = embedding_to_blob(all_embeddings[i])
    else:
        embed_time = 0

    # Replace chunks table contents
    print("\nStoring chunks...")
    conn.execute("DELETE FROM chunks")
    for chunk in new_chunks:
        conn.execute(
            "INSERT INTO chunks (page_id, chunk_index, text, text_hash, database_key, embedding) VALUES (?, ?, ?, ?, ?, ?)",
            (chunk["page_id"], chunk["chunk_index"], chunk["text"],
             chunk["text_hash"], chunk["database_key"], chunk["embedding_blob"]),
        )
    conn.commit()

    return len(new_chunks), len(to_embed), reused, embed_time


# =============================================================================
# Main
# =============================================================================

def main():
    parser = argparse.ArgumentParser(description="Incremental refresh of Notion research corpus")
    parser.add_argument("--db", type=Path, default=DEFAULT_DB_PATH)
    parser.add_argument("--full", action="store_true", help="Force full rebuild (ignore timestamps)")
    parser.add_argument("--sync-only", action="store_true", help="Only sync pages, skip embedding")
    args = parser.parse_args()

    if not NOTION_TOKEN:
        print("Error: NOTION_TOKEN not set in .env")
        sys.exit(1)

    args.db.parent.mkdir(parents=True, exist_ok=True)

    is_new_db = not args.db.exists()
    if is_new_db:
        args.full = True

    print(f"Refreshing research corpus → {args.db}")
    print(f"Mode: {'full rebuild' if args.full else 'incremental'}")
    print(f"Databases: {len(DATABASES)}")
    print()

    global _request_count
    _request_count = 0
    t0 = time.time()

    conn = sqlite3.connect(args.db)
    conn.row_factory = sqlite3.Row
    ensure_schema(conn)

    # Phase 1: Sync pages from Notion
    print("=" * 50)
    print("PHASE 1: SYNC")
    print("=" * 50)
    changed_ids, sync_stats = sync_pages(conn, full=args.full)
    sync_time = time.time() - t0

    print(f"\nSync: {sync_stats['new']} new, {sync_stats['updated']} updated, "
          f"{sync_stats['unchanged']} unchanged, {sync_stats['deleted']} deleted")
    print(f"  {_request_count} API requests in {sync_time:.1f}s")

    # Phase 2: Rebuild chunks and embed
    total_chunks = embedded = reused = 0
    embed_time = 0
    if not args.sync_only:
        if not changed_ids and not args.full:
            print("\nNo changes detected, skipping embedding phase.")
        else:
            print()
            print("=" * 50)
            print("PHASE 2: CHUNK + EMBED")
            print("=" * 50)
            total_chunks, embedded, reused, embed_time = rebuild_and_embed(
                conn, changed_ids, full=args.full
            )

    # Store metadata
    total_time = time.time() - t0
    total_pages = conn.execute("SELECT COUNT(*) FROM pages").fetchone()[0]
    total_blocks = conn.execute("SELECT COUNT(*) FROM blocks").fetchone()[0]
    total_chunks = conn.execute("SELECT COUNT(*) FROM chunks").fetchone()[0]

    conn.execute("INSERT OR REPLACE INTO sync_meta (key, value) VALUES (?, ?)",
                 ("last_sync", datetime.now().isoformat()))
    conn.execute("INSERT OR REPLACE INTO sync_meta (key, value) VALUES (?, ?)",
                 ("sync_duration_seconds", str(round(total_time, 1))))
    conn.execute("INSERT OR REPLACE INTO sync_meta (key, value) VALUES (?, ?)",
                 ("total_pages", str(total_pages)))
    conn.execute("INSERT OR REPLACE INTO sync_meta (key, value) VALUES (?, ?)",
                 ("total_blocks", str(total_blocks)))
    conn.execute("INSERT OR REPLACE INTO sync_meta (key, value) VALUES (?, ?)",
                 ("total_api_requests", str(_request_count)))
    conn.execute("INSERT OR REPLACE INTO sync_meta (key, value) VALUES (?, ?)",
                 ("embedding_model", MODEL_NAME))
    conn.execute("INSERT OR REPLACE INTO sync_meta (key, value) VALUES (?, ?)",
                 ("embedding_count", str(total_chunks)))
    conn.commit()
    conn.close()

    # Summary
    db_size = args.db.stat().st_size / 1024 / 1024
    print()
    print("=" * 50)
    print("REFRESH COMPLETE")
    print("=" * 50)
    print(f"Total time:     {total_time:.1f}s ({total_time/60:.1f} min)")
    print(f"API requests:   {_request_count}")
    print(f"Pages:          {total_pages} ({sync_stats['new']} new, {sync_stats['updated']} updated, {sync_stats['deleted']} deleted)")
    print(f"Blocks:         {total_blocks}")
    print(f"Chunks:         {total_chunks} ({embedded} embedded, {reused} reused)")
    if embed_time:
        print(f"Embed time:     {embed_time:.1f}s")
    print(f"DB size:        {db_size:.1f} MB")


if __name__ == "__main__":
    main()
