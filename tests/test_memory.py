from __future__ import annotations

from unittest.mock import AsyncMock, MagicMock

import pytest

from src.memory.base import BaseMemory, MemoryEntry


class FakeMemory(BaseMemory):
    def __init__(self):
        self._shared: dict[str, list[dict]] = {}
        self._private: dict[str, list[dict]] = {}

    async def store_shared(self, debate_id: str, content: str, metadata: dict) -> str:
        key = f"debate_{debate_id}"
        if key not in self._shared:
            self._shared[key] = []
        entry_id = str(len(self._shared[key]))
        self._shared[key].append({"id": entry_id, "content": content, **metadata})
        return entry_id

    async def search_shared(self, debate_id: str, query: str, limit: int = 5) -> list[MemoryEntry]:
        key = f"debate_{debate_id}"
        entries = self._shared.get(key, [])
        return [
            MemoryEntry(id=e["id"], content=e["content"], metadata={k: v for k, v in e.items() if k not in ("id", "content")}, score=1.0)
            for e in entries[:limit]
        ]

    async def store_private(self, agent_id: str, content: str, metadata: dict) -> str:
        key = f"agent_{agent_id}_private"
        if key not in self._private:
            self._private[key] = []
        entry_id = str(len(self._private[key]))
        self._private[key].append({"id": entry_id, "content": content, **metadata})
        return entry_id

    async def search_private(self, agent_id: str, query: str, limit: int = 5) -> list[MemoryEntry]:
        key = f"agent_{agent_id}_private"
        entries = self._private.get(key, [])
        return [
            MemoryEntry(id=e["id"], content=e["content"], metadata={k: v for k, v in e.items() if k not in ("id", "content")}, score=1.0)
            for e in entries[:limit]
        ]


@pytest.mark.asyncio
async def test_store_and_search_shared():
    memory = FakeMemory()
    await memory.store_shared("debate1", "test content", {"agent_id": "skeptic"})
    results = await memory.search_shared("debate1", "test")
    assert len(results) == 1
    assert results[0].content == "test content"


@pytest.mark.asyncio
async def test_store_and_search_private():
    memory = FakeMemory()
    await memory.store_private("skeptic", "private reasoning", {"round": 1})
    results = await memory.search_private("skeptic", "reasoning")
    assert len(results) == 1
    assert results[0].content == "private reasoning"


@pytest.mark.asyncio
async def test_search_empty_returns_empty():
    memory = FakeMemory()
    results = await memory.search_shared("nonexistent", "query")
    assert results == []
