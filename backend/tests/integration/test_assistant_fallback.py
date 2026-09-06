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


async def test_reasoning_model_returns_answer(monkeypatch):
    from types import SimpleNamespace

    monkeypatch.setattr(settings, "groq_api_key", None)
    monkeypatch.setattr(settings, "groq_model", "openai/gpt-oss-120b")
    provider = GroqProvider()
    provider._client = AsyncMock()
    provider._client.chat.completions.create.return_value = SimpleNamespace(
        choices=[SimpleNamespace(message=SimpleNamespace(content="Review the expiry alerts."))]
    )
    answer = await provider.complete(system_prompt="Facts", messages=[])
    assert answer == "Review the expiry alerts."
    kwargs = provider._client.chat.completions.create.call_args.kwargs
    assert kwargs["reasoning_effort"] == "low"
    assert kwargs["max_completion_tokens"] == 4096
    assert "max_tokens" not in kwargs


async def test_invalid_key_is_distinguished_without_leaking_error_body(monkeypatch):
    from openai import AuthenticationError

    monkeypatch.setattr(settings, "groq_api_key", None)
    provider = GroqProvider()
    provider._client = AsyncMock()
    provider._client.chat.completions.create.side_effect = AuthenticationError(
        "secret-value", response=httpx.Response(
            401, request=httpx.Request("POST", "https://example.test")
        ), body=None,
    )
    answer = await provider.complete(system_prompt="--- Context snapshot --- Facts", messages=[])
    assert "Groq rejected the API key" in answer
    assert "secret-value" not in answer
