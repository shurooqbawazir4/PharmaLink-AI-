"""Assistant use cases: explain already-computed recommendations, and
answer freeform questions grounded in a context snapshot. The LLM never
predicts a number — see `infrastructure/external/llm/provider.py`.

Depends on `HospitalService`/`MedicineService` purely to resolve
human-readable names for prompts (`"Hospital A"`, `"Insulin"`, matching
the spec's own example — "Transferring 420 insulin units from Hospital A
to Hospital B") rather than stuffing raw UUIDs into what an LLM has to
narrate. The widest cross-module composition in the codebase so far, and
squarely the same "application layer may compose across modules" pattern
`OptimizationService` and `TransferService` already established.
"""

from __future__ import annotations

from uuid import UUID

from app.application.analytics.service import AnalyticsService
from app.application.expiry.service import ExpiryService
from app.application.hospitals.service import HospitalService
from app.application.medicines.service import MedicineService
from app.application.notifications.service import NotificationService
from app.application.procurement.service import ProcurementService
from app.application.transfers.service import TransferService
from app.infrastructure.external.llm.provider import LLMProvider, Message

_EXPLAIN_SYSTEM_PROMPT = (
    "You are MedCycle AI's explanation assistant for a hospital medication "
    "intelligence platform. You explain a recommendation the system has already "
    "computed. Never invent numbers, never predict demand, never suggest actions "
    "beyond what's given below. Be concise (2-3 sentences), concrete, and "
    "reference the actual figures provided."
)

_CHAT_SYSTEM_PROMPT_TEMPLATE = (
    "You are MedCycle AI's assistant for a hospital medication intelligence "
    "platform. Answer the user's question using ONLY the context snapshot below "
    "— never invent numbers, predictions, or recommendations beyond what's given. "
    "If the context doesn't contain the answer, say so plainly rather than "
    "guessing. Be concise and concrete.\n\n--- Context snapshot ---\n{context}"
)

_MAX_CONTEXT_ALERTS = 10
_MAX_CONTEXT_HIGH_RISK = 5


class AssistantService:
    def __init__(
        self,
        llm_provider: LLMProvider,
        transfer_service: TransferService,
        procurement_service: ProcurementService,
        analytics_service: AnalyticsService,
        expiry_service: ExpiryService,
        notification_service: NotificationService,
        hospital_service: HospitalService,
        medicine_service: MedicineService,
    ) -> None:
        self._llm = llm_provider
        self._transfers = transfer_service
        self._procurement = procurement_service
        self._analytics = analytics_service
        self._expiry = expiry_service
        self._notifications = notification_service
        self._hospitals = hospital_service
        self._medicines = medicine_service

    async def explain_transfer(self, transfer_id: UUID) -> str:
        transfer = await self._transfers.get(transfer_id)
        source = await self._hospitals.get(transfer.source_hospital_id)
        destination = await self._hospitals.get(transfer.destination_hospital_id)
        medicine = await self._medicines.get(transfer.medicine_id)

        prompt = (
            f"Transfer: {transfer.quantity} units of {medicine.name} from "
            f"{source.name} to {destination.name}. Status: {transfer.status.value}. "
            f"Recommended by: {transfer.recommended_by.value}. "
            f"Distance: {transfer.distance_km} km. "
            f"Transportation cost: ${transfer.transportation_cost}. "
            f"Value of expiry waste prevented: ${transfer.expiry_prevented_value}.\n\n"
            "Explain why this transfer makes sense, referencing the actual numbers above."
        )
        return await self._llm.complete(
            system_prompt=_EXPLAIN_SYSTEM_PROMPT, messages=[Message(role="user", content=prompt)]
        )

    async def explain_purchase_order(self, order_id: UUID) -> str:
        order = await self._procurement.get(order_id)
        hospital = await self._hospitals.get(order.hospital_id)
        medicine = await self._medicines.get(order.medicine_id)

        prompt = (
            f"Purchase order: {order.quantity} units of {medicine.name} for "
            f"{hospital.name}. Unit cost: ${order.unit_cost}, total cost: "
            f"${order.total_cost}. Status: {order.status.value}. Recommended by: "
            f"{order.recommended_by.value}. Expected delivery: "
            f"{order.expected_delivery_date}.\n\n"
            "Explain why this purchase makes sense, referencing the actual numbers above."
        )
        return await self._llm.complete(
            system_prompt=_EXPLAIN_SYSTEM_PROMPT, messages=[Message(role="user", content=prompt)]
        )

    async def chat(
        self, *, hospital_id: UUID | None, question: str, history: list[Message]
    ) -> str:
        context = await self._build_context_snapshot(hospital_id)
        system_prompt = _CHAT_SYSTEM_PROMPT_TEMPLATE.format(context=context)
        return await self._llm.complete(
            system_prompt=system_prompt, messages=[*history, Message(role="user", content=question)]
        )

    async def _build_context_snapshot(self, hospital_id: UUID | None) -> str:
        kpis = await self._analytics.get_kpi_summary(hospital_id)
        high_risk = await self._expiry.list_high_risk(threshold=0.5, hospital_id=hospital_id)
        alerts = await self._notifications.list(hospital_id=hospital_id, is_resolved=False)

        lines = [
            f"Medicine waste: {kpis.medicine_waste_units} units "
            f"(${kpis.medicine_waste_value:,.2f}).",
            f"Transfer success rate: {kpis.transfer_success_rate}.",
            f"Procurement spend: ${kpis.procurement_spend:,.2f} across "
            f"{kpis.procurement_orders_count} orders.",
            f"Stockout count: {kpis.stockout_count}. "
            f"Inventory turnover ratio: {kpis.inventory_turnover_ratio}.",
            f"Unresolved alerts: {len(alerts)}.",
        ]

        if high_risk:
            lines.append("Highest expiry-risk batches:")
            ranked = sorted(
                high_risk, key=lambda record: record.probability_expires_before_use, reverse=True
            )
            for record in ranked[:_MAX_CONTEXT_HIGH_RISK]:
                lines.append(
                    f"  - {record.probability_expires_before_use:.0%} risk of expiring "
                    f"unused, ${record.estimated_financial_loss:,.2f} at risk "
                    f"(inventory batch {record.inventory_id})"
                )

        for alert in alerts[:_MAX_CONTEXT_ALERTS]:
            lines.append(f"  - [{alert.severity.value}] {alert.type.value}: {alert.message}")

        return "\n".join(lines)
