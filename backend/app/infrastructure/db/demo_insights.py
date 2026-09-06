"""Initialize derived demo risks and alerts using existing inventory."""
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.application.expiry.service import ExpiryService
from app.application.notifications.service import NotificationService
from app.domain.shared.enums import AlertSeverity, AlertType
from app.infrastructure.db.models import AlertModel
from app.infrastructure.db.repositories.alert_repository import SQLAlchemyAlertRepository
from app.infrastructure.db.repositories.expiry_repository import SQLAlchemyExpiryRiskRepository
from app.infrastructure.db.repositories.inventory_repository import SQLAlchemyInventoryRepository
from app.infrastructure.external.naive_expiry_scorer import NaiveExpiryScorer


async def initialize_insights(session: AsyncSession) -> None:
    inventory = SQLAlchemyInventoryRepository(session)
    notifications = NotificationService(SQLAlchemyAlertRepository(session))
    expiry = ExpiryService(
        SQLAlchemyExpiryRiskRepository(session), inventory, NaiveExpiryScorer(), notifications
    )
    evaluated = 0
    for batch in await inventory.list_batches():
        # Seed only missing evaluations so restarts do not duplicate alerts.
        if await expiry.get_latest_for_inventory(batch.id) is None:
            await expiry.evaluate_batch(batch.id)
            evaluated += 1
        if batch.current_stock < batch.safety_stock:
            existing = await session.scalar(select(AlertModel.id).where(
                AlertModel.hospital_id == batch.hospital_id,
                AlertModel.medicine_id == batch.medicine_id,
                AlertModel.type == AlertType.LOW_STOCK,
            ).limit(1))
            if existing is None:
                await notifications.create_alert(
                    hospital_id=batch.hospital_id,
                    medicine_id=batch.medicine_id,
                    alert_type=AlertType.LOW_STOCK,
                    severity=AlertSeverity.WARNING,
                    message=f"Batch {batch.batch_number}: {batch.current_stock} units remaining; "
                    f"safety stock is {batch.safety_stock} units.",
                )
    await session.commit()
    print(f"Dashboard insights: {evaluated} batches evaluated; alerts initialized.")
