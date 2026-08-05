"""Structured logging setup + the audit-log HTTP middleware.

The middleware — not per-service decorators — is what writes `audit_logs`
rows, so no module can forget to audit a mutation (see plan §6). It opens
its own short-lived DB session rather than reusing the request's, so a
rollback in the route's own session (e.g. a 422) doesn't also roll back the
audit entry, and vice versa.
"""

from __future__ import annotations

import logging
import sys
from datetime import UTC, datetime
from uuid import UUID

from starlette.middleware.base import BaseHTTPMiddleware, RequestResponseEndpoint
from starlette.requests import Request
from starlette.responses import Response

from app.core.config import settings

_MUTATING_METHODS = {"POST", "PUT", "PATCH", "DELETE"}


def setup_logging() -> None:
    """Configure root logging once, at app startup."""
    logging.basicConfig(
        level=logging.DEBUG if settings.debug else logging.INFO,
        format="%(asctime)s %(levelname)-8s %(name)s | %(message)s",
        stream=sys.stdout,
    )
    # Quiet down noisy third-party loggers unless we're actively debugging.
    noisy_level = logging.INFO if settings.debug else logging.WARNING
    for noisy_logger in ("sqlalchemy.engine", "httpx"):
        logging.getLogger(noisy_logger).setLevel(noisy_level)


class AuditLogMiddleware(BaseHTTPMiddleware):
    """Writes an `audit_logs` row for every successful mutating request.

    `entity_type`/`entity_id` are derived from the URL path (e.g.
    `/api/v1/hospitals/{id}` -> entity_type="hospitals", entity_id="{id}")
    — a heuristic that holds for this API's REST-resource routing
    convention and avoids every router having to declare it explicitly.
    """

    async def dispatch(self, request: Request, call_next: RequestResponseEndpoint) -> Response:
        response = await call_next(request)

        if request.method in _MUTATING_METHODS and response.status_code < 400:
            await self._record(request, response)

        return response

    async def _record(self, request: Request, response: Response) -> None:
        # Imported lazily to avoid a hard import-time dependency between
        # core/ and infrastructure/db/ — this is the one deliberate
        # exception to that layering, isolated to this middleware.
        from app.infrastructure.db.models import AuditLogModel

        # Read from `app.state` rather than importing the production
        # `AsyncSessionLocal` directly — middleware sits outside FastAPI's
        # `Depends` graph, so `app.dependency_overrides` can't reach it.
        # Routing through `app.state` (set once in `main.create_app`, and
        # swappable by tests) keeps this middleware's DB access overridable
        # like every other data access path in the app.
        session_factory = request.app.state.audit_session_factory

        entity_type, entity_id = self._parse_entity(request.url.path)
        user_id: UUID | None = getattr(request.state, "user_id", None)

        try:
            async with session_factory() as session:
                session.add(
                    AuditLogModel(
                        created_at=datetime.now(UTC),
                        user_id=user_id,
                        action=request.method,
                        entity_type=entity_type,
                        entity_id=entity_id,
                        event_metadata={"status_code": response.status_code},
                        ip_address=request.client.host if request.client else None,
                    )
                )
                await session.commit()
        except Exception:  # noqa: BLE001 — audit logging must never break the request.
            logging.getLogger(__name__).exception("Failed to write audit log entry")

    @staticmethod
    def _parse_entity(path: str) -> tuple[str, str | None]:
        prefix = settings.api_v1_prefix
        relative = path[len(prefix) :] if path.startswith(prefix) else path
        segments = [segment for segment in relative.split("/") if segment]
        entity_type = segments[0] if segments else "unknown"
        entity_id = segments[1] if len(segments) > 1 else None
        return entity_type, entity_id
