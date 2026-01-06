# Matometa Web Frontend Design

**Date:** 2026-01-05
**Status:** Approved

---

## Overview

Web-based chat interface for the Matometa data analytics system. Enables interactive conversations with Claude Code to query Matomo and Metabase data.

### Scope (v1)

- Two-section sidebar layout (Explorations active, Connaissances placeholder)
- Chat interface in Explorations section
- Full event streaming from Claude Code (with CSS toggle to hide tool calls)
- CLI backend (SDK stub for future compatibility)
- In-memory conversation storage
- No authentication

### Key Decisions

- **Backend:** Flask (Python) — matches existing codebase
- **Agent communication:** Spawn `claude` CLI with `--output-format stream-json`
- **Streaming:** Server-Sent Events (SSE) at event-level granularity
- **Storage:** Server-managed conversation history (HATEOAS-style API)
- **UI:** Adapted from autoplatformer design system (itou.css, Bootstrap 5, Remix Icons)
- **Abstraction:** Agent backend interface supports swapping CLI for SDK later

---

## Architecture

### File Structure

```
web/
├── app.py                    # Flask routes, SSE streaming
├── config.py                 # AGENT_BACKEND, paths
├── storage.py                # Conversation, Message, ConversationStore
├── agents/
│   ├── base.py               # AgentBackend ABC, AgentMessage
│   ├── cli.py                # CLIBackend (spawns claude CLI)
│   └── sdk.py                # SDKBackend stub
├── static/
│   ├── css/
│   │   └── style.css         # Adapted from autoplatformer
│   └── js/
│       └── chat.js           # SSE handling, event rendering, toggles
├── templates/
│   ├── base.html             # Sidebar layout
│   ├── explorations.html     # Chat interface
│   └── connaissances.html    # Placeholder
└── requirements.txt
```

### Agent Backend Abstraction

Common message format normalized from both CLI and SDK:

```python
@dataclass
class AgentMessage:
    type: str          # "assistant", "tool_use", "tool_result", "system", "error"
    content: Any       # text, tool call details, etc.
    timestamp: float
    raw: dict          # original message for debugging
```

Abstract interface:

```python
class AgentBackend(ABC):
    @abstractmethod
    async def start_conversation(self, conversation_id: str) -> str:
        """Initialize a conversation, return session_id"""
        pass

    @abstractmethod
    async def send_message(
        self,
        conversation_id: str,
        message: str,
        history: list[dict]
    ) -> AsyncIterator[AgentMessage]:
        """Send message, yield streaming responses"""
        pass

    @abstractmethod
    async def cancel(self, conversation_id: str) -> bool:
        """Cancel running task"""
        pass
```

Selection via environment variable:

```python
AGENT_BACKEND = os.getenv("AGENT_BACKEND", "cli")  # "cli" or "sdk"
```

---

## Conversation Storage

### Data Model

```python
@dataclass
class Message:
    role: str              # "user" or "assistant"
    content: str           # text content
    timestamp: datetime
    raw_events: list[dict] # full agent events for replay

@dataclass
class Conversation:
    id: str
    user_id: Optional[str]  # None for now, required when auth added
    title: Optional[str]    # auto-generated from first message
    messages: list[Message]
    session_id: Optional[str]  # agent session for resumption
    created_at: datetime
    updated_at: datetime
```

### REST API (HATEOAS-style)

```
POST /api/conversations
  → {"id": "abc123", "links": {"self": "...", "stream": "..."}}

POST /api/conversations/{id}/messages
  body: {"content": "..."}
  → {"status": "started", "links": {"stream": "...", "cancel": "..."}}

GET /api/conversations/{id}/stream
  → SSE: events until done

GET /api/conversations/{id}
  → full conversation with messages and links

POST /api/conversations/{id}/cancel
  → {"status": "cancelled"}
```

---

## Streaming Design

### Server-Sent Events

```python
@app.route('/api/conversations/<conv_id>/stream')
def stream_conversation(conv_id: str):
    def generate():
        for event in agent.send_message(...):
            yield f"event: {event.type}\n"
            yield f"data: {json.dumps(event.to_dict())}\n\n"
        yield "event: done\ndata: {}\n\n"

    return Response(generate(), mimetype='text/event-stream')
```

### Frontend Handling

```javascript
const source = new EventSource(`/api/conversations/${id}/stream`);

['assistant', 'tool_use', 'tool_result', 'system', 'error'].forEach(type => {
    source.addEventListener(type, (e) => {
        const data = JSON.parse(e.data);
        appendEvent(type, data);  // renders with class="event-{type}"
    });
});
```

### CSS Visibility Toggle

```css
.event-tool_use, .event-tool_result { display: block; }

.chat-output.hide-tools .event-tool_use,
.chat-output.hide-tools .event-tool_result {
    display: none;
}
```

---

## UI Design

Based on autoplatformer (branch `claude/redesign-menu-sections-YFY6C`):

- **Sidebar:** Two sections (Explorations, Connaissances)
- **Header:** Logo, structure dropdown
- **Main area:** Section content with header and body
- **Chat bar:** Fixed at bottom, input + send button
- **Design system:** itou.css, Bootstrap 5, Remix Icons
- **Primary color:** #000091 (French government blue)

---

## Roadmap / Possible Evolutions

| Evolution | Description |
|-----------|-------------|
| Chunk-level streaming | SDK adapter emits `content_block_delta` for character-by-character text |
| SQLite persistence | Swap `ConversationStore` implementation, add migrations |
| Conversation list | Show past conversations in Explorations sidebar |
| Google OAuth | Add `User` model, populate `user_id`, filter by user |
| Connaissances section | Browse/edit `knowledge/` and `skills/` files |
| Report generation | Save conversation outputs to `reports/` folder |
| SDK backend | Full `SDKBackend` implementation for remote deployment |

---

## References

- Vigil patterns: `~/Development/vigil/web/js/console.js`, `~/Development/vigil/web/server/agent.js`
- Autoplatformer UI: `~/Development/gip/autoplatformer` (branch `claude/redesign-menu-sections-YFY6C`)
- Original planning doc: `docs/plans/data_analytics_web_app_planning.md`
