# MedCycle AI — Backend

FastAPI service implementing MedCycle AI's Clean Architecture backend. See
[../docs/architecture.md](../docs/architecture.md) for the full layering
write-up and [../docs/database.md](../docs/database.md) for the schema.

Run via Docker from the repo root — see the top-level
[README.md](../README.md#getting-started). This package is not intended to
be installed/run outside a container in this milestone (no local Python is
assumed to be installed).

## Local layout

```
app/
  core/            config, security (JWT/bcrypt), DI wiring, exceptions, logging
  domain/          entities + repository interfaces (framework-free)
  application/      services — business logic
  infrastructure/    SQLAlchemy models + repository implementations
  api/               FastAPI routers + Pydantic schemas
alembic/           migrations
tests/
  unit/            service tests against in-memory fake repositories
  integration/      full-stack tests against an in-memory SQLite DB
```

## Common commands (run inside the container)

```bash
# tests
pytest -v

# lint / type-check
ruff check .
mypy .

# new migration after changing app/infrastructure/db/models.py
alembic revision --autogenerate -m "describe the change"
alembic upgrade head
```
