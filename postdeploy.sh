#!/bin/sh
set -e

python -m lib.migrate

# Why: V1 one-shot import — APP.md → dashboards table. Idempotent (upserts).
# À retirer (avec lib/dashboards_import_v1.py et son test) une fois exécuté
# en prod et staging.
python -m lib.dashboards_import_v1
