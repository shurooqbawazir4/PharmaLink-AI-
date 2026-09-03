# PharmaLink AI — Architecture

## Overview

PharmaLink AI is a medication intelligence platform: it forecasts demand,
flags expiry and shortage risk, recommends inventory transfers and
procurement, and explains those recommendations through an LLM assistant.
The backend follows **Clean Architecture** with **Domain-Driven Design**
boundaries, a **Repository Pattern**, an explicit **Service Layer**, and
**Dependency Injection** via FastAPI's native `Depends` graph — deliberately
without a DI framework.

```
/frontend   Next.js 15 dashboard — all 10 spec pages (see §Frontend below)
/backend    FastAPI service — Clean Architecture (this document)
/ml         LightGBM forecaster + OR-Tools transfer optimizer (Milestone C)
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

### The naive-now, forecast-fed-later pattern (Expiry, Procurement)

Expiry and Procurement each need a "smart" decision — is this batch going
to expire unused? should we reorder? Milestone B shipped both behind a
`Protocol` (`domain/expiry/scorer.py::ExpiryRiskScorer`,
`domain/procurement/recommender.py::ProcurementRecommender`) with a
documented heuristic implementation
(`infrastructure/external/naive_expiry_scorer.py`,
`naive_procurement_recommender.py`), wired in via `core/di.py`
(`get_expiry_scorer`, `get_procurement_recommender`).

Milestone C does **not** replace these with trained classifiers — there's
no labeled outcome data (no seeded batch has ever actually been written
off) to train "will this expire unused?" against, and manufacturing a
synthetic labeled dataset just to justify a classifier would be worse than
being honest about the gap. Instead, the real upgrade is one layer up:
`ExpiryService` and `ProcurementService` now take an optional
`ForecastService` dependency and ask it for a trained, seasonality-aware
daily-consumption rate first (`_daily_consumption_signal()` in each
service), falling back to `InventoryRepository.average_daily_consumption`
— the same Milestone B historical-average signal — when no forecast
exists yet for that hospital/medicine pair. Same scorer/recommender
`Protocol`s, same naive implementations, just fed a better number once one
is available. The `ExpiryRiskScorer`/`ProcurementRecommender` interfaces
remain the real swap point for a future trained classifier, should labeled
outcome data ever exist.

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

`/ml` is a plain, installable Python package (own `pyproject.toml`) with
no FastAPI/SQLAlchemy imports — `forecasting/` and `optimization/` are
top-level packages (not `ml.forecasting`; the dotted-path in the original
design doc was aspirational, documented as a deliberate deviation in
`ml_client.py`'s docstring). It's `pip install -e`'d into the backend
image (`docker/Dockerfile.backend`), so the backend imports it directly —
`infrastructure/external/ml_client.py::MLForecastClient` is the sole
adapter, translating domain rows ↔ pandas DataFrames and back into a
`ForecastResult`. The forecaster trains lazily, once per process
(`@lru_cache` singleton in `core/di.py::get_ml_forecast_client`).

- **Forecasting** (`ml/forecasting/`): `interface.py` defines the
  `Forecaster` `Protocol` (`fit`, `predict`) so a different model is a DI
  swap, not a rewrite. `lightgbm_forecaster.py::LightGBMForecaster` is the
  real, load-bearing implementation — quantile regression (α = 0.1/0.5/0.9)
  over lag/rolling-window/day-of-week/flu-index features
  (`features.py`), predicting a daily rate scaled by `horizon_days` (a
  documented simplification vs. full recursive multi-step forecasting).
  `chronos_forecaster.py::ChronosForecaster` is a real, present stub whose
  `fit`/`predict` raise `NotImplementedError` with the reasoning inline:
  Chronos needs `torch`+`transformers` (multiple GB of CPU-only deps) for
  worse-fitting results than LightGBM on this feature-rich tabular data —
  the swap point from the original spec is real code, not just asserted.
- **Optimization** (`ml/optimization/transfer_optimizer.py`): the network
  transfer problem is a classic transportation LP (surplus hospitals →
  deficit hospitals), solved with OR-Tools' `pywraplp` GLOP solver —
  maximize total quantity moved, with distance as a tiny tie-breaker
  coefficient. No MIP/integer constraints needed: transportation-problem
  LPs with integer supply/demand have integer-optimal solutions by total
  unimodularity. `solve_network_transfers()` is pure — it takes/returns
  plain dataclasses (`HospitalState`, `TransferRecommendation`), no DB or
  domain-entity awareness, so it's unit-testable with zero backend
  imports.

`application/optimization/service.py::OptimizationService.optimize_network`
is the backend-side caller: builds `HospitalState`s from
`InventoryRepository`+`HospitalRepository`+`ForecastService`, runs the
solver, then reuses `TransferService.propose(..., recommended_by=AI)` for
each recommendation (not a new transfer-creation path) and raises a
`transfer_suggested` alert via `NotificationService`. Restricted to
`admin` only (`require_role`, not hospital-scoped) since one run spans the
whole network by design.

## LLM explanation layer (Milestone C)

The LLM is strictly **explanation-only** — it never predicts a number,
only narrates numbers the deterministic pipeline already computed — and
the code enforces that by giving it nothing else to do: system prompts
name the constraint explicitly, and every prompt is built from real
already-computed fields (never blank-slate reasoning).

- **Provider**: `infrastructure/external/llm/provider.py::LLMProvider` is
  a `Protocol` (`async def complete(system_prompt, messages) -> str`);
  `groq_provider.py::GroqProvider` implements it against Groq's
  OpenAI-compatible endpoint (`openai.AsyncOpenAI(base_url=...)`, model
  `openai/gpt-oss-120b`) — swappable to a different OpenAI-compatible
  provider by changing `core/config.py` settings and the DI provider,
  nothing else. Tests inject a `FakeLLMProvider` (canned responses); no
  automated test makes a live Groq call.
- **`application/assistant/service.py::AssistantService`** has two
  capabilities: `explain_transfer`/`explain_purchase_order` (grounds a
  prompt in one already-proposed recommendation's real fields) and `chat`
  (answers freeform questions like "what's my highest-risk medicine?"
  against a context snapshot — KPIs, high-risk expiry batches, unresolved
  alerts — built via `AnalyticsService`/`ExpiryService`/
  `NotificationService`). It also depends on `HospitalService` and
  `MedicineService` for one specific reason: **prompts use hospital and
  medicine *names*, never raw UUIDs** — resolved before the prompt is
  built, matching the spec's own example phrasing ("Transferring 420
  insulin units from Hospital A to Hospital B").
- Non-admin callers of `POST /assistant/chat` are always scoped to their
  own hospital regardless of what `hospital_id` they pass in the request
  body — enforced at the router, same pattern as
  `require_own_hospital_or_admin` elsewhere.

## Celery (Milestone C)

`core/celery_app.py` wires a `Celery` app (Redis as both broker and result
backend). Tasks in `infrastructure/tasks/` (`forecast_tasks.py`,
`optimization_tasks.py`) are thin wrappers: each opens its own
`AsyncSessionLocal()` and manually constructs the same
repositories/services the synchronous HTTP endpoints use via `Depends` —
Celery tasks can't participate in FastAPI's request-scoped DI graph, so
they build an equivalent one by hand and call the *same* application-layer
methods (`ForecastService.generate`, `OptimizationService.optimize_network`)
rather than duplicating any business logic. `celery_worker` and
`celery_beat` services run alongside `backend` in `docker-compose.yml`;
`celery_app.conf.beat_schedule` (Milestone E) runs a nightly forecast
refresh followed by a network optimization pass, on top of the same tasks
still being triggerable on demand (`docker compose run --rm backend
celery -A app.core.celery_app call optimization.run_network`).

## Deployment (Milestone E)

`docker-compose.prod.yml` overlays the dev compose file: a standalone
Next.js frontend build (no bind mount) fronted by nginx as the single
`:80` entry point, instead of the dev file's hot-reload frontend with its
own published port. GitHub Actions CI (`.github/workflows/ci.yml`) runs
backend (`ruff`/`mypy`/`pytest`) and frontend (`lint`/`typecheck`/`test`)
on every push/PR without Docker — both suites already run against
in-memory/mocked dependencies (SQLite, Vitest/RTL), so plain pip/npm
installs are enough. Full writeup, including a `!reset`-tag gotcha in the
compose overlay worth knowing before extending it: `docs/deployment.md`.

## Frontend (Milestone D)

Next.js 15 (App Router) + React 19 + TypeScript + TailwindCSS + shadcn/ui +
Framer Motion + TanStack Query + React Hook Form/Zod + Recharts. Runs as its
own dev-mode Docker service (`docker/Dockerfile.frontend`, bind-mounted
source, `next dev`) — pulled forward from Milestone E's originally-planned
integration pass, since the standing "Docker only, no local Node" constraint
means the user can't run or see this milestone's work without it; the
*production* multi-stage build + nginx reverse proxy remain E's job.

**Module boundaries mirror the backend's, one `features/<module>/` folder per
backend module** (Auth, Hospitals, Medicines, Inventory, Transfers, Forecast,
Optimization, Expiry, Procurement, Analytics, Notifications, Assistant) — each
holds an `api.ts` (typed fetch calls) and `hooks.ts` (TanStack Query wrappers).
Page components under `app/(app)/` compose these, never call `fetch` directly.

- **Hand-written API client, not OpenAPI-codegen'd.** `lib/types/*.ts` mirrors
  `backend/app/api/v1/schemas/*.py` 1:1 by hand — kept lean deliberately,
  matching the backend's "no framework where a plain function suffices" ethos
  from `core/di.py`. `lib/api-client.ts::apiFetch` is the one place that knows
  about the `Authorization` header and retry logic: a single-flight
  refresh-and-retry-once on a 401 (concurrent 401s across multiple in-flight
  queries all await the same refresh call), logging out only if the refresh
  token itself is rejected.
- **Auth token storage: `localStorage` via a Zustand store (`lib/auth-store.ts`),
  not httpOnly cookies.** The backend issues tokens as a JSON body
  (`TokenResponse`), not `Set-Cookie`; matching that contract without a backend
  change means client-side storage. This is XSS-exposed compared to httpOnly
  cookies — an accepted MVP tradeoff, flagged here as a Milestone E hardening
  candidate, not silently glossed over.
- **RBAC is UX-only on the frontend.** `lib/rbac.ts` mirrors
  `api/v1/deps.py`'s `require_role`/`require_own_hospital_or_admin` exactly
  (same role lists, same admin-always-passes rule) to decide what to
  hide/disable, and `hooks/useHospitalScope.ts` mirrors
  `require_own_hospital_or_admin`'s scoping (non-admins locked to their own
  hospital; admins pick any hospital or network-wide). The backend remains the
  actual enforcement boundary — every one of these checks is duplicated
  server-side and would reject the request even if the UI hid the button.
- **Map: MapLibre GL, not Mapbox GL JS** (`components/map/HospitalMap.tsx`,
  reused by the Hospitals and Optimization pages for the network map and the
  AI-recommended-transfer arcs respectively) — MapLibre is Mapbox GL's
  open-source fork, functionally equivalent for this use case, chosen
  specifically to avoid a second external API-key dependency alongside Groq.
- **Page-to-spec mapping isn't 1:1 with backend modules.** The spec's 10
  dashboard pages don't include Inventory or Expiry as their own pages —
  those are hospital-scoped, so they live inside a **hospital drill-down**
  on the Hospitals page (`features/hospitals/components/HospitalDrilldown.tsx`)
  rather than getting invented pages of their own. Analytics/Sustainability
  split the spec's 7 "Analytics" KPIs between an operational/financial page
  (Analytics) and an environmental/redistribution-story page
  (Sustainability) — see `docs/database.md`'s "Derived KPI fields" section
  for the real numbers backing the latter.
- **Testing scope**: Vitest + React Testing Library covering the API client
  (including the 401-refresh-retry path), the auth store, the RBAC helpers,
  and a handful of representative components (`frontend/tests/`) — not full
  per-page coverage, and no browser e2e this milestone. Consistent with the
  backend's own choice not to unit-test `AnalyticsService` directly
  (Milestone B/C), relying on integration/live coverage instead.

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
