#!/bin/sh
# Start the process manager in background, then run uvicorn
python -m web.pm &
PM_PID=$!

# Keep OAuth token alive (refresh every 30 minutes)
(while true; do
  claude auth status >/dev/null 2>&1
  sleep 1800
done) &
REFRESH_PID=$!

# Health check: restart crashed project containers every 60s
(sleep 30; while true; do
  python -c "
from lib.docker_deploy import health_check_all, docker_available
if docker_available():
    health_check_all()
" 2>/dev/null
  sleep 60
done) &
HEALTH_PID=$!

trap "kill $PM_PID $REFRESH_PID $HEALTH_PID" EXIT
exec uvicorn web.app:app --host 0.0.0.0 --port "${WEB_PORT:-5000}"
