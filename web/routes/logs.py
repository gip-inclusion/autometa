"""Log streaming routes."""

import json
import time

from flask import Blueprint, Response, jsonify, request

from .. import config

bp = Blueprint("logs", __name__, url_prefix="/api/logs")


@bp.route("")
def stream_logs():
    """Stream agent logs via SSE (tail -f style)."""
    lines = request.args.get("lines", 50, type=int)

    def generate():
        # First, send last N lines
        try:
            with open(config.LOG_FILE, "r") as f:
                all_lines = f.readlines()
                for line in all_lines[-lines:]:
                    yield f"data: {json.dumps({'line': line.rstrip()})}\n\n"
        except FileNotFoundError:
            yield f"data: {json.dumps({'line': '[No logs yet]'})}\n\n"

        # Then tail the file
        try:
            with open(config.LOG_FILE, "r") as f:
                f.seek(0, 2)  # Go to end
                while True:
                    line = f.readline()
                    if line:
                        yield f"data: {json.dumps({'line': line.rstrip()})}\n\n"
                    else:
                        time.sleep(0.5)
                        yield ": keepalive\n\n"
        except GeneratorExit:
            pass

    return Response(
        generate(),
        mimetype="text/event-stream",
        headers={"Cache-Control": "no-cache", "X-Accel-Buffering": "no"},
    )


@bp.route("/recent")
def get_recent_logs():
    """Get recent log lines (non-streaming)."""
    lines = request.args.get("lines", 100, type=int)
    try:
        with open(config.LOG_FILE, "r") as f:
            all_lines = f.readlines()
            return jsonify({"lines": [l.rstrip() for l in all_lines[-lines:]]})
    except FileNotFoundError:
        return jsonify({"lines": []})
