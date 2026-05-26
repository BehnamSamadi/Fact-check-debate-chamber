from __future__ import annotations

import logging
import uuid

from qdrant_client import AsyncQdrantClient
from qdrant_client.models import Distance, PointStruct, VectorParams

from src.memory.base import BaseMemory, MemoryEntry
from src.memory.embedding import EmbeddingService

logger = logging.getLogger(__name__)


class QdrantMemory(BaseMemory):
    def __init__(self, url: str | None = None, embedding_service: EmbeddingService | None = None):
        self._url = url or "http://localhost:6333"
        self._client = AsyncQdrantClient(url=self._url)
        self._embedding = embedding_service or EmbeddingService()
        self._initialized_collections: set[str] = set()

    async def _ensure_collection(self, name: str) -> None:
        if name in self._initialized_collections:
            return
        exists = await self._client.collection_exists(name)
        if not exists:
            await self._client.create_collection(
                collection_name=name,
                vectors_config=VectorParams(size=1536, distance=Distance.COSINE),
            )
            logger.info("Created Qdrant collection: %s", name)
        self._initialized_collections.add(name)

    async def store_shared(self, debate_id: str, content: str, metadata: dict) -> str:
        collection = f"debate_{debate_id}"
        return await self._store(collection, content, metadata)

    async def search_shared(self, debate_id: str, query: str, limit: int = 5) -> list[MemoryEntry]:
        collection = f"debate_{debate_id}"
        return await self._search(collection, query, limit)

    async def store_private(self, agent_id: str, content: str, metadata: dict) -> str:
        collection = f"agent_{agent_id}_private"
        return await self._store(collection, content, metadata)

    async def search_private(self, agent_id: str, query: str, limit: int = 5) -> list[MemoryEntry]:
        collection = f"agent_{agent_id}_private"
        return await self._search(collection, query, limit)

    async def _store(self, collection: str, content: str, metadata: dict) -> str:
        await self._ensure_collection(collection)
        point_id = str(uuid.uuid4())
        vector = await self._embedding.embed_single(content)
        point = PointStruct(id=point_id, vector=vector, payload={"content": content, **metadata})
        await self._client.upsert(collection_name=collection, points=[point])
        return point_id

    async def _search(self, collection: str, query: str, limit: int) -> list[MemoryEntry]:
        try:
            await self._ensure_collection(collection)
        except Exception:
            return []
        query_vector = await self._embedding.embed_single(query)
        results = await self._client.query_points(
            collection_name=collection, query=query_vector, limit=limit
        )
        return [
            MemoryEntry(
                id=str(hit.id),
                content=hit.payload.get("content", ""),
                metadata={k: v for k, v in hit.payload.items() if k != "content"},
                score=hit.score,
            )
            for hit in results.points
        ]
