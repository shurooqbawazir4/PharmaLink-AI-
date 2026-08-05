# Bring up the MedCycle AI dev stack (db + redis + backend) and apply
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

Write-Host "==> Starting db + redis"
docker compose @composeArgs up -d db redis

Write-Host "==> Applying migrations"
docker compose @composeArgs run --rm backend alembic upgrade head

Write-Host "==> Starting backend"
docker compose @composeArgs up -d backend

Write-Host ""
Write-Host "MedCycle AI backend is up:"
Write-Host "  Docs:   http://localhost:8000/docs"
Write-Host "  Health: http://localhost:8000/api/v1/health"
