"""Assistant has a transparent fallback when its external provider is unavailable."""
from unittest.mock import AsyncMock

import httpx
from openai import APIConnectionError

from app.core.config import settings
from app.infrastructure.external.llm.groq_provider import GroqProvider
from app.infrastructure.external.llm.provider import Message


async def test_missing_key_returns_database_summary(monkeypatch):
    monkeypatch.setattr(settings, "groq_api_key", None)
    provider = GroqProvider()
    answer = await provider.complete(
        system_prompt="Instructions\n--- Context snapshot ---\nUnresolved alerts: 12.",
        messages=[Message(role="user", content="What needs attention?")],
    )
    assert "Unresolved alerts: 12." in answer
    assert "not an AI-generated answer" in answer
    assert "Instructions" not in answer


async def test_provider_failure_returns_summary(monkeypatch):
    monkeypatch.setattr(settings, "groq_api_key", None)
    provider = GroqProvider()
    provider._client = AsyncMock()
    provider._client.chat.completions.create.side_effect = APIConnectionError(
        request=httpx.Request("POST", "https://example.test")
    )
    answer = await provider.complete(
        system_prompt="--- Context snapshot ---\nStockout count: 3.",
        messages=[Message(role="user", content="Explain")],
    )
    assert "Stockout count: 3." in answer
    assert "AI responses are currently unavailable" in answer
