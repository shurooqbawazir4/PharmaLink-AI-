"""Groq — OpenAI-compatible chat completions endpoint. The `openai` SDK
works unmodified once `base_url` is overridden to point at Groq instead of
OpenAI; see docs/architecture.md for why Groq was chosen and
`core/config.py::Settings` for the `groq_*` fields.
"""

from __future__ import annotations

from openai import AsyncOpenAI
from openai.types.chat import (
    ChatCompletionAssistantMessageParam,
    ChatCompletionMessageParam,
    ChatCompletionSystemMessageParam,
    ChatCompletionUserMessageParam,
)

from app.core.config import settings
from app.infrastructure.external.llm.provider import Message

_TEMPERATURE = 0.3
"""Low but not zero — explanations should read naturally, not robotically
repeat the same phrasing, but must stay grounded in the given numbers."""
_MAX_TOKENS = 600


class GroqProvider:
    def __init__(self) -> None:
        self._client = AsyncOpenAI(base_url=settings.groq_base_url, api_key=settings.groq_api_key)

    async def complete(self, *, system_prompt: str, messages: list[Message]) -> str:
        chat_messages: list[ChatCompletionMessageParam] = [
            ChatCompletionSystemMessageParam(role="system", content=system_prompt),
        ]
        for message in messages:
            if message.role == "assistant":
                chat_messages.append(
                    ChatCompletionAssistantMessageParam(role="assistant", content=message.content)
                )
            else:
                chat_messages.append(
                    ChatCompletionUserMessageParam(role="user", content=message.content)
                )

        response = await self._client.chat.completions.create(
            model=settings.groq_model,
            messages=chat_messages,
            temperature=_TEMPERATURE,
            max_tokens=_MAX_TOKENS,
        )
        return response.choices[0].message.content or ""
