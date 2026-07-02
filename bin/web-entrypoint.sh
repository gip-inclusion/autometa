#!/bin/bash
set -e

if [ "$APP_ROLE" = "prefect-server" ]; then
    exec uv run prefect server start --host 0.0.0.0 --port "$PORT"
else
    exec /app/bin/start_with_oauth2_proxy.sh uvicorn web.app:app --host 0.0.0.0 --port 8080
fi
