"""Domain layer: entities and repository interfaces, framework-free.

Nothing under `app/domain` may import FastAPI, SQLAlchemy, or any other
framework — that's what keeps business rules testable in isolation and
keeps the ORM/web framework swappable in principle.
"""
