"""Log streaming routes."""

import json
import time

from fastapi import APIRouter, Query
from fastapi.responses import StreamingResponse

from .. import config

router = APIRouter(prefix="/api/logs")


@router.get("")
def stream_logs(lines: int = Query(default=50)):
    """Stream agent logs via SSE (tail -f style)."""

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

    return StreamingResponse(
        generate(),
        media_type="text/event-stream",
        headers={"Cache-Control": "no-cache", "X-Accel-Buffering": "no"},
    )


@router.get("/recent")
def get_recent_logs(lines: int = Query(default=100)):
    """Get recent log lines (non-streaming)."""
    try:
        with open(config.LOG_FILE, "r") as f:
            all_lines = f.readlines()
            return {"lines": [l.rstrip() for l in all_lines[-lines:]]}
    except FileNotFoundError:
        return {"lines": []}
