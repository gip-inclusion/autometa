# Plan: Chat Velocity — In-Process Signal-Based SSE

**Date:** 2026-03-02
**Status:** Draft
**Complements:** `docs/audit-performance-fiabilite-2026-02-26.md` (Phase 3 — Performance web)

## Problem

On Scalingo, chat message delivery has ~500ms average latency. The SSE endpoint
polls the database every 0.5s with 3 queries per iteration (messages, conversation
status, PM liveness). With N concurrent SSE streams, this creates 6N queries/sec
of steady DB load — even when idle.

The ProcessManager and SSE handler run in the **same asyncio event loop** (via
FastAPI lifespan in `web/app.py:44-46`). This means we can replace DB polling
with `asyncio.Event` signaling for near-instant message delivery.

Additional issues found during audit:
- PM heartbeat writes to DB 2x/sec (unnecessary for 15s liveness check)
- PG connection pool maxconn=10 is tight under concurrent SSE streams
- `entrypoint.sh` starts a duplicate PM subprocess (Docker/local dev only — Scalingo
  uses the Procfile which only runs uvicorn, PM starts in-process via lifespan)

**Target:** 500ms → ~10ms message delivery latency, ~90% reduction in SSE DB load.

## Current Hot Path

```
SSE loop (every 0.5s):
  1. store.get_messages_since()     → SELECT messages       (1 query)
  2. store.get_conversation()       → SELECT conversations  (1 query)
  3. store.is_pm_alive()            → SELECT pm_heartbeat   (1 query, every 3s)
  = 6 queries/sec per active stream

PM loop (every 0.5s):
  1. store.update_pm_heartbeat()    → INSERT/UPDATE         (1 write)
  2. store.claim_pending_commands() → UPDATE...RETURNING    (1 write)
  = 4 writes/sec always
```

## Plan

### Step 1 — Create signal registry

**New file:** `web/signals.py` (~50 lines)

A `SignalRegistry` holding `{conv_id: ConversationSignal}` where each signal has:
- `message_event: asyncio.Event` — set by PM after writing a message
- `finished: bool` — set by PM after clearing `needs_response`
- PM liveness cache (`_pm_alive_at: float`) — updated by PM, read by SSE

Key methods:
| Method | Called by | DB queries |
|--------|----------|------------|
| `notify_message(conv_id)` | PM after `add_message` / `update_message` | 0 |
| `notify_finished(conv_id)` | PM after clearing `needs_response` | 0 |
| `wait_for_message(conv_id, timeout=3s)` | SSE generator | 0 |
| `is_finished(conv_id)` | SSE generator | 0 |
| `update_pm_alive()` / `is_pm_alive()` | PM heartbeat / SSE | 0 |
| `cleanup(conv_id)` | SSE on stream end | 0 |

Global singleton: `signals = SignalRegistry()`.

**Effort:** 1h

---

### Step 2 — PM notifies signals after every DB write

**File:** `web/pm.py`

In `_run_agent()` (lines 86-133):
- After `store.add_message(...)` → `signals.notify_message(conversation_id)`
- After `store.update_message(...)` → `signals.notify_message(conversation_id)`
- In `finally` after `store.update_conversation(..., needs_response=False)` → `signals.notify_finished(conversation_id)`

In `run()` main loop: call `signals.update_pm_alive()` alongside the DB heartbeat.

**Effort:** 30 min

---

### Step 3 — Replace SSE polling loop with signal-based waiting

**File:** `web/routes/conversations.py` — rewrite `generate()` in `stream_conversation`

New loop structure:
```python
while elapsed < 300s:
    signaled = await signals.wait_for_message(conv_id, timeout=3s)

    if signaled:
        # Signal fired — query DB for new messages (1 query)
        new_messages = store.get_messages_since(conv_id, last_msg_id)
        yield messages

    # Completion check: in-memory flag (0 queries)
    if signals.is_finished(conv_id):
        final sweep → yield done → return

    # Safety-net fallback: check DB every ~5s for missed signals
    if not signaled and elapsed % 5 == 0:
        new_messages = store.get_messages_since(conv_id, last_msg_id)
        yield messages
        conv = store.get_conversation(conv_id)  # check needs_response
        if conv and not conv.needs_response:
            final sweep → yield done → return

    # PM liveness: in-memory cache (0 queries)
    if not signals.is_pm_alive():
        yield error → yield done → return

    yield heartbeat  # every ~3s (matching wait timeout)
```

Query reduction:

| Scenario | Before (per 0.5s) | After |
|----------|-------------------|-------|
| Message arrives | 3 queries | 1 query (instant) |
| Waiting (idle) | 3 queries | 0 (+ 2 queries every 5s fallback) |
| QPS per stream | 6/s | ~0.4/s idle, ~0.3/s active |

**Effort:** 1.5h

---

### Step 4 — Reduce PM heartbeat to every 5s

**File:** `web/pm.py` — add counter in `run()` loop

```python
heartbeat_counter = 0
HEARTBEAT_EVERY = 10  # 10 x 0.5s = 5s

while True:
    heartbeat_counter += 1
    if heartbeat_counter >= HEARTBEAT_EVERY:
        await asyncio.to_thread(store.update_pm_heartbeat)
        signals.update_pm_alive()
        heartbeat_counter = 0
    ...
```

Adjust `is_pm_alive(max_age_seconds=30)` in `web/database.py:601`.

**Effort:** 15 min

---

### Step 5 — Increase PG connection pool

**File:** `web/db.py:29-31`

```python
_pg_pool = ThreadedConnectionPool(minconn=2, maxconn=20, dsn=...)
```

**Effort:** 5 min

---

## Why NOT multiple uvicorn workers

In-process signaling requires PM and SSE to share the same process. A single
async worker can handle hundreds of SSE connections because generators spend
99% of time awaiting `asyncio.Event` (zero CPU). DB queries are offloaded via
`asyncio.to_thread`.

If horizontal scaling becomes necessary: PostgreSQL LISTEN/NOTIFY for cross-process
signaling (see `docs/plans/2026-01-11-pubsub-streaming.md`).

## Housekeeping — Fix entrypoint PM duplication (Docker only)

**File:** `entrypoint.sh`

Not a Scalingo issue (Procfile is used in production), but `entrypoint.sh` starts
a duplicate PM subprocess (`python -m web.pm &`) alongside the lifespan PM.
Remove it for Docker/local dev consistency:

```bash
#!/bin/sh
exec uvicorn web.app:app --host 0.0.0.0 --port "${WEB_PORT:-5000}"
```

**Effort:** 5 min

---

## Summary

| # | Change | File(s) | Effort | Impact |
|---|--------|---------|--------|--------|
| 1 | Signal registry | `web/signals.py` (new) | 1h | Core signaling infra |
| 2 | PM notifies signals | `web/pm.py` | 30 min | PM → SSE instant notify |
| 3 | Signal-based SSE | `web/routes/conversations.py` | 1.5h | 500ms → ~10ms delivery |
| 4 | Heartbeat 5s | `web/pm.py`, `web/database.py` | 15 min | -90% heartbeat writes |
| 5 | PG pool maxconn=20 | `web/db.py` | 5 min | Connection headroom |
| — | Fix entrypoint (Docker) | `entrypoint.sh` | 5 min | Docker dev consistency |
| **Total** | | | **~3.5h** | **~97% latency reduction** |

## Verification

1. Send a message, verify SSE delivers assistant chunks within ~50ms
2. Kill the PM task, verify SSE detects it via liveness cache and falls back
3. Disable signals, verify 5s fallback poll still detects completion
4. Open 5 concurrent conversations, verify PG pool doesn't exhaust
