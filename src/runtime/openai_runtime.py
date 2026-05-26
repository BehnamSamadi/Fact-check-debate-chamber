from __future__ import annotations

import json
import os

from openai import AsyncOpenAI

from src.runtime.base import BaseRuntime, RuntimeResponse, TokenUsage
from src.tracing.tracer import TraceContext


class OpenAIRuntime(BaseRuntime):
    def __init__(
        self,
        model: str | None = None,
        base_url: str | None = None,
        api_key: str | None = None,
    ):
        self._model = model or os.getenv("OPENAI_MODEL", "gpt-4o")
        self._client = AsyncOpenAI(
            base_url=base_url or os.getenv("LLM_BASE_URL"),
            api_key=api_key,
        )

    async def generate(
        self,
        system_prompt: str,
        messages: list[dict],
        tools: list[dict] | None = None,
        trace: TraceContext | None = None,
    ) -> RuntimeResponse:
        all_messages = [{"role": "system", "content": system_prompt}] + messages

        kwargs: dict = {
            "model": self._model,
            "messages": all_messages,
        }
        if tools:
            kwargs["tools"] = tools
        try:
            kwargs["response_format"] = {"type": "json_object"}
            response = await self._client.chat.completions.create(**kwargs)
        except Exception:
            kwargs.pop("response_format", None)
            kwargs.pop("tools", None)
            response = await self._client.chat.completions.create(**kwargs)

        choice = response.choices[0]
        content = choice.message.content or ""

        tool_calls = None
        if choice.message.tool_calls:
            tool_calls = [
                {
                    "name": tc.function.name,
                    "arguments": json.loads(tc.function.arguments),
                }
                for tc in choice.message.tool_calls
            ]

        usage = TokenUsage()
        if response.usage:
            usage = TokenUsage(
                prompt_tokens=response.usage.prompt_tokens,
                completion_tokens=response.usage.completion_tokens,
                total_tokens=response.usage.total_tokens,
            )

        if trace:
            gen = trace.generation(
                name=f"llm_call_{self._model}",
                model=self._model,
                input_data=all_messages,
                output_data=content,
                usage={"prompt_tokens": usage.prompt_tokens, "completion_tokens": usage.completion_tokens, "total_tokens": usage.total_tokens},
            )
            if gen:
                gen.end()

        return RuntimeResponse(content=content, tool_calls=tool_calls, usage=usage)
