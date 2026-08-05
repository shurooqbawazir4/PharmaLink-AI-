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
/data       real-signal ingestion + synthetic generation (see data/README.md)
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

Inventory, Transfers, Expiry, Procurement, and Notifications (Milestone B)
repeat this exact shape — Auth, Hospitals, and Medicines (Milestone A) are
the reference implementations. Forecast and Optimization (Milestone C)
will too. Three deliberate variations on the pattern showed up along the
way:

- **Transactional multi-write methods.** Most repository methods are
  single-row CRUD, but some actions are inherently "change stock *and*
  log why" as one atomic unit. `InventoryRepository.record_change` (and
  `.create(batch, reason=...)`) update `current_stock` and insert the
  matching `InventoryHistory` row in the same flush — every later
  "this action changes stock" flow (Transfers, Procurement receipt) calls
  through these two methods rather than writing history rows ad hoc.
- **Cross-module application-layer collaboration.** `TransferService`
  depends on `InventoryRepository` *and* `HospitalRepository` (not just
  `TransferRepository`); `ProcurementService` depends on `InventoryService`
  directly (reusing its `receive_stock` use case for `mark_received`
  rather than duplicating it). Domain layers stay isolated from each
  other; application layers are allowed to compose across modules — that's
  where real workflows (a transfer moves *inventory* between *hospitals*)
  actually live.
- **Analytics is the one exception to "service depends on a repository
  interface."** `AnalyticsService` takes an `AsyncSession` directly and
  runs cross-table aggregate queries — forcing KPI reporting through
  single-entity repositories would be the wrong abstraction. See
  `application/analytics/service.py`.

### The naive-now, ML-later pattern (Expiry, Procurement)

Expiry and Procurement each need a "smart" decision — is this batch going
to expire unused? should we reorder? — that's properly an ML/optimizer
job, but that job doesn't land until Milestone C. Both modules define a
`Protocol` for the decision (`domain/expiry/scorer.py::ExpiryRiskScorer`,
`domain/procurement/recommender.py::ProcurementRecommender`) and ship a
documented heuristic implementation behind it now
(`infrastructure/external/naive_expiry_scorer.py`,
`naive_procurement_recommender.py`), wired in via `core/di.py`
(`get_expiry_scorer`, `get_procurement_recommender`). Milestone C adds
`MLExpiryScorer` / the OR-Tools-informed recommender behind the *same*
interfaces and swaps the DI provider — nothing about the service, API, or
DB schema changes. This is the same shape as the Chronos→LightGBM
forecast fallback from the original design, applied a milestone early so
these modules are demoable now instead of blocked on the ML pipeline.

### Hospital-scoped RBAC

`require_role(...)` (Milestone A) is network-wide — any `pharmacist` can
touch the shared Medicines catalogue, which is correct, since it isn't
hospital-specific. Inventory/Transfers/Procurement *are* hospital-specific,
so `api/v1/deps.py::require_own_hospital_or_admin(user, hospital_id)`
adds the second check: an `admin` always passes, anyone else must have
`user.hospital_id == hospital_id`. It's a plain function, not a `Depends`
factory like `require_role`, because the target hospital id comes from
different places per route — a path param for hospital-scoped list/detail
routes, a request-body field for actions like "propose transfer" (source/
destination are both body fields) — so each router calls it explicitly
with whichever hospital id is actually in scope for that request.

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

## Data pipeline separation

`/data/pipeline` (real-signal ingestion) and `/data/synthetic` (generation)
run in their own minimal Docker image (`docker/Dockerfile.pipeline` —
pandas/numpy/requests), not inside `/backend`, for the same reason `/ml`
will get its own package: keeps the API image free of data-science
dependencies. `backend/scripts/seed_database.py` is the one bridge — it
runs *inside* the backend container (real DB connection, real ORM models)
and reads the pipeline's CSV output with the stdlib `csv` module rather
than pandas, so `/backend` still never gains a pandas dependency. See
`data/README.md` for the full pipeline and why OpenPrescribing (part of
the original plan) was dropped for FluView-only after live testing found
it now blocks automated access entirely.

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
