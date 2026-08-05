"""Dependency-injection wiring — idiomatic FastAPI `Depends` chains, no DI
framework. Each `get_*_service` composes repository -> service, so routers
only ever depend on a service and tests only ever override a provider
function via `app.dependency_overrides`.
"""

from __future__ import annotations

from typing import Annotated

from fastapi import Depends
from sqlalchemy.ext.asyncio import AsyncSession

from app.application.analytics.service import AnalyticsService
from app.application.auth.service import AuthService
from app.application.expiry.service import ExpiryService
from app.application.hospitals.service import HospitalService
from app.application.inventory.service import InventoryService
from app.application.medicines.service import MedicineService
from app.application.notifications.service import NotificationService
from app.application.procurement.service import ProcurementService
from app.application.procurement.supplier_service import SupplierService
from app.application.transfers.service import TransferService
from app.core.database import get_db
from app.domain.auth.repository import UserRepository
from app.domain.expiry.repository import ExpiryRiskRepository
from app.domain.expiry.scorer import ExpiryRiskScorer
from app.domain.hospitals.repository import HospitalRepository
from app.domain.inventory.repository import InventoryRepository
from app.domain.medicines.repository import MedicineRepository
from app.domain.notifications.repository import AlertRepository
from app.domain.procurement.recommender import ProcurementRecommender
from app.domain.procurement.repository import PurchaseOrderRepository, SupplierRepository
from app.domain.transfers.repository import TransferRepository
from app.infrastructure.db.repositories.alert_repository import SQLAlchemyAlertRepository
from app.infrastructure.db.repositories.expiry_repository import SQLAlchemyExpiryRiskRepository
from app.infrastructure.db.repositories.hospital_repository import SQLAlchemyHospitalRepository
from app.infrastructure.db.repositories.inventory_repository import SQLAlchemyInventoryRepository
from app.infrastructure.db.repositories.medicine_repository import SQLAlchemyMedicineRepository
from app.infrastructure.db.repositories.purchase_order_repository import (
    SQLAlchemyPurchaseOrderRepository,
)
from app.infrastructure.db.repositories.supplier_repository import SQLAlchemySupplierRepository
from app.infrastructure.db.repositories.transfer_repository import SQLAlchemyTransferRepository
from app.infrastructure.db.repositories.user_repository import SQLAlchemyUserRepository
from app.infrastructure.external.naive_expiry_scorer import NaiveExpiryScorer
from app.infrastructure.external.naive_procurement_recommender import (
    NaiveProcurementRecommender,
)

DbSession = Annotated[AsyncSession, Depends(get_db)]


# --- Repositories ------------------------------------------------------------


def get_user_repository(db: DbSession) -> UserRepository:
    return SQLAlchemyUserRepository(db)


def get_hospital_repository(db: DbSession) -> HospitalRepository:
    return SQLAlchemyHospitalRepository(db)


def get_medicine_repository(db: DbSession) -> MedicineRepository:
    return SQLAlchemyMedicineRepository(db)


def get_alert_repository(db: DbSession) -> AlertRepository:
    return SQLAlchemyAlertRepository(db)


def get_inventory_repository(db: DbSession) -> InventoryRepository:
    return SQLAlchemyInventoryRepository(db)


def get_transfer_repository(db: DbSession) -> TransferRepository:
    return SQLAlchemyTransferRepository(db)


def get_expiry_repository(db: DbSession) -> ExpiryRiskRepository:
    return SQLAlchemyExpiryRiskRepository(db)


def get_expiry_scorer() -> ExpiryRiskScorer:
    """Milestone C swaps this for an ML-backed scorer — every caller depends
    on `ExpiryRiskScorer` (the interface), never on `NaiveExpiryScorer`
    directly, so nothing else has to change when that happens."""
    return NaiveExpiryScorer()


def get_supplier_repository(db: DbSession) -> SupplierRepository:
    return SQLAlchemySupplierRepository(db)


def get_purchase_order_repository(db: DbSession) -> PurchaseOrderRepository:
    return SQLAlchemyPurchaseOrderRepository(db)


def get_procurement_recommender() -> ProcurementRecommender:
    """Milestone C swaps this for the OR-Tools-informed recommender —
    same pattern as `get_expiry_scorer`."""
    return NaiveProcurementRecommender()


# --- Services ------------------------------------------------------------------


def get_auth_service(
    user_repo: Annotated[UserRepository, Depends(get_user_repository)],
) -> AuthService:
    return AuthService(user_repo)


def get_analytics_service(db: DbSession) -> AnalyticsService:
    """The one service composed straight from a DB session, not a
    repository — see `application/analytics/service.py` for why."""
    return AnalyticsService(db)


def get_hospital_service(
    hospital_repo: Annotated[HospitalRepository, Depends(get_hospital_repository)],
) -> HospitalService:
    return HospitalService(hospital_repo)


def get_medicine_service(
    medicine_repo: Annotated[MedicineRepository, Depends(get_medicine_repository)],
) -> MedicineService:
    return MedicineService(medicine_repo)


def get_notification_service(
    alert_repo: Annotated[AlertRepository, Depends(get_alert_repository)],
) -> NotificationService:
    return NotificationService(alert_repo)


def get_inventory_service(
    inventory_repo: Annotated[InventoryRepository, Depends(get_inventory_repository)],
    notification_service: Annotated[NotificationService, Depends(get_notification_service)],
) -> InventoryService:
    return InventoryService(inventory_repo, notification_service)


def get_transfer_service(
    transfer_repo: Annotated[TransferRepository, Depends(get_transfer_repository)],
    inventory_repo: Annotated[InventoryRepository, Depends(get_inventory_repository)],
    hospital_repo: Annotated[HospitalRepository, Depends(get_hospital_repository)],
) -> TransferService:
    return TransferService(transfer_repo, inventory_repo, hospital_repo)


def get_expiry_service(
    expiry_repo: Annotated[ExpiryRiskRepository, Depends(get_expiry_repository)],
    inventory_repo: Annotated[InventoryRepository, Depends(get_inventory_repository)],
    scorer: Annotated[ExpiryRiskScorer, Depends(get_expiry_scorer)],
    notification_service: Annotated[NotificationService, Depends(get_notification_service)],
) -> ExpiryService:
    return ExpiryService(expiry_repo, inventory_repo, scorer, notification_service)


def get_supplier_service(
    supplier_repo: Annotated[SupplierRepository, Depends(get_supplier_repository)],
) -> SupplierService:
    return SupplierService(supplier_repo)


def get_procurement_service(
    order_repo: Annotated[PurchaseOrderRepository, Depends(get_purchase_order_repository)],
    supplier_repo: Annotated[SupplierRepository, Depends(get_supplier_repository)],
    inventory_repo: Annotated[InventoryRepository, Depends(get_inventory_repository)],
    inventory_service: Annotated[InventoryService, Depends(get_inventory_service)],
    recommender: Annotated[ProcurementRecommender, Depends(get_procurement_recommender)],
) -> ProcurementService:
    return ProcurementService(
        order_repo, supplier_repo, inventory_repo, inventory_service, recommender
    )
