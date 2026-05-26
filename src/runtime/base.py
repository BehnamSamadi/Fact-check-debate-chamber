from __future__ import annotations

from abc import ABC, abstractmethod
from typing import TYPE_CHECKING

from pydantic import BaseModel

if TYPE_CHECKING:
    from src.tracing.tracer import TraceContext


class ToolCall(BaseModel):
    name: str
    arguments: dict


class TokenUsage(BaseModel):
    prompt_tokens: int = 0
    completion_tokens: int = 0
    total_tokens: int = 0


class RuntimeResponse(BaseModel):
    content: str
    tool_calls: list[ToolCall] | None = None
    usage: TokenUsage = TokenUsage()


class BaseRuntime(ABC):
    @abstractmethod
    async def generate(
        self,
        system_prompt: str,
        messages: list[dict],
        tools: list[dict] | None = None,
        trace: TraceContext | None = None,
    ) -> RuntimeResponse:
        pass
