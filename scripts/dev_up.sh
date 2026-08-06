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

echo "==> Starting db + redis"
$COMPOSE up -d db redis

echo "==> Applying migrations"
$COMPOSE run --rm backend alembic upgrade head

echo "==> Starting backend + celery worker"
$COMPOSE up -d backend celery_worker

echo
echo "MedCycle AI backend is up:"
echo "  Docs:   http://localhost:8000/docs"
echo "  Health: http://localhost:8000/api/v1/health"
