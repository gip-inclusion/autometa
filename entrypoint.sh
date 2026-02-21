#!/bin/sh
# Start the process manager in background, then run uvicorn
python -m web.pm &
PM_PID=$!
trap "kill $PM_PID" EXIT
exec uvicorn web.app:app --host 0.0.0.0 --port "${WEB_PORT:-5000}"
