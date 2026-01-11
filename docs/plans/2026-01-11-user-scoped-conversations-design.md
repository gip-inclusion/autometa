# User-Scoped Conversations Design

Date: 2026-01-11

## Overview

Conversations become user-scoped (private per user), with a redesigned sidebar showing recent conversations inline. Reports remain shared.

## 1. User Identity Resolution

**Config:**
- Add `DEFAULT_USER` to `.env` (e.g., `admin@localhost` locally, `matometa@inclusion.gouv.fr` on remote)

**Resolution in `web/app.py`:**
```python
@app.before_request
def set_user_identity():
    g.user_email = (
        request.headers.get("X-Forwarded-Email")
        or config.DEFAULT_USER
        or "admin@localhost"
    )
```

- OAuth proxy provides `X-Forwarded-Email` header on remote
- Falls back to `DEFAULT_USER` on localhost (no proxy)

## 2. URL Structure

| URL | Purpose |
|-----|---------|
| `/explorations` | Full conversation list (grid view) |
| `/explorations/new` | Empty chat, focused input, no conversation created yet |
| `/explorations/<uuid>` | View/continue specific conversation |

**Redirect for compatibility:**
```python
if conv_id := request.args.get("conv"):
    return redirect(f"/explorations/{conv_id}", code=301)
```

## 3. Sidebar Layout

```
┌─────────────────────────┐
│ Nouvelle conversation   │  → /explorations/new
├─────────────────────────┤
│ Rapports                │  → /rapports
│ Connaissances           │  → /connaissances
├─────────────────────────┤
│ ┌─────────────────────┐ │
│ │ Analyse trafic...   │ │  Recent conversations
│ │ Comparaison déc...  │ │  (no icons, smaller text)
│ │ Candidats Q4 2025   │ │  Scrollable, max 15 items
│ │ ...                 │ │
│ └─────────────────────┘ │
│ Voir plus...            │  → /explorations
└─────────────────────────┘
```

- Conversations filtered by current user only
- Active conversation highlighted when viewing `/explorations/<uuid>`

## 4. Deferred Conversation Creation

At `/explorations/new`:
1. Render empty chat UI with no `conversation_id`
2. Input focused, ready to type
3. On first message send:
   - `POST /api/conversations` → creates conversation, returns `id`
   - `POST /api/conversations/<id>/messages` → sends message
   - Update URL to `/explorations/<id>` via `history.replaceState`

## 5. Migration Script

**Script:** `scripts/migrate_conversation_authors.py`

```python
import os
import sqlite3

DB_PATH = os.getenv("DB_PATH", "data/matometa.db")
DEFAULT_USER = os.getenv("DEFAULT_USER", "admin@localhost")

def migrate():
    conn = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()

    cursor.execute("""
        UPDATE conversations
        SET user_id = ?
        WHERE user_id IS NULL OR user_id = ''
    """, (DEFAULT_USER,))

    updated = cursor.rowcount
    conn.commit()
    conn.close()

    print(f"Updated {updated} conversations with user_id = {DEFAULT_USER}")

if __name__ == "__main__":
    migrate()
```

**Execution:**
```bash
# Local
DEFAULT_USER=admin@localhost python scripts/migrate_conversation_authors.py

# Remote
ssh matometa@ljt.cc "cd /srv/matometa && DEFAULT_USER=matometa@inclusion.gouv.fr python scripts/migrate_conversation_authors.py"
```

## 6. User Filtering in Database Layer

**`list_conversations()`:**
```python
def list_conversations(self, limit=20, user_id=None, conv_type=None):
    query = "SELECT * FROM conversations WHERE 1=1"
    params = []

    if user_id:
        query += " AND user_id = ?"
        params.append(user_id)
    # ...
```

**`get_conversation()`:**
- Add optional `user_id` parameter
- Return None (or 403) if user doesn't match

**Reports remain unfiltered** — shared across all users.

## 7. Files to Change

| File | Changes |
|------|---------|
| `.env` / `.env.example` | Add `DEFAULT_USER` |
| `web/config.py` | Load `DEFAULT_USER` |
| `web/app.py` | Set `g.user_email` in `before_request` |
| `web/database.py` | Add `user_id` filtering to `list_conversations`, `get_conversation` |
| `web/routes/html.py` | New routes, redirect, sidebar data |
| `web/routes/conversations.py` | Pass `g.user_email` to store methods |
| `web/templates/base.html` | New sidebar layout |
| `web/templates/explorations.html` | Handle "new" mode |
| `web/static/js/chat.js` | Deferred conversation creation, URL update |

**New file:**
- `scripts/migrate_conversation_authors.py`
