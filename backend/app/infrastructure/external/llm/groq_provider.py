"""Groq — OpenAI-compatible chat completions endpoint. The `openai` SDK
works unmodified once `base_url` is overridden to point at Groq instead of
OpenAI; see docs/architecture.md for why Groq was chosen and
`core/config.py::Settings` for the `groq_*` fields.
"""

from __future__ import annotations

import logging

from openai import NOT_GIVEN, APIError, AsyncOpenAI
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
_MAX_TOKENS = 4096


class GroqProvider:
    def __init__(self) -> None:
        self._client = (
            AsyncOpenAI(base_url=settings.groq_base_url, api_key=settings.groq_api_key.strip(),
                        timeout=20.0, max_retries=0)
            if settings.groq_api_key and settings.groq_api_key.strip() else None
        )

    async def complete(self, *, system_prompt: str, messages: list[Message]) -> str:
        if self._client is None:
            return self._summary(
                system_prompt, messages, "Groq is not configured on this API service."
            )
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

        try:
            response = await self._client.chat.completions.create(
                model=settings.groq_model,
                messages=chat_messages,
                temperature=_TEMPERATURE,
                max_completion_tokens=_MAX_TOKENS,
                reasoning_effort=(
                    "low" if settings.groq_model.startswith("openai/gpt-oss-") else NOT_GIVEN
                ),
            )
            content = response.choices[0].message.content if response.choices else None
            if content and content.strip():
                return content
            logging.getLogger(__name__).warning(
                "Assistant provider returned no answer; finish_reason=%s",
                response.choices[0].finish_reason if response.choices else "no_choices",
            )
            return self._summary(system_prompt, messages, "Groq returned an empty answer.")
        except APIError as exc:
            logging.getLogger(__name__).warning(
                "Assistant provider unavailable: %s status=%s",
                type(exc).__name__, getattr(exc, "status_code", None),
            )
            status = getattr(exc, "status_code", None)
            reason = {
                401: "Groq rejected the API key.",
                403: "Groq denied access to this model or account.",
                404: "The configured Groq model or endpoint was not found.",
                429: "Groq rate or usage limit reached. Try again later.",
                400: "Groq rejected the model request. Check the API model configuration.",
            }.get(status, "The API could not reach Groq or Groq is temporarily unavailable.")
            return self._summary(system_prompt, messages, reason)

    @staticmethod
    def _summary(system_prompt: str, messages: list[Message], reason: str) -> str:
        """Transparent non-generative fallback, using only supplied database facts."""
        marker = "--- Context snapshot ---"
        if marker in system_prompt:
            facts = system_prompt.split(marker, 1)[1].strip()
        else:
            facts = messages[-1].content.split("\n\n", 1)[0] if messages else ""
        return (
            f"AI responses are currently unavailable. {reason} Here is a database summary, "
            "not an AI-generated answer to your question:\n\n" + facts
        )
