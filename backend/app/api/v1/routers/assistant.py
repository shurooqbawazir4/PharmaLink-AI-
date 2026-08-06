"""Assistant endpoints — explain a specific recommendation, or chat
grounded in a context snapshot. Reads open to any authenticated user; a
non-admin's chat is always scoped to their own hospital (see
`ChatRequest.hospital_id`'s docstring), never another hospital's data.
"""

from __future__ import annotations

from typing import Annotated
from uuid import UUID

from fastapi import APIRouter, Depends

from app.api.v1.deps import CurrentUser
from app.api.v1.schemas.assistant import ChatRequest, ChatResponse, ExplanationResponse
from app.application.assistant.service import AssistantService
from app.core.di import get_assistant_service
from app.infrastructure.external.llm.provider import Message

router = APIRouter(prefix="/assistant", tags=["AI Assistant"])

AssistantServiceDep = Annotated[AssistantService, Depends(get_assistant_service)]


@router.get("/explain/transfer/{transfer_id}", response_model=ExplanationResponse)
async def explain_transfer(
    transfer_id: UUID, service: AssistantServiceDep, _current_user: CurrentUser
) -> ExplanationResponse:
    explanation = await service.explain_transfer(transfer_id)
    return ExplanationResponse(explanation=explanation)


@router.get("/explain/purchase-order/{order_id}", response_model=ExplanationResponse)
async def explain_purchase_order(
    order_id: UUID, service: AssistantServiceDep, _current_user: CurrentUser
) -> ExplanationResponse:
    explanation = await service.explain_purchase_order(order_id)
    return ExplanationResponse(explanation=explanation)


@router.post("/chat", response_model=ChatResponse)
async def chat(
    payload: ChatRequest, service: AssistantServiceDep, current_user: CurrentUser
) -> ChatResponse:
    # Non-admins are always scoped to their own hospital, regardless of
    # what they pass — never another hospital's alerts/KPIs.
    hospital_id = (
        payload.hospital_id if current_user.role_name == "admin" else current_user.hospital_id
    )

    history = [Message(role=m.role, content=m.content) for m in payload.history]
    answer = await service.chat(
        hospital_id=hospital_id, question=payload.question, history=history
    )
    return ChatResponse(answer=answer)
