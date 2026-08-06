"""FastAPI application factory and entrypoint (`uvicorn app.main:app`)."""

from __future__ import annotations

from collections.abc import AsyncIterator
from contextlib import asynccontextmanager

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from app.api.v1.routers import (
    analytics,
    assistant,
    auth,
    expiry,
    forecast,
    hospitals,
    inventory,
    medicines,
    notifications,
    optimization,
    procurement,
    transfers,
)
from app.core.config import settings
from app.core.database import AsyncSessionLocal
from app.core.exceptions import register_exception_handlers
from app.core.logging import AuditLogMiddleware, setup_logging


@asynccontextmanager
async def lifespan(_app: FastAPI) -> AsyncIterator[None]:
    setup_logging()
    yield


def create_app() -> FastAPI:
    app = FastAPI(
        title=settings.app_name,
        description="AI-powered medication intelligence platform: demand forecasting, "
        "expiry-risk, shortage prediction, transfer optimization, and procurement "
        "recommendations for hospital networks.",
        version="0.1.0",
        lifespan=lifespan,
        docs_url="/docs",
        redoc_url="/redoc",
        openapi_url="/openapi.json",
    )

    # Default DB session factory for the audit-log middleware — swappable
    # via `app.state.audit_session_factory` (tests point this at an
    # in-memory SQLite factory; see tests/conftest.py).
    app.state.audit_session_factory = AsyncSessionLocal

    app.add_middleware(
        CORSMiddleware,
        allow_origins=settings.cors_origins_list,
        allow_credentials=True,
        allow_methods=["*"],
        allow_headers=["*"],
    )
    app.add_middleware(AuditLogMiddleware)

    register_exception_handlers(app)

    app.include_router(auth.router, prefix=settings.api_v1_prefix)
    app.include_router(hospitals.router, prefix=settings.api_v1_prefix)
    app.include_router(medicines.router, prefix=settings.api_v1_prefix)
    app.include_router(inventory.router, prefix=settings.api_v1_prefix)
    app.include_router(transfers.router, prefix=settings.api_v1_prefix)
    app.include_router(expiry.router, prefix=settings.api_v1_prefix)
    app.include_router(procurement.suppliers_router, prefix=settings.api_v1_prefix)
    app.include_router(procurement.purchase_orders_router, prefix=settings.api_v1_prefix)
    app.include_router(notifications.router, prefix=settings.api_v1_prefix)
    app.include_router(analytics.router, prefix=settings.api_v1_prefix)
    app.include_router(forecast.router, prefix=settings.api_v1_prefix)
    app.include_router(optimization.router, prefix=settings.api_v1_prefix)
    app.include_router(assistant.router, prefix=settings.api_v1_prefix)

    @app.get(f"{settings.api_v1_prefix}/health", tags=["Health"])
    async def health_check() -> dict[str, str]:
        return {"status": "ok", "app": settings.app_name, "env": settings.env}

    return app


app = create_app()
