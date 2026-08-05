# MedCycle AI — Architecture

## Overview

MedCycle AI is a medication intelligence platform: it forecasts demand,
flags expiry and shortage risk, recommends inventory transfers and
procurement, and explains those recommendations through an LLM assistant.
The backend follows **Clean Architecture** with **Domain-Driven Design**
boundaries, a **Repository Pattern**, an explicit **Service Layer**, and
**Dependency Injection** via FastAPI's native `Depends` graph — deliberately
without a DI framework.

```
/frontend   Next.js 15 dashboard (Milestone D)
/backend    FastAPI service — Clean Architecture (this document)
/ml         LightGBM/CatBoost/Chronos/OR-Tools package (Milestone C)
/data       raw/, processed/, synthetic/ data pipeline (Milestone B)
/docs       this directory
/docker     docker-compose.yml, Dockerfiles, .env.example
/scripts    dev bootstrap scripts
/tests      cross-cutting integration tests (backend also has its own)
```

## Backend layering

```
backend/app/
  core/            cross-cutting: config, security, DI wiring, exceptions, logging
  domain/          entities + repository interfaces — framework-free
  application/      services — business logic, depends only on domain interfaces
  infrastructure/    SQLAlchemy models + repository implementations, external adapters
  api/               FastAPI routers, Pydantic schemas, HTTP-layer auth deps
```

**Dependency direction is one-way inward:** `api` → `application` →
`domain`. `infrastructure` implements the interfaces `domain` declares, but
`domain` never imports `infrastructure`. Concretely:

- **`domain/<module>/entities.py`** — a plain `@dataclass`, zero SQLAlchemy
  or FastAPI imports. e.g. `domain/medicines/entities.py::Medicine`.
- **`domain/<module>/repository.py`** — a `Protocol` describing the
  persistence contract (`get`, `list`, `create`, `update`, ...). Nothing
  about *how* data is stored, only *what* operations exist.
- **`domain/<module>/exceptions.py`** — thin subclasses of the generic
  `core.exceptions.NotFoundError` / `AlreadyExistsError` / etc., giving
  each module its own named errors (`HospitalNotFoundError`) without
  duplicating the HTTP-mapping logic (that lives once, in `core/exceptions.py`).
- **`application/<module>/service.py`** — the use-case layer. Takes a
  repository *interface* in its constructor, holds business rules (e.g.
  "hospital codes are unique", "unit cost must be positive"), and is
  completely unaware of SQLAlchemy or HTTP.
- **`infrastructure/db/models.py`** — the single source of truth for the
  DB schema (see `docs/database.md`). ORM classes are suffixed `Model`
  (`HospitalModel`) to stay visually distinct from the domain entity of the
  same concept (`Hospital`).
- **`infrastructure/db/repositories/<module>_repository.py`** —
  `SQLAlchemy<Module>Repository`, implementing the domain `Protocol`,
  translating ORM rows ↔ domain entities via a `_to_entity` staticmethod.
- **`api/v1/schemas/<module>.py`** — Pydantic v2 request/response models.
  The *only* layer allowed to shape HTTP JSON.
- **`api/v1/routers/<module>.py`** — thin: parse request, call a service
  method, translate the returned domain entity into a response schema.

Every future module (Inventory, Transfers, Forecast, Optimization, Expiry,
Procurement, Analytics, Notifications) repeats this exact five-file shape —
Auth, Hospitals, and Medicines are the reference implementations.

## Dependency injection

`core/di.py` is a small chain of provider functions composed via
`Depends`, not a DI container:

```python
def get_hospital_repository(db: DbSession) -> HospitalRepository:
    return SQLAlchemyHospitalRepository(db)

def get_hospital_service(
    repo: Annotated[HospitalRepository, Depends(get_hospital_repository)],
) -> HospitalService:
    return HospitalService(repo)
```

Routers only ever depend on `get_<module>_service`. Tests override
`app.dependency_overrides[get_db]` with an in-memory SQLite session
(`tests/conftest.py`) — no network, no Docker needed for the unit/
integration suite. See `tests/unit/fakes.py` for repository-level fakes
used to unit-test services with zero database at all.

## Auth, RBAC, and audit logging

- **JWT**: `core/security.py` issues/decodes access (short-lived) and
  refresh (long-lived) tokens — framework-free, unit-testable in isolation.
- **RBAC**: `roles.permissions` is a flat JSONB string list (`["*"]` for
  admin, `[]` for viewer). `api/v1/deps.py::require_role("admin", ...)` is
  a dependency factory added per-route (`dependencies=[Depends(require_role(...))]`)
  — declarative at the router, not scattered through services.
- **Audit logging**: `core/logging.py::AuditLogMiddleware` writes an
  `audit_logs` row for every successful mutating request (POST/PUT/PATCH/
  DELETE), so no module can forget to audit a change. Because middleware
  sits outside the `Depends` graph, it reads its DB session factory from
  `app.state.audit_session_factory` (set once in `main.create_app`, and
  swapped by tests) rather than importing the production session factory
  directly — keeping it just as overridable as everything else.

## `/backend` ↔ `/ml` boundary (Milestone C)

`/ml` is a plain, installable Python package with no FastAPI/SQLAlchemy
imports, exposing typed functions (e.g.
`ml.forecasting.forecast(history: pd.DataFrame, horizon: int) -> ForecastResult`).
The backend's `infrastructure/external/ml_client.py` adapts domain data
into what `/ml` expects and back — called directly for fast synchronous
paths (single expiry-risk score) and from Celery tasks for batch jobs
(nightly forecast refresh). Model fallback (Chronos → LightGBM) lives
*inside* `/ml`, invisible to the backend.

## Why these tradeoffs

- **No DI framework** — FastAPI's `Depends` graph already gives explicit,
  typed, overridable wiring; a container would add indirection without
  adding capability at this scale.
- **Dataclasses, not Pydantic, for domain entities** — keeps `domain/`
  genuinely framework-free per Clean Architecture's dependency rule, even
  though Pydantic is used everywhere else.
- **Dialect-agnostic column types** (`sa.Uuid`, `JSON().with_variant(JSONB, "postgresql")`)
  instead of `postgresql.UUID`/`JSONB` directly — the same `models.py` runs
  against SQLite in tests and Postgres/TimescaleDB in every other
  environment, so there's no second set of test-only models to drift.
