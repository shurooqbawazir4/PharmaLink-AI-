# MedCycle AI — Database Schema

PostgreSQL + the TimescaleDB extension. Single source of truth for the
schema is `backend/app/infrastructure/db/models.py`; migrations live in
`backend/alembic/versions/`. This document is the human-readable map of it.

## Conventions

- UUID primary keys (`uuid4`, generated client-side unless noted).
- `created_at`/`updated_at` timestamps on regular tables, DB-maintained via
  `server_default=func.now()` / `onupdate=func.now()`.
- Soft-delete via `is_active` where a row can be deactivated rather than
  deleted (hospitals, medicines, suppliers, roles-linked users).
- Every foreign key is indexed.
- Column types are dialect-agnostic (`sa.Uuid`, `JSON().with_variant(JSONB, "postgresql")`)
  so the same models run against SQLite in tests and Postgres everywhere
  else — see `docs/architecture.md`.

## TimescaleDB hypertables

Six append-only, time-indexed, high-volume tables are converted to
hypertables by the initial migration (`SELECT create_hypertable(...)`).
Each uses a **composite primary key** `(id, <time column>)` — TimescaleDB
requires the partitioning column be part of any primary key on the table.

| Table | Time column | Why it's a hypertable |
|---|---|---|
| `consumption` | `consumed_at` | The core demand-forecasting signal — one row per medicine unit used |
| `inventory_history` | `recorded_at` | Every stock-changing event (receipt, transfer, write-off, ...) |
| `weather` | `recorded_date` | Regional weather / flu-activity, a forecasting feature |
| `forecasts` | `generated_at` | One row per (hospital, medicine, horizon) forecast run |
| `expiry_risk` | `evaluated_at` | Point-in-time expiry-risk score per inventory batch |
| `audit_logs` | `created_at` | Append-only trail of every mutating API request |

Everything else is a normal relational table — lower write volume, needs
full relational integrity/joins more than time-bucketing.

## Tables

**roles** — RBAC roles. `permissions` is a flat JSONB string list (`["*"]`
for admin, `[]` for viewer) so new permissions don't require a migration.
Seeded by the initial migration: `admin`, `hospital_manager`, `pharmacist`,
`viewer` (see `_DEFAULT_ROLES` in `0001_initial_schema.py`).

**users** — `email` (unique), `hashed_password`, `role_id` → roles,
`hospital_id` → hospitals (nullable — not every user is hospital-scoped,
e.g. a network-wide admin).

**hospitals** — network node registry. `code` (unique), lat/lon (for the
Milestone D Mapbox view), `bed_capacity`, `occupancy_rate`, `type` (general/
specialty/teaching/clinic).

**suppliers** — `lead_time_days`, `reliability_score` — inputs to the
Milestone C procurement optimizer.

**medicines** — the catalogue. `atc_code` (nullable — not every synthetic/
generic entry will have one), `requires_refrigeration`, `is_controlled`.

**inventory** — one row per physical batch: `hospital_id` + `medicine_id` +
`batch_number`, `current_stock`, `safety_stock`, `expiry_date`,
`supplier_id`, `unit_cost_at_receipt`.

**inventory_history** *(hypertable)* — every stock-changing event:
`change_qty`, `reason` (receipt/consumption/transfer_out/transfer_in/
expiry_writeoff/adjustment).

**patients** — deliberately minimal and de-identified (`anonymized_ref`,
`age_band`, admission/discharge dates, `primary_diagnosis_code`) — this is
synthetic/aggregate admission context for demand forecasting, not a real
clinical record; MedCycle never stores real patient identity.

**consumption** *(hypertable)* — the demand signal: `quantity` of a
medicine used at a hospital, optionally linked to a patient/department.

**weather** *(hypertable)* — `region`, `temperature_c`, `humidity_pct`,
`flu_activity_index` — a demand-forecasting feature (see the AI Modules
spec's "seasonality / disease outbreaks" input).

**transfers** — `source_hospital_id` → `destination_hospital_id`,
`medicine_id`, `quantity`, `status` (proposed/approved/in_transit/
completed/cancelled), `transportation_cost`, `expiry_prevented_value` (the
sustainability-impact number surfaced on the dashboard).

**forecasts** *(hypertable)* — `horizon_days` (7/30/90), `model_used`
(chronos/lightgbm — the fallback path), `predicted_demand` with a
confidence interval.

**expiry_risk** *(hypertable)* — `probability_expires_before_use`,
`estimated_financial_loss`, `confidence_score` per inventory batch.

**purchase_orders** — `status` (recommended/approved/ordered/received/
cancelled), `recommended_by` (ai/manual) — AI-recommended orders start as
`recommended` and a human approves them, never auto-submitted.

**alerts** — `severity` (info/warning/critical), `type` (shortage_risk/
expiry_risk/low_stock/transfer_suggested), `is_resolved`.

**audit_logs** *(hypertable)* — `action` (HTTP method), `entity_type`/
`entity_id` (parsed from the URL path by `AuditLogMiddleware`),
`event_metadata` (JSONB — currently just `status_code`), `ip_address`.

## Migrations

```bash
# generate a new migration after changing models.py
docker compose -f docker/docker-compose.yml --env-file docker/.env run --rm backend \
  alembic revision --autogenerate -m "describe the change"

# apply
docker compose -f docker/docker-compose.yml --env-file docker/.env run --rm backend \
  alembic upgrade head
```

`alembic/env.py` reads `DATABASE_URL` from the same `Settings` the app
uses, so migrations and the running app can never point at different
databases by accident. Autogenerate diffs table/column/index shape but
**cannot** detect hypertable conversions or seed data — after
autogenerating, hand-check whether the new migration needs an addition to
`_HYPERTABLES` / a data-seeding step, following the pattern in
`0001_initial_schema.py`.
