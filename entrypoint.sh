#!/bin/sh
python -m web.warmup
exec uvicorn web.app:app --host 0.0.0.0 --port "${WEB_PORT:-5000}"
