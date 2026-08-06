"""The LLM explanation-layer contract. Explanation only — the LLM never
computes a number, prediction, or recommendation; it narrates ones the
backend has already computed (Expiry/Procurement/Transfers/Optimization).
See docs/architecture.md and the original spec's explicit constraint.
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import Protocol


@dataclass(slots=True, frozen=True)
class Message:
    role: str
    """"user" or "assistant" — never "system"; the system prompt is a
    separate argument on `complete()` so callers can't accidentally let
    conversation history override the explanation-only framing."""
    content: str


class LLMProvider(Protocol):
    async def complete(self, *, system_prompt: str, messages: list[Message]) -> str: ...
