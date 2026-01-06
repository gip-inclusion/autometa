# Unified Conversations and Reports

**Date:** 2026-01-06
**Status:** Approved

## Summary

Merge conversations and reports into a unified data model. Simplify the sidebar to show only section links. Display conversations and reports in a grid/list view. Enable continuing conversations after reports are generated.

## Goals

1. Clean data model with normalized messages
2. Simplified sidebar (no nested lists)
3. Reports as part of conversations, not separate entities
4. Ability to chat about reports after they're generated
5. htmx for navigation, vanilla JS for SSE streaming

## Data Model

### conversations

| Column | Type | Notes |
|--------|------|-------|
| id | UUID | PK |
| user_id | TEXT | Nullable for now, required later |
| title | TEXT | LLM-generated or null |
| session_id | TEXT | Agent SDK session for resumption |
| created_at | DATETIME | |
| updated_at | DATETIME | |

### messages

| Column | Type | Notes |
|--------|------|-------|
| id | INTEGER | PK, auto-increment |
| conversation_id | UUID | FK → conversations |
| type | TEXT | user, assistant, tool_use, tool_result |
| content | TEXT | Message content (JSON for tool types) |
| created_at | DATETIME | |

### reports

| Column | Type | Notes |
|--------|------|-------|
| id | INTEGER | PK, auto-increment |
| conversation_id | UUID | FK → conversations |
| message_id | INTEGER | FK → messages (where report appears) |
| title | TEXT | Report title |
| website | TEXT | emplois, dora, etc. |
| category | TEXT | Query category |
| tags | TEXT | JSON array |
| original_query | TEXT | User's original question |
| version | INTEGER | Default 1, increments on update |
| created_at | DATETIME | |
| updated_at | DATETIME | |

## Navigation & UX

### Sidebar (simplified)

- Logo/brand at top
- Two menu items only: **Explorations** and **Connaissances**
- No nested lists, no conversation/report sublists

### Explorations page (list view)

- Grid or list of past conversations, sorted by `updated_at` desc
- Each card shows: title, date, badge if has report
- Click → opens conversation detail view
- Bottom: persistent chat bar
- Typing in chat bar creates new conversation automatically

### Conversation detail view

- Shows message history (filterable by view mode toggle)
- Report rendered inline at its message position
- Chat bar at bottom to continue conversation
- Back button to return to list

### Report rendering

- Report content (markdown) rendered as HTML
- Report metadata (title, website, tags) shown in header
- User can ask follow-up questions below it

## API Endpoints

### Conversations

```
GET  /api/conversations          List conversations (with report flag)
POST /api/conversations          Create new conversation
GET  /api/conversations/<id>     Get conversation with messages
DELETE /api/conversations/<id>   Delete conversation
```

### Messages

```
POST /api/conversations/<id>/messages   Send message
GET  /api/conversations/<id>/stream     SSE stream for agent response
```

Messages stored individually as they arrive.

### Reports

```
GET /api/reports        List all reports (for search/filter)
GET /api/reports/<id>   Get report with rendered content
```

Reports created automatically when agent produces one (detected via YAML front-matter).

## htmx Integration

### Page structure

- Flask serves full HTML pages (Jinja templates)
- htmx handles partial updates without full page reloads

### Key interactions

| Action | htmx approach |
|--------|---------------|
| Load conversation list | `hx-get="/explorations/list"` returns partial |
| Click conversation | `hx-get="/explorations/<id>"` swaps main content |
| Send message | `hx-post` to create message, SSE for streaming |
| Back to list | `hx-get="/explorations/list"` or browser back |

### Templates

```
explorations.html           Full page wrapper
_conversation_list.html     Partial: grid/list of conversations
_conversation_detail.html   Partial: message history + chat
_message.html               Partial: single message block
```

### SSE streaming

Keep vanilla JS for SSE (already working). htmx for navigation only.

## Migration

1. Create new schema (conversations, messages, reports tables)
2. Migrate existing SQLite conversations to new schema
3. Import existing `./reports/*.md` files:
   - Create conversation for each report
   - Parse YAML front-matter for metadata
   - Store markdown content as assistant message
   - Create report record linked to message
4. Keep files temporarily for backup
5. Remove files once migration confirmed

## Implementation Order

1. Database schema migration
2. Update storage layer (Python)
3. Simplify sidebar template
4. Create list view template and endpoint
5. Update conversation detail view
6. Add htmx navigation
7. Migrate existing reports
8. Remove old report file handling

## Out of Scope

- User authentication (user_id stays nullable)
- Report search/filter UI (API ready, UI later)
- Report versioning UI (field exists, UI later)
