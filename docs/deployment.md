# PharmaLink AI — Deployment Guide

## Two stacks, one base file

`docker/docker-compose.yml` is the base — db, redis, backend, celery
worker/beat, and a dev-mode frontend (hot reload, bind-mounted source).
`docker/docker-compose.prod.yml` is a thin overlay on top of it, not a
separate stack: it changes only what actually differs in production.

```bash
# Dev (Milestone A–D's default) — as documented in the root README
docker compose -f docker/docker-compose.yml --env-file docker/.env up -d

# Production-shaped — standalone Next.js build + nginx on :80
docker compose -f docker/docker-compose.yml -f docker/docker-compose.prod.yml \
  --env-file docker/.env up -d --build
```

What the overlay changes:

- **frontend** builds the `prod` target of `docker/Dockerfile.frontend`
  (Next.js `output: "standalone"` — see `frontend/next.config.ts`) instead
  of `dev`. `NEXT_PUBLIC_API_URL` is baked in at *build* time as `/api/v1`
  (a relative path, not a host) since `NEXT_PUBLIC_*` vars are inlined into
  the client JS bundle, not read at container start — a relative path works
  regardless of what domain nginx ends up behind.
- **nginx** (new) is the only published entry point (`:80`) — reverse
  proxies `/api/*` to `backend:8000`, everything else to `frontend:3000`.
  Config: `docker/nginx/nginx.conf`.
- **backend**/**frontend** stop publishing their own host ports (`8000`/
  `3000`) — nginx is the single front door in this shape.
- Compose merges lists (`ports`, `volumes`) by union, not replacement, so
  clearing the dev bind mount/port requires the explicit `!reset` YAML tag
  rather than an empty `[]` — see the comments in `docker-compose.prod.yml`
  if extending it.

**Not done here, by design:** TLS termination (put a real load balancer or
a certbot sidecar in front of nginx for a real deployment), and Postgres/
Redis are still published to the host in both stacks for local
convenience — a real deployment should drop those two port mappings and
keep them on the internal Docker network only.

## Celery beat (periodic jobs)

`celery_beat` (both compose files) runs the schedule defined in
`backend/app/core/celery_app.py`: a nightly forecast refresh at 02:00 UTC
(`forecast.refresh_all`), followed by a network optimization run at 04:00
UTC (`optimization.run_network`) so it sees same-day-fresh forecasts. Both
tasks are the exact same code the on-demand HTTP endpoints and Milestone C's
manual `celery ... call` invocation use — see `docs/architecture.md`'s
Celery section.

## CI

`.github/workflows/ci.yml` runs on every push/PR: a `backend` job
(`pip install -e ".[dev]" -e ../ml`, then `ruff check . && mypy . && pytest`)
and a `frontend` job (`npm install`, then `lint`/`typecheck`/`test`).
Deliberately no Docker in CI — the backend suite runs against an in-memory
SQLite DB and the frontend suite is pure Vitest/RTL, so neither needs
Postgres/Redis; plain pip/npm installs are faster and cheaper per run than
building the full compose stack.

## Environment variables

See `docker/.env.example` for the full list. The only one that must be real
for the AI Assistant to answer live is `GROQ_API_KEY` — everything else has
a working default for local/demo use. Never commit `docker/.env` (gitignored).

### Render demo database initialization

The Render blueprint sets `SEED_DEMO_DATA=true` on the API service.
After migrations, startup generates an offline synthetic demo dataset and
runs `scripts/seed_database.py` without `--reset`. Reference records are
added only when missing; existing inventory causes volume-data loading to
be skipped. Existing accounts and role permissions are not modified.

The offline generator uses a synthetic seasonal curve, not observed FluView
data. Local real-data generation still uses the existing pipeline by default.

For an existing Render service, deploy this code and set
`SEED_DEMO_DATA=true` in its environment (or sync the updated Blueprint).
Redeploy the API. Logs should show hospital/medicine counts and `Done.`.
Deploy the frontend too to receive UI changes. Set the flag to `false`
after successful initialization if demo seeding is no longer needed.
This loads demo data; it does not copy local accounts or database edits.

### Viewer full access

Migration `b42f6e81d903` adds `"*"` to the viewer role permissions on existing
and fresh databases. Render runs this migration automatically through
`alembic upgrade head` in its API startup script. All viewer accounts,
including new registrations, receive full administrative and network-wide
access. No additional environment variable is required.

Deploy the updated API and frontend, then log out and back in to refresh
cached user permissions. The migration preserves other role permissions.

Viewer access is also explicit in the backend and frontend authorization
helpers: both admin and viewer have full access even when an older database
returns empty permissions. Revoking the wildcard alone no longer restricts
viewers. Both the API and frontend must be deployed to apply this behavior.
