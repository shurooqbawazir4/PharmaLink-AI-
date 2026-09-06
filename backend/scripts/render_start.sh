#!/bin/sh
set -eu

cd /app/backend
alembic upgrade head
if [ "${SEED_DEMO_DATA:-false}" = "true" ]; then
    python /app/data/synthetic/generate.py --demo
    python scripts/seed_database.py
fi
exec uvicorn app.main:app --host 0.0.0.0 --port "${PORT:-8000}"
