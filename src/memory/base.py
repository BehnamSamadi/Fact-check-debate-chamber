from __future__ import annotations

from abc import ABC, abstractmethod
from pydantic import BaseModel


class MemoryEntry(BaseModel):
    id: str
    content: str
    metadata: dict
    score: float = 0.0


class BaseMemory(ABC):
    @abstractmethod
    async def store_shared(self, debate_id: str, content: str, metadata: dict) -> str:
        pass

    @abstractmethod
    async def search_shared(self, debate_id: str, query: str, limit: int = 5) -> list[MemoryEntry]:
        pass

    @abstractmethod
    async def store_private(self, agent_id: str, content: str, metadata: dict) -> str:
        pass

    @abstractmethod
    async def search_private(self, agent_id: str, query: str, limit: int = 5) -> list[MemoryEntry]:
        pass
