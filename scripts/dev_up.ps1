# Bring up the PharmaLink AI dev stack (db + redis + backend) and apply
# migrations. Run from the repo root: .\scripts\dev_up.ps1

$ErrorActionPreference = "Stop"
Set-Location (Join-Path $PSScriptRoot "..")

if (-not (Test-Path "docker/.env")) {
    Write-Host "docker/.env not found — copying from docker/.env.example"
    Copy-Item "docker/.env.example" "docker/.env"
}

$composeArgs = @("-f", "docker/docker-compose.yml", "--env-file", "docker/.env")

Write-Host "==> Building images"
docker compose @composeArgs build

Write-Host "==> Starting db + redis + adminer"
docker compose @composeArgs up -d db redis adminer

Write-Host "==> Applying migrations"
docker compose @composeArgs run --rm backend alembic upgrade head

Write-Host "==> Starting backend + celery worker/beat + frontend"
docker compose @composeArgs up -d backend celery_worker celery_beat frontend

Write-Host ""
Write-Host "PharmaLink AI is up:"
Write-Host "  Dashboard: http://localhost:3000"
Write-Host "  API docs:  http://localhost:8000/docs"
Write-Host "  Health:    http://localhost:8000/api/v1/health"
Write-Host "  Adminer:   http://localhost:8080  (System: PostgreSQL, Server: db, User/DB: medcycle)"
