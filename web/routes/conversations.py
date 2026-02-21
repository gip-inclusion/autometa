"""Conversation API routes."""

import asyncio
import json
import logging
import threading

from fastapi import APIRouter, Depends, Request, UploadFile
from fastapi.responses import JSONResponse, Response, StreamingResponse

from ..deps import get_current_user
from ..storage import store
from ..agents import get_agent
from .. import config
from .. import llm
from ..config import ADMIN_USERS
from ..uploads import (
    upload_file as do_upload_file,
    copy_file_for_modification,
    get_file_content,
    format_file_for_context,
    FileTooLargeError,
    BlockedFileTypeError,
    AVScanFailedError,
)
from lib.tool_taxonomy import classify_tool
from lib.api_signals import parse_api_signals

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/api/conversations")

# Global agent instance
_agent = None


def get_agent_instance():
    """Get or create the agent backend instance."""
    global _agent
    if _agent is None:
        _agent = get_agent()
    return _agent


def generate_conversation_title(user_message: str, conv_id: str) -> None:
    """Generate a smart title for a conversation (async, in background)."""
    def _generate():
        try:
            model = config.OLLAMA_TITLE_MODEL if config.LLM_BACKEND in ("ollama", "cli-ollama") else config.CLAUDE_MODEL
            prompt = (
                "Ecris un resume concis EN FRANCAIS (max 10 mots, sans guillemets) "
                f"de cette demande:\n\n{user_message[:500]}"
            )
            title = llm.generate_text(prompt, model=model, max_tokens=50).strip()[:100]
            if title:
                store.update_conversation(conv_id, title=title)
        except Exception as exc:
            logger.warning(f"Failed to generate title: {exc}")

    threading.Thread(target=_generate, daemon=True).start()


def generate_conversation_tags(user_message: str, conv_id: str) -> None:
    """Auto-tag a conversation (async, in background).

    Uses the configured LLM backend to analyze the first user message and
    assign relevant tags from the predefined taxonomy.
    Runs in a background thread.
    """
    # Tag taxonomy (must match database _seed_tags)
    TAG_TAXONOMY = """
## Produits (choisir 1 seul, obligatoire)
- emplois: Les Emplois de l'inclusion
- dora: Dora (annuaire de services)
- marche: Le Marché de l'inclusion
- communaute: La Communauté de l'inclusion
- pilotage: Pilotage de l'inclusion
- plateforme: inclusion.gouv.fr (site vitrine)
- rdv-insertion: RDV-Insertion
- mon-recap: Mon Récap
- multi: Multi-produits (concerne plusieurs produits)

## Thèmes - Acteurs (0 à 2)
- candidats: Candidats / demandeurs d'emploi
- prescripteurs: Prescripteurs
- employeurs: Employeurs / SIAE
- structures: Structures / SIAE (angle organisation)
- acheteurs: Acheteurs (Marché)
- fournisseurs: Fournisseurs (Marché)

## Thèmes - Concepts métier (0 à 2)
- iae: IAE en général
- orientation: Orientation
- depot-de-besoin: Dépôt de besoin (Marché)
- demande-de-devis: Demande de devis (Marché)
- commandes: Commandes (Mon Récap)

## Thèmes - Métriques (0 à 2)
- trafic: Analyse de trafic
- conversions: Conversions / funnel
- retention: Rétention / fidélisation
- geographique: Analyse géographique

## Type de demande (choisir 1 seul, obligatoire)
- extraction: Extraction de données brutes
- analyse: Analyse / rapport
- appli: Application interactive
- meta: Question sur Matometa lui-même
"""

    VALID_TAGS = {
        "emplois", "dora", "marche", "communaute", "pilotage",
        "plateforme", "rdv-insertion", "mon-recap", "multi",
        "matomo", "stats", "datalake",
        "candidats", "prescripteurs", "employeurs", "structures",
        "acheteurs", "fournisseurs",
        "iae", "orientation", "depot-de-besoin", "demande-de-devis", "commandes",
        "trafic", "conversions", "retention", "geographique",
        "extraction", "analyse", "appli", "meta",
    }

    prompt = f"""Analyse cette demande utilisateur et attribue des tags parmi la taxonomie suivante.

{TAG_TAXONOMY}

Règles:
- OBLIGATOIRE: exactement 1 tag produit
- OBLIGATOIRE: exactement 1 tag type_demande
- OPTIONNEL: 0 à 2 tags thème (acteurs, concepts, métriques)
- Si la demande mentionne plusieurs produits, utilise "multi"
- Si c'est une question sur l'outil Matometa, utilise "meta"

Demande: {user_message[:1000]}

Réponds UNIQUEMENT avec les noms des tags séparés par des virgules, rien d'autre.
Exemple: emplois, candidats, trafic, analyse"""

    def _parse_tags(response: str) -> list[str]:
        """Extract valid tag names from response."""
        # Handle potential explanation text - take just the tag line
        if "\n" in response:
            for line in response.split("\n"):
                if "," in line and not line.startswith("#"):
                    response = line
                    break

        tag_names = []
        for part in response.replace("\n", ",").split(","):
            tag = part.strip().lower().strip(".-*")
            if tag in VALID_TAGS:
                tag_names.append(tag)
        return tag_names

    def _generate():
        """Generate tags using the configured LLM backend."""
        try:
            model = config.OLLAMA_TAG_MODEL if config.LLM_BACKEND in ("ollama", "cli-ollama") else config.CLAUDE_MODEL
            response = llm.generate_text(prompt, model=model, max_tokens=100)
            tag_names = _parse_tags(response)
            if tag_names:
                store.set_conversation_tags(conv_id, tag_names)
                logger.info(f"Auto-tagged conversation {conv_id}: {tag_names}")
        except Exception as exc:
            logger.warning(f"Failed to generate tags: {exc}")

    threading.Thread(target=_generate, daemon=True).start()


@router.post("")
def create_conversation(user_email: str = Depends(get_current_user)):
    """Create a new conversation."""
    conv = store.create_conversation(user_id=user_email)
    return {
        "id": conv.id,
        "links": {
            "self": f"/api/conversations/{conv.id}",
            "messages": f"/api/conversations/{conv.id}/messages",
            "stream": f"/api/conversations/{conv.id}/stream",
        },
    }


@router.get("")
def list_conversations(user_email: str = Depends(get_current_user), limit: int = 20):
    """List recent conversations."""
    convs = store.list_conversations(limit=limit, user_id=user_email)
    agent = get_agent_instance()
    return {
        "conversations": [
            {
                "id": c.id,
                "title": c.title,
                "has_report": c.has_report,
                "is_running": agent.is_running(c.id),
                "updated_at": c.updated_at.isoformat(),
                "links": {"self": f"/api/conversations/{c.id}"},
            }
            for c in convs
        ]
    }


@router.get("/{conv_id}")
def get_conversation(conv_id: str, user_email: str = Depends(get_current_user)):
    """Get a conversation with all messages.

    Allows read-only access to any conversation (shared via UUID link).
    Returns is_owner flag to indicate if current user owns the conversation.
    """
    conv = store.get_conversation(conv_id)
    if not conv:
        return JSONResponse({"error": "Conversation not found"}, status_code=404)

    is_owner = conv.user_id == user_email or conv.user_id is None

    agent = get_agent_instance()
    return {
        **conv.to_dict(),
        "is_running": agent.is_running(conv_id),
        "is_owner": is_owner,
        "links": {
            "self": f"/api/conversations/{conv_id}",
            "messages": f"/api/conversations/{conv_id}/messages",
            "stream": f"/api/conversations/{conv_id}/stream",
        },
    }


@router.delete("/{conv_id}")
def delete_conversation(conv_id: str, user_email: str = Depends(get_current_user)):
    """Delete a conversation. User must be owner or admin."""
    conv = store.get_conversation(conv_id)
    if not conv:
        return JSONResponse({"error": "Conversation not found"}, status_code=404)

    is_admin = user_email in ADMIN_USERS
    is_owner = conv.user_id == user_email
    if not is_admin and not is_owner:
        return JSONResponse({"error": "Permission denied"}, status_code=403)

    if store.delete_conversation(conv_id):
        return Response(status_code=200)
    return JSONResponse({"error": "Failed to delete"}, status_code=500)


@router.post("/{conv_id}/pin")
async def pin_conversation(conv_id: str, request: Request, user_email: str = Depends(get_current_user)):
    """Pin a conversation to the sidebar. Admin only."""
    if user_email not in ADMIN_USERS:
        return JSONResponse({"error": "Permission denied"}, status_code=403)

    conv = store.get_conversation(conv_id, include_messages=False)
    if not conv:
        return JSONResponse({"error": "Conversation not found"}, status_code=404)

    body = await request.body()
    data = (await request.json()) if body else {}
    label = data.get("label", "").strip() or conv.title or "Sans titre"

    if store.pin_conversation(conv_id, label):
        return {"ok": True, "label": label}
    return JSONResponse({"error": "Failed to pin"}, status_code=500)


@router.delete("/{conv_id}/pin")
def unpin_conversation(conv_id: str, user_email: str = Depends(get_current_user)):
    """Unpin a conversation from the sidebar. Admin only."""
    if user_email not in ADMIN_USERS:
        return JSONResponse({"error": "Permission denied"}, status_code=403)

    if store.unpin_conversation(conv_id):
        return {"ok": True}
    return JSONResponse({"error": "Failed to unpin"}, status_code=500)


@router.patch("/{conv_id}")
async def update_conversation(conv_id: str, request: Request):
    """Update conversation (title, etc.)."""
    data = await request.json()
    if not data:
        return JSONResponse({"error": "No data provided"}, status_code=400)

    title = data.get("title")
    if title is not None:
        store.update_conversation(conv_id, title=title)
        return {"title": title}

    return JSONResponse({"error": "No valid fields to update"}, status_code=400)


@router.post("/{conv_id}/generate-title")
def generate_title(conv_id: str):
    """Generate a title for a conversation using LLM."""
    conv = store.get_conversation(conv_id)
    if not conv:
        return JSONResponse({"error": "Conversation not found"}, status_code=404)

    user_messages = []
    last_assistant_msg = None
    for msg in conv.messages:
        if msg.type == "user" and len(user_messages) < 2:
            user_messages.append(msg.content[:300])
        if msg.type == "assistant":
            last_assistant_msg = msg.content[:500]

    # For reports without user messages, use original_query or report title
    if not user_messages and conv.report:
        if conv.report.original_query:
            user_messages.append(conv.report.original_query[:300])
        elif conv.report.title:
            user_messages.append(conv.report.title)

    if not user_messages:
        return JSONResponse({"error": "No user message to generate title from"}, status_code=400)

    context_parts = []
    for i, um in enumerate(user_messages, 1):
        context_parts.append(f"Message utilisateur {i}: {um}")
    if last_assistant_msg:
        context_parts.append(f"Derniere reponse: {last_assistant_msg}")
    context = "\n\n".join(context_parts)

    try:
        model = config.OLLAMA_TITLE_MODEL if config.LLM_BACKEND in ("ollama", "cli-ollama") else config.CLAUDE_MODEL
        prompt = (
            "Ecris un titre court et direct (6-10 mots) sur le theme de cette conversation. "
            "En francais uniquement. Pas de guillemets.\n\n"
            f"{context}"
        )
        title = llm.generate_text(prompt, model=model, max_tokens=50).strip().strip('"\'')[:100]
        store.update_conversation(conv_id, title=title)
        return {"title": title}

    except Exception as exc:
        logger.error(f"Failed to generate title: {exc}")
        return JSONResponse({"error": str(exc)}, status_code=500)


@router.post("/{conv_id}/fork")
def fork_conversation(conv_id: str, user_email: str = Depends(get_current_user)):
    """Fork (deep copy) a conversation.

    Creates a new conversation owned by the current user with all messages copied.
    The original conversation is unchanged.
    """
    if not user_email:
        return JSONResponse({"error": "Authentication required"}, status_code=401)

    source = store.get_conversation(conv_id, include_messages=False)
    if not source:
        return JSONResponse({"error": "Conversation not found"}, status_code=404)

    new_conv = store.fork_conversation(conv_id, user_email)
    if not new_conv:
        return JSONResponse({"error": "Failed to fork conversation"}, status_code=500)

    return {
        "id": new_conv.id,
        "forked_from": conv_id,
        "links": {
            "self": f"/api/conversations/{new_conv.id}",
            "view": f"/explorations/{new_conv.id}",
        },
    }


@router.post("/{conv_id}/messages")
async def send_message(conv_id: str, request: Request, user_email: str = Depends(get_current_user)):
    """Send a message to start agent processing.

    Only the conversation owner can send messages. Shared conversations are read-only.
    """
    conv = store.get_conversation(conv_id)
    if not conv:
        return JSONResponse({"error": "Conversation not found"}, status_code=404)

    # Check ownership - only owner can send messages
    if conv.user_id and conv.user_id != user_email:
        return JSONResponse(
            {"error": "Cette conversation appartient à un autre utilisateur. Vous pouvez la consulter mais pas y ajouter de messages."},
            status_code=403,
        )

    data = await request.json()
    if not data or "content" not in data:
        return JSONResponse({"error": "Missing 'content' field"}, status_code=400)

    content = data["content"]
    agent = get_agent_instance()

    if agent.is_running(conv_id):
        return JSONResponse({"error": "Conversation already running"}, status_code=409)

    is_first_message = len(conv.messages) == 0
    store.add_message(conv_id, "user", content)
    store.update_conversation(conv_id, needs_response=True)

    if is_first_message:
        generate_conversation_title(content, conv_id)
        generate_conversation_tags(content, conv_id)

    return {
        "status": "started",
        "links": {
            "stream": f"/api/conversations/{conv_id}/stream",
            "cancel": f"/api/conversations/{conv_id}/cancel",
        },
    }


@router.get("/{conv_id}/stream")
async def stream_conversation(conv_id: str, user_email: str = Depends(get_current_user)):
    """Stream agent responses via Server-Sent Events.

    Allows streaming for shared conversations (read-only view of existing responses).
    New agent runs are still restricted to the owner via send_message.
    """
    from ..helpers import get_staging_dir, KNOWLEDGE_ROOT
    from ..audit import audit_log

    conv = store.get_conversation(conv_id)
    if not conv:
        return JSONResponse({"error": "Conversation not found"}, status_code=404)

    if not conv.messages:
        return JSONResponse({"error": "No messages in conversation"}, status_code=400)

    agent = get_agent_instance()

    # Find the last user message content
    last_user_msg = None
    for msg in conv.messages:
        if msg.type == "user":
            last_user_msg = msg.content

    # If no response needed and agent not running, nothing to stream
    if not conv.needs_response and not agent.is_running(conv_id):
        async def done_stream():
            yield f"event: done\n"
            yield f"data: {json.dumps({'conversation_id': conv_id})}\n\n"

        return StreamingResponse(
            done_stream(),
            media_type="text/event-stream",
            headers={"Cache-Control": "no-cache", "X-Accel-Buffering": "no"},
        )

    if agent.is_running(conv_id):
        async def wait_stream():
            yield f"event: system\n"
            yield f"data: {json.dumps({'content': 'Agent already running, please wait...'})}\n\n"
            for _ in range(60):
                await asyncio.sleep(1)
                if not agent.is_running(conv_id):
                    yield f"event: done\n"
                    yield f"data: {json.dumps({'conversation_id': conv_id, 'reload': True})}\n\n"
                    return
                yield ": keepalive\n\n"
            yield f"event: error\n"
            yield f"data: {json.dumps({'error': 'Timeout waiting for agent'})}\n\n"

        return StreamingResponse(
            wait_stream(),
            media_type="text/event-stream",
            headers={"Cache-Control": "no-cache", "X-Accel-Buffering": "no"},
        )

    if not last_user_msg:
        return JSONResponse({"error": "No user message to respond to"}, status_code=400)

    last_message = last_user_msg

    # Inject knowledge editing context for knowledge conversations
    if conv.conv_type == "knowledge" and conv.file_path:
        staging_dir = get_staging_dir(conv.id)
        original_path = KNOWLEDGE_ROOT / conv.file_path
        staged_path = staging_dir / conv.file_path

        is_first_message = not any(m.type == "user" for m in conv.messages[:-1])

        if is_first_message:
            if staged_path.exists():
                file_content = staged_path.read_text()
            elif original_path.exists():
                file_content = original_path.read_text()
            else:
                file_content = "(fichier introuvable)"

            knowledge_context = f"""You are editing a knowledge file.

IMPORTANT: Write ALL changes to the staging directory:
  {staging_dir}/

The original file is at: knowledge/{conv.file_path}
Your working copy is at: {staged_path}

Current content of {conv.file_path}:
---
{file_content}
---

User request: """
        else:
            knowledge_context = f"""(Reminder: write changes to {staged_path})

User request: """

        last_message = knowledge_context + last_message

    async def generate():
        history = []
        for msg in conv.messages[:-1]:
            if msg.type in ("user", "assistant"):
                history.append({"role": msg.type, "content": msg.content})

        # Storage state
        assistant_text_parts = []
        assistant_msg_id = None
        error_holder = [None]

        try:
            async for event in agent.send_message(
                conversation_id=conv_id,
                message=last_message,
                history=history,
                session_id=conv.session_id,
            ):
                # Store to database FIRST (survives client disconnect)
                if event.type == "assistant":
                    assistant_text_parts.append(str(event.content))
                    append_mode = bool(getattr(event, "raw", {}).get("append"))
                    if append_mode:
                        full_text = "".join(assistant_text_parts)
                    else:
                        full_text = "\n".join(assistant_text_parts)
                    if assistant_msg_id is None:
                        msg = store.add_message(conv_id, "assistant", full_text)
                        assistant_msg_id = msg.id if msg else None
                    else:
                        store.update_message(assistant_msg_id, full_text)

                if event.type in ("tool_use", "tool_result"):
                    # Finalize current assistant message so next text creates a new one
                    if event.type == "tool_use":
                        assistant_msg_id = None
                        assistant_text_parts = []

                    # Add taxonomy category to tool_use events
                    if event.type == "tool_use" and isinstance(event.content, dict):
                        tool_name = event.content.get("tool", "")
                        tool_input = event.content.get("input", {})
                        category = classify_tool(tool_name, tool_input)
                        enriched = {**event.content, "category": category}
                        content = json.dumps(enriched)
                        # Attach enriched content for SSE
                        event._sse_content = enriched

                        # Audit log tool usage
                        audit_log(
                            conversation_id=conv_id,
                            user_email=user_email,
                            tool_name=tool_name,
                            tool_input=tool_input,
                        )
                    # Parse API signals from tool_result events
                    elif event.type == "tool_result":
                        if isinstance(event.content, dict) and 'output' in event.content:
                            raw_content = event.content['output']
                            if not isinstance(raw_content, str):
                                raw_content = str(raw_content)
                        elif isinstance(event.content, str):
                            raw_content = event.content
                        else:
                            raw_content = str(event.content)
                        api_calls = parse_api_signals(raw_content)
                        if api_calls:
                            enriched = {
                                "output": event.content,
                                "api_calls": api_calls,
                            }
                            content = json.dumps(enriched)
                            event._sse_content = enriched
                        else:
                            content = json.dumps(event.content) if isinstance(event.content, dict) else str(event.content)
                    else:
                        content = json.dumps(event.content) if isinstance(event.content, dict) else str(event.content)

                    store.add_message(conv_id, event.type, content)

                if event.type == "system":
                    # Handle session ID from init event
                    if event.raw.get("subtype") == "init":
                        new_session_id = event.raw.get("session_id")
                        if new_session_id:
                            store.update_conversation(conv_id, session_id=new_session_id)

                    # Extract and store token usage from result event
                    if event.raw.get("usage"):
                        usage = event.raw["usage"]
                        extra = {}
                        if usage.get("service_tier"):
                            extra["service_tier"] = usage["service_tier"]
                        if usage.get("web_search_requests"):
                            extra["web_search_requests"] = usage["web_search_requests"]

                        store.accumulate_usage(
                            conv_id,
                            input_tokens=usage.get("input_tokens", 0),
                            output_tokens=usage.get("output_tokens", 0),
                            cache_creation_tokens=usage.get("cache_creation_input_tokens", 0),
                            cache_read_tokens=usage.get("cache_read_input_tokens", 0),
                            backend=config.AGENT_BACKEND,
                            extra=extra if extra else None,
                        )

                # Yield SSE data
                if hasattr(event, '_sse_content'):
                    sse_data = {"type": event.type, "content": event._sse_content}
                else:
                    sse_data = event.to_dict()

                yield f"event: {event.type}\n"
                yield f"data: {json.dumps(sse_data)}\n\n"

        except Exception as e:
            logger.error(f"Stream error for {conv_id}: {e}", exc_info=True)
            error_holder[0] = e
        finally:
            store.update_conversation(conv_id, needs_response=False)

        if error_holder[0]:
            yield f"event: error\n"
            yield f"data: {json.dumps({'error': str(error_holder[0])})}\n\n"

        yield "event: done\n"
        yield f"data: {json.dumps({'conversation_id': conv_id})}\n\n"

    return StreamingResponse(
        generate(),
        media_type="text/event-stream",
        headers={"Cache-Control": "no-cache", "X-Accel-Buffering": "no"},
    )


@router.post("/{conv_id}/cancel")
async def cancel_conversation(conv_id: str):
    """Cancel a running conversation."""
    agent = get_agent_instance()
    cancelled = await agent.cancel(conv_id)

    if cancelled:
        return {"status": "cancelled"}
    return {"status": "not_running"}


@router.get("/running")
def get_running():
    """Get list of currently running conversation IDs."""
    agent = get_agent_instance()
    running_ids = list(agent._running) if hasattr(agent, '_running') else []
    return {"running": running_ids}


@router.get("/{conv_id}/tags")
def get_conversation_tags(conv_id: str):
    """Get tags for a conversation."""
    tags = store.get_conversation_tags(conv_id)
    return {
        "tags": [{"name": t.name, "type": t.type, "label": t.label} for t in tags]
    }


@router.put("/{conv_id}/tags")
async def set_conversation_tags(conv_id: str, request: Request):
    """Set tags for a conversation (replaces existing)."""
    data = await request.json()
    if not data or "tags" not in data:
        return JSONResponse({"error": "Missing 'tags' field"}, status_code=400)

    tag_names = data["tags"]
    if not isinstance(tag_names, list):
        return JSONResponse({"error": "'tags' must be a list"}, status_code=400)

    store.set_conversation_tags(conv_id, tag_names)
    tags = store.get_conversation_tags(conv_id)
    return {
        "tags": [{"name": t.name, "type": t.type, "label": t.label} for t in tags]
    }


# =============================================================================
# File Upload Endpoints
# =============================================================================

@router.post("/{conv_id}/files")
async def upload_file_endpoint(conv_id: str, file: UploadFile, user_email: str = Depends(get_current_user)):
    """Upload a file to a conversation.

    Accepts multipart/form-data with 'file' field.
    Returns file metadata and optional text content for small text files.
    """
    conv = store.get_conversation(conv_id, include_messages=False)
    if not conv:
        return JSONResponse({"error": "Conversation not found"}, status_code=404)

    # Check ownership
    if conv.user_id and conv.user_id != user_email:
        return JSONResponse({"error": "Permission denied"}, status_code=403)

    # Check conversation type
    if conv.conv_type == "report":
        return JSONResponse({"error": "Cannot upload files to report conversations"}, status_code=400)

    if not file.filename:
        return JSONResponse({"error": "No file selected"}, status_code=400)

    try:
        uploaded_file, text_content = do_upload_file(
            file_obj=file.file,
            filename=file.filename,
            conversation_id=conv_id,
            user_id=user_email,
            check_duplicate=True,
        )

        response = {
            "file": uploaded_file.to_dict(),
            "text_content": text_content,
            "context_message": format_file_for_context(uploaded_file, text_content),
        }
        return JSONResponse(response, status_code=201)

    except FileTooLargeError as e:
        return JSONResponse({"error": f"File too large: {e}"}, status_code=413)
    except BlockedFileTypeError as e:
        return JSONResponse({"error": f"File type not allowed: {e}"}, status_code=415)
    except AVScanFailedError as e:
        return JSONResponse({"error": f"File failed security scan: {e}"}, status_code=422)
    except Exception as e:
        logger.error(f"File upload failed: {e}")
        return JSONResponse({"error": "Upload failed"}, status_code=500)


@router.get("/{conv_id}/files")
def list_files(conv_id: str):
    """List all files uploaded to a conversation."""
    conv = store.get_conversation(conv_id, include_messages=False)
    if not conv:
        return JSONResponse({"error": "Conversation not found"}, status_code=404)

    files = store.get_conversation_files(conv_id)
    return {
        "files": [f.to_dict() for f in files]
    }


@router.get("/{conv_id}/files/{file_id}")
def get_file(conv_id: str, file_id: int):
    """Get metadata for a specific uploaded file."""
    uploaded_file = store.get_uploaded_file(file_id)
    if not uploaded_file:
        return JSONResponse({"error": "File not found"}, status_code=404)

    if uploaded_file.conversation_id != conv_id:
        return JSONResponse({"error": "File not in this conversation"}, status_code=404)

    return {"file": uploaded_file.to_dict()}


@router.get("/{conv_id}/files/{file_id}/content")
def get_file_content_endpoint(conv_id: str, file_id: int):
    """Download the content of an uploaded file."""
    uploaded_file = store.get_uploaded_file(file_id)
    if not uploaded_file:
        return JSONResponse({"error": "File not found"}, status_code=404)

    if uploaded_file.conversation_id != conv_id:
        return JSONResponse({"error": "File not in this conversation"}, status_code=404)

    content = get_file_content(uploaded_file)
    if content is None:
        return JSONResponse({"error": "File content not available"}, status_code=404)

    return Response(
        content=content,
        media_type=uploaded_file.mime_type or "application/octet-stream",
        headers={
            "Content-Disposition": f'attachment; filename="{uploaded_file.original_filename}"'
        }
    )


@router.post("/{conv_id}/files/{file_id}/copy")
async def copy_file(conv_id: str, file_id: int, request: Request, user_email: str = Depends(get_current_user)):
    """Create a writable copy of an uploaded file for modification.

    Used when the user asks the agent to modify a file.
    The original remains read-only.
    """
    uploaded_file = store.get_uploaded_file(file_id)
    if not uploaded_file:
        return JSONResponse({"error": "File not found"}, status_code=404)

    if uploaded_file.conversation_id != conv_id:
        return JSONResponse({"error": "File not in this conversation"}, status_code=404)

    # Check ownership
    conv = store.get_conversation(conv_id, include_messages=False)
    if conv and conv.user_id and conv.user_id != user_email:
        return JSONResponse({"error": "Permission denied"}, status_code=403)

    body = await request.body()
    data = (await request.json()) if body else {}
    new_filename = data.get("filename")

    copy_path = copy_file_for_modification(uploaded_file, new_filename=new_filename)
    if copy_path is None:
        return JSONResponse({"error": "Failed to create copy"}, status_code=500)

    return {
        "copy_path": str(copy_path),
        "original_file": uploaded_file.to_dict(),
    }
