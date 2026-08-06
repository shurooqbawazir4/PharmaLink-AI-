"""Pydantic v2 request/response models for the assistant endpoints."""

from __future__ import annotations

from typing import Literal
from uuid import UUID

from pydantic import BaseModel, Field


class ChatMessage(BaseModel):
    role: Literal["user", "assistant"]
    content: str


class ChatRequest(BaseModel):
    question: str = Field(min_length=1, max_length=2000)
    history: list[ChatMessage] = Field(default_factory=list)
    hospital_id: UUID | None = Field(
        default=None,
        description="Scope context to one hospital. Non-admins are always scoped to "
        "their own hospital regardless of this field; admins may pass any hospital "
        "or omit it for a network-wide view.",
    )


class ChatResponse(BaseModel):
    answer: str


class ExplanationResponse(BaseModel):
    explanation: str
