#!/bin/sh
set -e
alembic upgrade head
python -m web.warmup
