# MedCycle AI

**AI-powered medication intelligence platform.** Predicts medication demand,
flags expiry and shortage risk, recommends inventory transfers and
procurement across a hospital network, and explains every recommendation
through an LLM assistant — built to reduce medicine waste and prevent
stockouts.

> Status: **Milestone A** complete — architecture, database schema, and a
> production-shaped backend foundation (Auth, Hospitals, Medicines) are
> live and tested. See [Roadmap](#roadmap) below.

## Why

Hospitals routinely sit on both shortages and surplus at the same time —
one site is out of insulin while another three towns over is about to
write off a batch to expiry. MedCycle AI forecasts demand per hospital per
medicine, scores expiry/shortage risk, and recommends *specific* transfers
and purchase orders (with quantities, costs, and the waste/CO₂ they
prevent) rather than generic dashboards.

## Tech stack

| Layer | Stack |
|---|---|
| Frontend | Next.js 15, React 19, TypeScript, TailwindCSS, shadcn/ui, Framer Motion, TanStack Query, Recharts, Mapbox *(Milestone D)* |
| Backend | FastAPI, Python 3.12, Pydantic v2, SQLAlchemy 2.0 (async), Alembic, Celery, Redis |
| Database | PostgreSQL + TimescaleDB |
| ML | PyTorch, LightGBM, CatBoost, XGBoost, scikit-learn, Chronos, OR-Tools *(Milestone C)* |
| LLM | Anthropic / OpenAI, provider-agnostic — explanation only, never prediction *(Milestone C)* |
| Deployment | Docker, Docker Compose, GitHub Actions |

## Architecture

Clean Architecture + DDD: `domain` (entities, repository interfaces) →
`application` (services, business rules) → `infrastructure` (SQLAlchemy) →
`api` (FastAPI routers, Pydantic schemas), wired with FastAPI's native
`Depends` graph instead of a DI framework. Full write-up:
[docs/architecture.md](docs/architecture.md). Schema reference:
[docs/database.md](docs/database.md).

```
/frontend   Next.js dashboard                  (Milestone D)
/backend    FastAPI service — Clean Architecture
/ml         Forecasting / optimization package  (Milestone C)
/data       raw/, processed/, synthetic/ pipeline (Milestone B)
/docs       architecture, database, API, deployment, ML docs
/docker     docker-compose.yml, Dockerfiles, .env.example
/scripts    dev bootstrap scripts
/tests      cross-cutting integration tests
```

## Getting started

Requires Docker + Docker Compose. No local Node/Python install needed —
everything runs in containers.

```bash
# macOS/Linux
./scripts/dev_up.sh

# Windows
.\scripts\dev_up.ps1
```

This copies `docker/.env.example` → `docker/.env` on first run, builds the
backend image, starts Postgres/TimescaleDB + Redis, applies migrations
(creating all tables, converting the 6 time-series tables to TimescaleDB
hypertables, and seeding the 4 default RBAC roles), then starts the API.

- **API docs (Swagger)**: http://localhost:8000/docs
- **Health check**: http://localhost:8000/api/v1/health

Try it:

```bash
curl -X POST http://localhost:8000/api/v1/auth/register \
  -H "Content-Type: application/json" \
  -d '{"email":"you@example.com","password":"supersecret123","full_name":"Your Name"}'

curl -X POST http://localhost:8000/api/v1/auth/login \
  -H "Content-Type: application/json" \
  -d '{"email":"you@example.com","password":"supersecret123"}'
# -> use the returned access_token as: Authorization: Bearer <token>
```

New users register as `viewer` by default; promote a user's role directly
in the `users`/`roles` tables to exercise the `hospital_manager`/
`pharmacist`/`admin` RBAC-gated routes (a proper admin-promotion endpoint
lands with the rest of the Auth module's write paths in Milestone B).

### Running tests

```bash
docker compose -f docker/docker-compose.yml --env-file docker/.env run --rm --no-deps backend pytest -v
```

The suite runs against an in-memory SQLite DB (no live Postgres needed) —
see `backend/tests/conftest.py`.

## Roadmap

| Milestone | Scope | Status |
|---|---|---|
| A | Architecture, DB schema, Docker skeleton, Auth/Hospitals/Medicines (reference modules) | ✅ Done |
| B | Inventory, Transfers, Expiry, Procurement, Analytics, Notifications + real-data ingestion (NHS OpenPrescribing, CDC FluView) + synthetic layer | Next |
| C | Forecasting (LightGBM → Chronos), expiry/shortage models, OR-Tools optimizer, LLM explanation layer | Planned |
| D | Next.js dashboard: all 10 pages, charts, hospital map, AI Assistant chat | Planned |
| E | Full docker-compose (+ frontend, nginx), GitHub Actions CI, full test/doc coverage | Planned |

## Documentation

- [Architecture](docs/architecture.md)
- [Database schema](docs/database.md)
- API docs: auto-generated OpenAPI at `/docs` once the backend is running
