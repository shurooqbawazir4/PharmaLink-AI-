"""Dependency-injection wiring — idiomatic FastAPI `Depends` chains, no DI
framework. Each `get_*_service` composes repository -> service, so routers
only ever depend on a service and tests only ever override a provider
function via `app.dependency_overrides`.
"""

from __future__ import annotations

from typing import Annotated

from fastapi import Depends
from sqlalchemy.ext.asyncio import AsyncSession

from app.application.auth.service import AuthService
from app.application.hospitals.service import HospitalService
from app.application.medicines.service import MedicineService
from app.core.database import get_db
from app.domain.auth.repository import UserRepository
from app.domain.hospitals.repository import HospitalRepository
from app.domain.medicines.repository import MedicineRepository
from app.infrastructure.db.repositories.hospital_repository import SQLAlchemyHospitalRepository
from app.infrastructure.db.repositories.medicine_repository import SQLAlchemyMedicineRepository
from app.infrastructure.db.repositories.user_repository import SQLAlchemyUserRepository

DbSession = Annotated[AsyncSession, Depends(get_db)]


# --- Repositories ------------------------------------------------------------


def get_user_repository(db: DbSession) -> UserRepository:
    return SQLAlchemyUserRepository(db)


def get_hospital_repository(db: DbSession) -> HospitalRepository:
    return SQLAlchemyHospitalRepository(db)


def get_medicine_repository(db: DbSession) -> MedicineRepository:
    return SQLAlchemyMedicineRepository(db)


# --- Services ------------------------------------------------------------------


def get_auth_service(
    user_repo: Annotated[UserRepository, Depends(get_user_repository)],
) -> AuthService:
    return AuthService(user_repo)


def get_hospital_service(
    hospital_repo: Annotated[HospitalRepository, Depends(get_hospital_repository)],
) -> HospitalService:
    return HospitalService(hospital_repo)


def get_medicine_service(
    medicine_repo: Annotated[MedicineRepository, Depends(get_medicine_repository)],
) -> MedicineService:
    return MedicineService(medicine_repo)
