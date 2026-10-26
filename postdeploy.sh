#!/bin/sh
set -e

python -m lib.migrate
python -m lib.review_fixtures
