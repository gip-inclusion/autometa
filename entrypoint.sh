#!/bin/sh
# PM runs in-process via FastAPI lifespan (web/app.py) — no separate subprocess needed.

# Keep OAuth token alive (check every 10 minutes, refresh if < 1h remaining)
(sleep 10; while true; do
  python -c "
from web.claude_credentials import ensure_valid_token
ensure_valid_token()
" 2>&1 | head -5
  sleep 600
done) &
REFRESH_PID=$!

# Health check: restart crashed project containers every 60s
# Docker cleanup: run daily (track via timestamp file)
(sleep 30; while true; do
  python -c "
from lib.docker_deploy import health_check_all, docker_available
if docker_available():
    health_check_all()
" 2>/dev/null

  # Daily cleanup: prune dangling images, stopped containers, build cache
  CLEANUP_FILE=/app/data/.last_cleanup
  if [ ! -f "$CLEANUP_FILE" ] || [ "$(find "$CLEANUP_FILE" -mmin +1440 2>/dev/null)" ]; then
    python -c "
from lib.docker_cleanup import cleanup
from lib.docker_deploy import docker_available
if docker_available():
    result = cleanup()
    if result.get('dangling_images') or result.get('stopped_containers'):
        print(f'Cleanup: {result[\"dangling_images\"]} images, {result[\"stopped_containers\"]} containers')
" 2>/dev/null
    touch "$CLEANUP_FILE"
  fi

  sleep 60
done) &
HEALTH_PID=$!

trap "kill $REFRESH_PID $HEALTH_PID" EXIT
exec uvicorn web.app:app --host 0.0.0.0 --port "${WEB_PORT:-5000}"
