# Connaissances Feature

**Date:** 2026-01-07
**Status:** Approved

## Summary

Add a "Connaissances" section to browse, view, and edit knowledge files through AI-assisted conversations. Changes are staged in a draft directory until explicitly committed.

## Goals

1. Browse knowledge files in a card grid (like explorations)
2. View rendered markdown content
3. Edit files via conversation with Claude
4. Stage changes in draft directory until commit
5. Explicit commit/abandon workflow with journal logging

## Security

### Path Hardening

The `?file=` parameter is a potential extraction vector. Multiple layers of defense:

```python
KNOWLEDGE_ROOT = (config.BASE_DIR / "knowledge").resolve()
ALLOWED_EXTENSIONS = {".md"}

def validate_knowledge_path(file_param: str) -> Path | None:
    """Validate and resolve a knowledge file path."""
    if not file_param:
        return None

    # Reject obvious attacks early
    if ".." in file_param or file_param.startswith("/"):
        return None

    # Only allow simple alphanumeric + hyphen/underscore + slash
    if not re.match(r'^[a-zA-Z0-9_\-/]+\.md$', file_param):
        return None

    # Resolve full path
    candidate = (KNOWLEDGE_ROOT / file_param).resolve()

    # CRITICAL: ensure it's inside knowledge/
    try:
        candidate.relative_to(KNOWLEDGE_ROOT)
    except ValueError:
        return None

    if not candidate.is_file():
        return None

    if candidate.suffix.lower() not in ALLOWED_EXTENSIONS:
        return None

    return candidate
```

## Page Layout

### List View (`/connaissances`)

- Cards grouped by category (Sites, Matomo, Metabase, Stats)
- Each category is a collapsible section
- Card shows: filename (humanized), last modified date
- Badge if file has active editing conversation
- Click card → file detail view

### File Detail View (`/connaissances?file=sites/emplois.md`)

- Back arrow to return to list
- Header: file name + path
- Content: rendered markdown (same styling as reports)
- Chat bar at bottom for editing conversations
- Modified files panel (when changes exist)

### URL Structure

- `/connaissances` → list view
- `/connaissances?file=sites/emplois.md` → file detail view
- `/connaissances?file=sites/emplois.md&conv=<uuid>` → file with conversation

## Staged Editing Workflow

### Directory Structure

```
knowledge-drafts/
  <conv-id>/
    sites/emplois.md    # modified copy
    matomo/funnels.md   # another edit
```

### Agent Context

When sending to agent, inject:

```
You are editing knowledge files.

IMPORTANT: Write changes to the staging directory:
  knowledge-drafts/<conv-id>/

The original file is at: knowledge/sites/emplois.md
Your working copy is at: knowledge-drafts/<conv-id>/sites/emplois.md

Current content:
---
<file content>
---

User request: <message>
```

### Modified Files Panel

Visible when conversation has staged changes:

```
┌─────────────────────────────────┐
│ Fichiers modifiés (2)           │
├─────────────────────────────────┤
│ ● sites/emplois.md              │
│ ● matomo/funnels.md             │
├─────────────────────────────────┤
│ [Valider]  [Abandonner]         │
└─────────────────────────────────┘
```

### Commit Flow

1. User clicks "Valider"
2. Copy staged files from `knowledge-drafts/<conv-id>/` to `knowledge/`
3. Append to JOURNAL.md:
   ```
   ## 2026-01-07 - Knowledge Update

   Files modified:
   - sites/emplois.md
   - matomo/funnels.md

   Summary: <brief description from conversation>
   ```
4. Delete staging directory
5. Mark conversation as committed/closed

### Abandon Flow

1. User clicks "Abandonner"
2. Confirm dialog: "Abandonner les modifications ?"
3. Delete staging directory
4. Delete conversation

### Pending Changes

- No auto-cleanup on navigation
- User must explicitly commit or abandon
- Conversations with pending changes shown with badge in list view
- Panel persists across page reloads

## Data Model

### conversations table changes

Add columns:
- `type TEXT DEFAULT 'exploration'` - 'exploration' or 'knowledge'
- `file_path TEXT` - for knowledge conversations, the primary file being edited
- `status TEXT DEFAULT 'active'` - 'active', 'committed', 'abandoned'

### Queries

Find active knowledge conversation for a file:
```sql
SELECT * FROM conversations
WHERE type = 'knowledge'
  AND file_path = ?
  AND status = 'active'
ORDER BY updated_at DESC
LIMIT 1
```

List files with active conversations:
```sql
SELECT file_path FROM conversations
WHERE type = 'knowledge' AND status = 'active'
```

## API Endpoints

### Knowledge Files

```
GET /api/knowledge                    List all knowledge files
GET /api/knowledge/<path:file>        Get file content
```

### Knowledge Conversations

```
POST /api/knowledge/<path:file>/conversation    Start/resume conversation
POST /api/knowledge/conversations/<id>/commit   Commit changes
POST /api/knowledge/conversations/<id>/abandon  Abandon changes
GET  /api/knowledge/conversations/<id>/files    List modified files
```

## Implementation Order

1. Add path validation utility
2. Add database columns (type, file_path, status)
3. Create knowledge file listing API
4. Update connaissances.html template (list view)
5. Add file detail view
6. Add knowledge conversation endpoints
7. Create staging directory logic
8. Add modified files panel UI
9. Implement commit/abandon flows
10. Add JOURNAL.md appending

## Out of Scope

- Diff view (can add later)
- Multiple files in same conversation (focus on primary file)
- Git integration (files just saved to disk)
