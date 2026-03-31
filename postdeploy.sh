#!/bin/sh
set -e

# FIXME: remove this block after the first successful deploy.
# One-time migration: the prod DB predates Alembic and needs stamping
# so that `alembic upgrade head` doesn't try to recreate existing tables.
if ! python -c "
from web.db import get_engine
from sqlalchemy import inspect
print('yes' if inspect(get_engine()).has_table('alembic_version') else 'no')
" 2>/dev/null | grep -q "yes"; then
    echo "First Alembic run — stamping existing database"
    alembic stamp head
fi

alembic upgrade head
