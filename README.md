# MedCycle AI

**AI-powered medication intelligence platform.** Predicts medication demand,
flags expiry and shortage risk, recommends inventory transfers and
procurement across a hospital network, and explains every recommendation
through an LLM assistant — built to reduce medicine waste and prevent
stockouts.

> Status: **Milestone D** complete — the full backend (Auth, Hospitals,
> Medicines, Inventory, Transfers, Expiry, Procurement, Analytics,
> Notifications), a real-signal + synthetic data pipeline, a seeded demo
> dataset, a trained LightGBM demand forecaster, an OR-Tools network
> transfer optimizer, a Groq-backed LLM explanation/assistant layer, and a
> Next.js dashboard covering all 10 spec pages are live and tested. See
> [Roadmap](#roadmap) below.

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
| Frontend | Next.js 15, React 19, TypeScript, TailwindCSS, shadcn/ui, Framer Motion, TanStack Query, React Hook Form/Zod, Recharts, MapLibre GL |
| Backend | FastAPI, Python 3.12, Pydantic v2, SQLAlchemy 2.0 (async), Alembic, Celery, Redis |
| Database | PostgreSQL + TimescaleDB |
| ML | LightGBM (quantile demand forecasting), OR-Tools (network transfer optimization), scikit-learn, pandas. Chronos is a documented, not-yet-implemented swap point — see [docs/architecture.md](docs/architecture.md) |
| LLM | Groq (`openai/gpt-oss-120b`, OpenAI-compatible client) — explanation only, never prediction |
| Data pipeline | pandas, numpy, requests — own image, kept out of the API (see below) |
| Deployment | Docker, Docker Compose, GitHub Actions |

## Architecture

Clean Architecture + DDD: `domain` (entities, repository interfaces) →
`application` (services, business rules) → `infrastructure` (SQLAlchemy) →
`api` (FastAPI routers, Pydantic schemas), wired with FastAPI's native
`Depends` graph instead of a DI framework. Full write-up:
[docs/architecture.md](docs/architecture.md). Schema reference:
[docs/database.md](docs/database.md). Data pipeline: [data/README.md](data/README.md).

```
/frontend   Next.js dashboard — all 10 spec pages
/backend    FastAPI service — Clean Architecture
/ml         LightGBM forecaster + OR-Tools transfer optimizer
/data       Real-signal ingestion + synthetic generation
/docs       architecture, database, API, deployment, ML docs
/docker     docker-compose.yml, Dockerfiles, .env.example
/scripts    dev bootstrap scripts
/tests      cross-cutting integration tests
```

Backend modules live: **Auth** (JWT + RBAC, incl. admin role/hospital
assignment), **Hospitals**, **Medicines**, **Inventory** (batch tracking,
FEFO), **Transfers** (propose → approve → complete, moves real stock,
manual or AI-recommended), **Expiry** and **Procurement** (heuristic risk
scoring/reorder logic, now fed a trained forecast signal when one exists —
see [docs/architecture.md](docs/architecture.md)), **Forecast** (LightGBM
quantile demand forecasting, trained on seeded consumption + weather
history), **Optimization** (OR-Tools network transfer solver, admin-only —
proposes and raises alerts for real transfers), **Assistant** (Groq LLM:
explains any transfer/purchase-order recommendation in plain language,
answers freeform ops questions grounded in live KPIs/alerts — never
predicts a number itself), **Analytics** (KPI reporting), **Notifications**
(alerts, raised internally by Inventory/Expiry/Optimization).

The frontend covers the spec's 10 dashboard pages — Dashboard, Medicines,
Hospitals (+ a per-hospital inventory/expiry drill-down), Forecast,
Optimization, Alerts, Procurement, Analytics, Sustainability, AI Assistant —
plus Login/Register, dark mode, and a hospital-network map. Full design
writeup: [docs/architecture.md](docs/architecture.md#frontend-milestone-d).

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
backend + frontend images, starts Postgres/TimescaleDB + Redis, applies
migrations (creating all tables, converting the 6 time-series tables to
TimescaleDB hypertables, and seeding the 4 default RBAC roles), then starts
the API, the Celery worker, and the Next.js dev server.

- **Dashboard**: http://localhost:3000 (register, then bootstrap yourself to
  `admin` via the SQL step below, then log in)
- **API docs (Swagger)**: http://localhost:8000/docs
- **Health check**: http://localhost:8000/api/v1/health

### Seed a realistic demo dataset

8 hospitals, 13 medicines, 4 suppliers, ~160 inventory batches (with
deliberately planted near-expiry and understocked positions — see
[data/README.md](data/README.md#narrative-seeding--documented-not-hidden)),
~1,000 patients, ~18,000 consumption records, and real FluView-anchored
seasonality:

```bash
docker compose -f docker/docker-compose.yml --env-file docker/.env build pipeline
docker compose -f docker/docker-compose.yml --env-file docker/.env run --rm pipeline python pipeline/fetch_fluview.py
docker compose -f docker/docker-compose.yml --env-file docker/.env run --rm pipeline python pipeline/build_processed.py
docker compose -f docker/docker-compose.yml --env-file docker/.env run --rm pipeline python synthetic/generate.py
docker compose -f docker/docker-compose.yml --env-file docker/.env run --rm backend python scripts/seed_database.py
```

### Try it

```bash
curl -X POST http://localhost:8000/api/v1/auth/register \
  -H "Content-Type: application/json" \
  -d '{"email":"you@example.com","password":"supersecret123","full_name":"Your Name"}'

curl -X POST http://localhost:8000/api/v1/auth/login \
  -H "Content-Type: application/json" \
  -d '{"email":"you@example.com","password":"supersecret123"}'
# -> use the returned access_token as: Authorization: Bearer <token>
```

New users register as `viewer`. To exercise `hospital_manager`/
`pharmacist`/`admin` RBAC-gated routes, an existing `admin` promotes a user
via `PATCH /api/v1/auth/users/{id}` (`{"role_name": "pharmacist",
"hospital_id": "<uuid>"}`) — but the very first admin has no admin to
promote them, so that one bootstrap has to happen directly against the DB
(exactly what `scripts/seed_database.py` and the test suite's
`admin_headers` fixture both do):

```sql
UPDATE users SET role_id = (SELECT id FROM roles WHERE name = 'admin') WHERE email = 'you@example.com';
```

### Try the AI features

Every action below is also available from the dashboard (Forecast,
Optimization, and AI Assistant pages) — these curl examples exercise the
same endpoints directly. Requires `GROQ_API_KEY` set in `docker/.env` for
the assistant endpoints (get a free key at
[console.groq.com](https://console.groq.com)); forecast and optimization
need no external key. Use the seeded demo dataset above first — the
forecaster needs consumption history to train on, and the optimizer needs a
real surplus/deficit pair to find.

```bash
# Train (first call only, lazily) + generate a demand forecast
curl -X POST "http://localhost:8000/api/v1/forecasts/generate/<hospital_id>/<medicine_id>?horizon_days=30" \
  -H "Authorization: Bearer <token>"

# Run the network transfer optimizer for one medicine (admin only)
curl -X POST http://localhost:8000/api/v1/optimization/transfers/<medicine_id> \
  -H "Authorization: Bearer <admin_token>"

# Ask the assistant a freeform question, grounded in live KPIs/alerts
curl -X POST http://localhost:8000/api/v1/assistant/chat \
  -H "Authorization: Bearer <token>" -H "Content-Type: application/json" \
  -d '{"question": "What is my highest-risk medicine right now?"}'

# Ask it to explain one specific recommendation, in plain language
curl http://localhost:8000/api/v1/assistant/explain/transfer/<transfer_id> \
  -H "Authorization: Bearer <token>"
```

### Running tests

```bash
docker compose -f docker/docker-compose.yml --env-file docker/.env run --rm --no-deps backend pytest -v
docker compose -f docker/docker-compose.yml --env-file docker/.env run --rm --no-deps frontend npm run lint
docker compose -f docker/docker-compose.yml --env-file docker/.env run --rm --no-deps frontend npm run typecheck
docker compose -f docker/docker-compose.yml --env-file docker/.env run --rm --no-deps frontend npm test
```

The backend suite runs against an in-memory SQLite DB (no live Postgres
needed) — see `backend/tests/conftest.py`. The frontend suite is Vitest +
React Testing Library — see `frontend/tests/` and
[docs/architecture.md](docs/architecture.md#frontend-milestone-d) for its
scope.

## Roadmap

| Milestone | Scope | Status |
|---|---|---|
| A | Architecture, DB schema, Docker skeleton, Auth/Hospitals/Medicines (reference modules) | ✅ Done |
| B | Inventory, Transfers, Expiry, Procurement, Analytics, Notifications + real-signal (FluView) + synthetic data pipeline | ✅ Done |
| C | LightGBM demand forecaster, OR-Tools transfer optimizer, forecast-fed Expiry/Procurement, Groq LLM explanation/assistant layer, Celery wiring | ✅ Done |
| D | Next.js dashboard: all 10 pages, charts, MapLibre hospital map, AI Assistant chat | ✅ Done |
| E | Production frontend build + nginx, GitHub Actions CI, celery beat, full test/doc coverage | Next |

## Documentation

- [Architecture](docs/architecture.md)
- [Database schema](docs/database.md)
- [Data pipeline](data/README.md)
- API docs: auto-generated OpenAPI at `/docs` once the backend is running
