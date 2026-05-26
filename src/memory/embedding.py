from __future__ import annotations

import os

from openai import AsyncOpenAI


class EmbeddingService:
    def __init__(
        self,
        model: str | None = None,
        base_url: str | None = None,
        api_key: str | None = None,
    ):
        self._model = model or os.getenv("EMBEDDING_MODEL", "text-embedding-3-small")
        self._client = AsyncOpenAI(
            base_url=base_url or os.getenv("EMBEDDING_BASE_URL"),
            api_key=api_key,
        )

    async def embed(self, texts: list[str]) -> list[list[float]]:
        response = await self._client.embeddings.create(input=texts, model=self._model)
        return [item.embedding for item in response.data]

    async def embed_single(self, text: str) -> list[float]:
        results = await self.embed([text])
        return results[0]
