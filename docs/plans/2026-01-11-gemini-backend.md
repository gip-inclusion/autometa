# Plan: Add Google ADK as Third Agent Backend

## Goal
Add Google ADK (Agent Development Kit) as a third option alongside Claude CLI and SDK backends, enabling Gemini-powered agents with the same web UI and tool ecosystem.

## Architecture Overview

The existing system has a clean abstraction:
```
AgentBackend (abstract base class)
├── CLIBackend  → spawns `claude` CLI process
├── SDKBackend  → uses claude-agent-sdk Python package
└── ADKBackend  → NEW: uses google-adk Python package
```

All backends yield `AgentMessage` objects, streamed to the frontend via SSE.

## Design Decisions

1. **Tool approach: Hybrid**
   - Expose MatomoAPI/MetabaseAPI methods as direct function tools (for common queries)
   - Also provide code execution tool for advanced/custom Python scripts
   - System prompt (AGENTS.md) guides when to use each

2. **Model configuration: Environment variable only**
   - `ADK_MODEL` env var (default: `gemini-2.5-pro`)
   - No UI changes needed

---

## Implementation Steps

### Step 1: Add google-adk dependency

**File:** `requirements.txt`

Add:
```
google-adk>=0.2.0
```

### Step 2: Add ADK environment variables

**File:** `.env.example` (and `.env`)

```
GOOGLE_GENAI_API_KEY=...
ADK_MODEL=gemini-2.5-pro
```

**File:** `docker-compose.yml`

Add to environment section:
```yaml
- GOOGLE_GENAI_API_KEY=${GOOGLE_GENAI_API_KEY}
- ADK_MODEL=${ADK_MODEL:-gemini-2.5-pro}
```

### Step 3: Create ADK backend implementation

**File:** `web/agents/adk.py` (new file)

```python
"""Google ADK backend for Matometa agents."""

import asyncio
import os
from typing import AsyncIterator, Optional

from google.adk import Agent, Runner
from google.adk.tools import FunctionTool
from google.genai import types

from .base import AgentBackend, AgentMessage
from web import config

class ADKBackend(AgentBackend):
    """Agent backend using Google ADK with Gemini models."""

    def __init__(self):
        self._running_tasks: dict[str, asyncio.Task] = {}
        self._cancelled: set[str] = set()

    async def send_message(
        self,
        conversation_id: str,
        prompt: str,
        system_prompt: str,
        session_id: Optional[str] = None,
    ) -> AsyncIterator[AgentMessage]:
        # Create agent with tools
        agent = self._create_agent(system_prompt)
        runner = Runner(agent=agent, app_name="matometa")

        # Run and stream responses
        async for event in runner.run_async(user_id=conversation_id, user_message=prompt):
            # Convert ADK events to AgentMessage format
            yield self._convert_event(event)

    def _create_agent(self, system_prompt: str) -> Agent:
        """Create ADK agent with Matomo/Metabase tools."""
        tools = self._build_tools()

        return Agent(
            name="matometa",
            model=os.getenv("ADK_MODEL", "gemini-2.5-pro"),
            instruction=system_prompt,
            tools=tools,
        )

    def _build_tools(self) -> list[FunctionTool]:
        """Build function tools from MatomoAPI and MetabaseAPI."""
        # Import API clients
        from skills.matomo_query.scripts.matomo import MatomoAPI
        from skills.metabase_query.scripts.metabase import MetabaseAPI

        matomo = MatomoAPI()
        metabase = MetabaseAPI()

        # Wrap methods as FunctionTools
        tools = [
            FunctionTool(func=matomo.get_visits, name="matomo_get_visits"),
            FunctionTool(func=matomo.get_dimension, name="matomo_get_dimension"),
            FunctionTool(func=matomo.get_event_categories, name="matomo_get_event_categories"),
            # ... more methods
            FunctionTool(func=metabase.execute_sql, name="metabase_execute_sql"),
            FunctionTool(func=metabase.execute_card, name="metabase_execute_card"),
            # ... more methods
        ]
        return tools

    def _convert_event(self, event) -> AgentMessage:
        """Convert ADK event to AgentMessage."""
        # Map ADK event types to our message types
        # (assistant, tool_use, tool_result, system, error)
        ...

    async def cancel(self, conversation_id: str) -> bool:
        ...

    def is_running(self, conversation_id: str) -> bool:
        ...
```

### Step 4: Register ADK backend in factory

**File:** `web/agents/__init__.py`

```python
from .cli import CLIBackend
from .sdk import SDKBackend
from .adk import ADKBackend  # NEW

def get_agent() -> AgentBackend:
    backend = os.getenv("AGENT_BACKEND", "cli").lower()

    if backend == "cli":
        return CLIBackend()
    elif backend == "sdk":
        return SDKBackend()
    elif backend == "adk":
        return ADKBackend()  # NEW
    else:
        raise ValueError(f"Unknown backend: {backend}")
```

### Step 5: Add ADK config constants

**File:** `web/config.py`

```python
# ADK settings
ADK_MODEL = os.getenv("ADK_MODEL", "gemini-2.5-pro")
ADK_AVAILABLE = bool(os.getenv("GOOGLE_GENAI_API_KEY"))
```

### Step 6: Update Dockerfile (if needed)

The Dockerfile may need no changes if google-adk installs cleanly. Verify during testing.

### Step 7: Create hybrid tool registry

**File:** `web/agents/adk_tools.py` (new file)

The hybrid approach provides:
1. **Direct function tools** for common Matomo/Metabase queries (fast, type-safe)
2. **Code execution tool** for advanced scripts (flexible, like Claude's Bash)

```python
"""Hybrid tool registry for Google ADK integration."""

import subprocess
import tempfile
from pathlib import Path
from google.adk.tools import FunctionTool
from skills.matomo_query.scripts.matomo import MatomoAPI
from skills.metabase_query.scripts.metabase import MetabaseAPI

# ============ DIRECT API TOOLS ============

def build_matomo_tools() -> list[FunctionTool]:
    """Build FunctionTools from MatomoAPI methods."""
    api = MatomoAPI()

    methods = [
        ("get_visits", "Get visit summary (nb_visits, nb_uniq_visitors, etc.) for a site. Args: site_id, period, date, segment (optional)"),
        ("get_dimension", "Get breakdown by custom dimension. Args: site_id, dimension_id, period, date, segment, limit"),
        ("get_event_categories", "List event categories. Args: site_id, period, date, segment"),
        ("get_event_actions", "List event actions in a category. Args: site_id, category, period, date"),
        ("get_entry_pages", "Get entry page statistics. Args: site_id, period, date, segment, limit"),
        ("get_page_urls", "Get page view statistics. Args: site_id, period, date, segment, limit"),
        ("get_referrers", "Get traffic referrer breakdown. Args: site_id, period, date"),
        ("get_goals", "Get goal definitions for a site. Args: site_id"),
        ("request", "Make raw Matomo API request. Args: method, **params"),
    ]

    return [
        FunctionTool(func=getattr(api, name), name=f"matomo_{name}", description=desc)
        for name, desc in methods
    ]

def build_metabase_tools() -> list[FunctionTool]:
    """Build FunctionTools from MetabaseAPI methods."""
    api = MetabaseAPI()

    methods = [
        ("execute_sql", "Execute native SQL query. Args: sql, timeout"),
        ("execute_card", "Execute a saved Metabase card. Args: card_id"),
        ("search_cards", "Search for saved cards by name. Args: query"),
    ]

    return [
        FunctionTool(func=getattr(api, name), name=f"metabase_{name}", description=desc)
        for name, desc in methods
    ]

# ============ CODE EXECUTION TOOL ============

def execute_python(code: str, timeout: int = 60) -> dict:
    """
    Execute Python code in a subprocess.

    Use this for advanced queries that require:
    - Multiple API calls with logic
    - Data transformation
    - Custom calculations

    The code has access to MatomoAPI and MetabaseAPI via:
        from skills.matomo_query.scripts.matomo import MatomoAPI
        from skills.metabase_query.scripts.metabase import MetabaseAPI

    Args:
        code: Python code to execute
        timeout: Max execution time in seconds

    Returns:
        {"stdout": str, "stderr": str, "returncode": int}
    """
    with tempfile.NamedTemporaryFile(mode='w', suffix='.py', delete=False) as f:
        f.write(code)
        script_path = f.name

    try:
        result = subprocess.run(
            ['python', script_path],
            capture_output=True,
            text=True,
            timeout=timeout,
            cwd=str(Path(__file__).parent.parent.parent),  # Project root
        )
        return {
            "stdout": result.stdout,
            "stderr": result.stderr,
            "returncode": result.returncode,
        }
    except subprocess.TimeoutExpired:
        return {"stdout": "", "stderr": f"Timeout after {timeout}s", "returncode": -1}
    finally:
        Path(script_path).unlink(missing_ok=True)

# ============ FILE TOOLS ============

def read_file(path: str) -> str:
    """Read a file from the knowledge base or project. Args: path (relative to project root)"""
    base = Path(__file__).parent.parent.parent
    full_path = base / path
    if not full_path.exists():
        return f"Error: File not found: {path}"
    return full_path.read_text()

def list_files(directory: str = "knowledge") -> list[str]:
    """List files in a directory. Args: directory (relative to project root)"""
    base = Path(__file__).parent.parent.parent
    dir_path = base / directory
    if not dir_path.is_dir():
        return [f"Error: Not a directory: {directory}"]
    return [str(p.relative_to(base)) for p in dir_path.rglob("*") if p.is_file()]

# ============ REGISTRY ============

def get_all_tools() -> list[FunctionTool]:
    """Get all available tools for ADK agent."""
    return (
        build_matomo_tools() +
        build_metabase_tools() +
        [
            FunctionTool(func=execute_python, name="execute_python", description=execute_python.__doc__),
            FunctionTool(func=read_file, name="read_file", description=read_file.__doc__),
            FunctionTool(func=list_files, name="list_files", description=list_files.__doc__),
        ]
    )
```

---

## Event Mapping

ADK events need to be converted to our `AgentMessage` format:

| ADK Event | AgentMessage Type |
|-----------|-------------------|
| `TextContent` | `assistant` |
| `FunctionCall` | `tool_use` |
| `FunctionResponse` | `tool_result` |
| Agent initialization | `system` |
| Exception/error | `error` |
| Run complete | `done` |

---

## Files to Create/Modify

| File | Action |
|------|--------|
| `requirements.txt` | Add `google-adk>=0.2.0` |
| `.env.example` | Add `GOOGLE_GENAI_API_KEY`, `ADK_MODEL` |
| `docker-compose.yml` | Add env vars to environment section |
| `web/agents/adk.py` | **Create** - main ADK backend class |
| `web/agents/adk_tools.py` | **Create** - hybrid tool registry |
| `web/agents/__init__.py` | Register ADK backend in `get_agent()` |
| `web/config.py` | Add `ADK_MODEL`, `ADK_AVAILABLE` |

---

## Verification Plan

1. **Local test without Docker**:
   ```bash
   # Set up
   export GOOGLE_GENAI_API_KEY=...
   export AGENT_BACKEND=adk

   # Run web server
   .venv/bin/python -m web.app

   # Test in browser
   # Query: "Combien de visites sur Emplois en décembre 2024?"
   ```

2. **Verify streaming**:
   - Open browser dev tools → Network → EventSource
   - Check events flow: `system` → `assistant` → `tool_use` → `tool_result` → `assistant`

3. **Verify tool calls**:
   - Check `matomo_get_visits` is called with correct args
   - Check `execute_python` works for advanced queries

4. **Docker test**:
   ```bash
   docker compose build
   AGENT_BACKEND=adk docker compose up
   ```

---

## Implementation Notes

### Session Management
- ADK has its own session via `Runner(session_id=...)`
- Store ADK session ID in database like SDK does
- Resume via `runner.run_async(session_id=stored_id)`

### Streaming
- ADK streams via async iterator (`async for event in runner.run_async()`)
- Events include: `TextContent`, `FunctionCall`, `FunctionResponse`
- Map to our `AgentMessage` types in `_convert_event()`

### Error Handling
- Wrap ADK exceptions in try/except
- Yield `AgentMessage(type="error", content=str(e))`
- Log full traceback for debugging

### AGENTS.md Adaptation
- Works as system prompt for Gemini too
- May need minor tweaks for tool naming differences (e.g., `matomo_get_visits` vs `Skill(matomo_query)`)
- Consider adding a section: "When using ADK backend, tools are called directly..."
