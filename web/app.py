"""Matometa web application - Flask server with SSE streaming."""

import asyncio
import json
from flask import Flask, Response, jsonify, render_template, request

from . import config
from .storage import store
from .agents import get_agent

app = Flask(__name__)

# Global agent instance
_agent = None


def get_agent_instance():
    """Get or create the agent backend instance."""
    global _agent
    if _agent is None:
        _agent = get_agent()
    return _agent


# -----------------------------------------------------------------------------
# HTML Routes
# -----------------------------------------------------------------------------


@app.route("/")
def index():
    """Redirect to explorations."""
    return render_template("explorations.html", section="explorations")


@app.route("/explorations")
def explorations():
    """Explorations section - chat interface."""
    return render_template("explorations.html", section="explorations")


@app.route("/connaissances")
def connaissances():
    """Connaissances section - placeholder."""
    return render_template("connaissances.html", section="connaissances")


# -----------------------------------------------------------------------------
# API Routes - Conversations
# -----------------------------------------------------------------------------


@app.route("/api/conversations", methods=["POST"])
def create_conversation():
    """Create a new conversation."""
    conv = store.create(user_id=None)  # No auth yet
    return jsonify(
        {
            "id": conv.id,
            "links": {
                "self": f"/api/conversations/{conv.id}",
                "messages": f"/api/conversations/{conv.id}/messages",
                "stream": f"/api/conversations/{conv.id}/stream",
            },
        }
    )


@app.route("/api/conversations/<conv_id>", methods=["GET"])
def get_conversation(conv_id: str):
    """Get a conversation with all messages."""
    conv = store.get(conv_id)
    if not conv:
        return jsonify({"error": "Conversation not found"}), 404

    return jsonify(
        {
            **conv.to_dict(),
            "links": {
                "self": f"/api/conversations/{conv_id}",
                "messages": f"/api/conversations/{conv_id}/messages",
                "stream": f"/api/conversations/{conv_id}/stream",
            },
        }
    )


@app.route("/api/conversations", methods=["GET"])
def list_conversations():
    """List recent conversations."""
    limit = request.args.get("limit", 20, type=int)
    convs = store.list_recent(limit=limit)
    return jsonify(
        {
            "conversations": [
                {
                    "id": c.id,
                    "title": c.title,
                    "updated_at": c.updated_at.isoformat(),
                    "message_count": len(c.messages),
                    "links": {"self": f"/api/conversations/{c.id}"},
                }
                for c in convs
            ]
        }
    )


# -----------------------------------------------------------------------------
# API Routes - Messages
# -----------------------------------------------------------------------------


@app.route("/api/conversations/<conv_id>/messages", methods=["POST"])
def send_message(conv_id: str):
    """Send a message to start agent processing."""
    conv = store.get(conv_id)
    if not conv:
        return jsonify({"error": "Conversation not found"}), 404

    data = request.get_json()
    if not data or "content" not in data:
        return jsonify({"error": "Missing 'content' field"}), 400

    content = data["content"]

    # Check if already running
    agent = get_agent_instance()
    if agent.is_running(conv_id):
        return jsonify({"error": "Conversation already running"}), 409

    # Add user message to conversation
    store.append_message(conv_id, "user", content)

    return jsonify(
        {
            "status": "started",
            "links": {
                "stream": f"/api/conversations/{conv_id}/stream",
                "cancel": f"/api/conversations/{conv_id}/cancel",
            },
        }
    )


@app.route("/api/conversations/<conv_id>/stream", methods=["GET"])
def stream_conversation(conv_id: str):
    """Stream agent responses via Server-Sent Events."""
    conv = store.get(conv_id)
    if not conv:
        return jsonify({"error": "Conversation not found"}), 404

    if not conv.messages:
        return jsonify({"error": "No messages in conversation"}), 400

    # Get the last user message
    last_message = None
    for msg in reversed(conv.messages):
        if msg.role == "user":
            last_message = msg.content
            break

    if not last_message:
        return jsonify({"error": "No user message to respond to"}), 400

    def generate():
        """Generate SSE events from agent."""
        agent = get_agent_instance()

        # Get history (excluding the last user message we're responding to)
        history = []
        for msg in conv.messages[:-1]:
            history.append({"role": msg.role, "content": msg.content})

        # Collect all events for the assistant response
        all_events = []
        assistant_text_parts = []

        # Run async generator in sync context
        async def stream():
            async for event in agent.send_message(
                conversation_id=conv_id,
                message=last_message,
                history=history,
                session_id=conv.session_id,
            ):
                yield event

        # Create event loop for async iteration
        loop = asyncio.new_event_loop()
        try:
            gen = stream()
            while True:
                try:
                    event = loop.run_until_complete(gen.__anext__())
                    all_events.append(event.raw)

                    # Collect assistant text
                    if event.type == "assistant":
                        assistant_text_parts.append(str(event.content))

                    # Yield SSE event
                    yield f"event: {event.type}\n"
                    yield f"data: {json.dumps(event.to_dict())}\n\n"

                except StopAsyncIteration:
                    break
        finally:
            loop.close()

        # Save assistant response to conversation
        if assistant_text_parts:
            full_response = "\n".join(assistant_text_parts)
            store.append_message(conv_id, "assistant", full_response, all_events)

        # Send done event
        yield "event: done\n"
        yield f"data: {json.dumps({'conversation_id': conv_id})}\n\n"

    return Response(
        generate(),
        mimetype="text/event-stream",
        headers={
            "Cache-Control": "no-cache",
            "X-Accel-Buffering": "no",  # Disable nginx buffering
        },
    )


@app.route("/api/conversations/<conv_id>/cancel", methods=["POST"])
def cancel_conversation(conv_id: str):
    """Cancel a running conversation."""
    agent = get_agent_instance()

    # Run cancel in event loop
    loop = asyncio.new_event_loop()
    try:
        cancelled = loop.run_until_complete(agent.cancel(conv_id))
    finally:
        loop.close()

    if cancelled:
        return jsonify({"status": "cancelled"})
    else:
        return jsonify({"status": "not_running"})


# -----------------------------------------------------------------------------
# Main
# -----------------------------------------------------------------------------


def main():
    """Run the development server."""
    print(f"Starting Matometa web server at http://{config.HOST}:{config.PORT}")
    print(f"Agent backend: {config.AGENT_BACKEND}")
    print(f"Working directory: {config.BASE_DIR}")
    app.run(host=config.HOST, port=config.PORT, debug=config.DEBUG, threaded=True)


if __name__ == "__main__":
    main()
