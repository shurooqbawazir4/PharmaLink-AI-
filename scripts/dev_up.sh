#!/usr/bin/env bash
# Bring up the MedCycle AI dev stack (db + redis + backend) and apply
# migrations. Run from the repo root: ./scripts/dev_up.sh
set -euo pipefail

cd "$(dirname "$0")/.."

if [ ! -f docker/.env ]; then
  echo "docker/.env not found — copying from docker/.env.example"
  cp docker/.env.example docker/.env
fi

COMPOSE="docker compose -f docker/docker-compose.yml --env-file docker/.env"

echo "==> Building images"
$COMPOSE build

echo "==> Starting db + redis + adminer"
$COMPOSE up -d db redis adminer

echo "==> Applying migrations"
$COMPOSE run --rm backend alembic upgrade head

echo "==> Starting backend + celery worker/beat + frontend"
$COMPOSE up -d backend celery_worker celery_beat frontend

echo
echo "MedCycle AI is up:"
echo "  Dashboard: http://localhost:3000"
echo "  API docs:  http://localhost:8000/docs"
echo "  Health:    http://localhost:8000/api/v1/health"
echo "  Adminer:   http://localhost:8080  (System: PostgreSQL, Server: db, User/DB: medcycle)"
