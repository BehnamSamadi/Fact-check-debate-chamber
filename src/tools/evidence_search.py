from __future__ import annotations

from src.memory.base import BaseMemory
from src.tools.base import BaseTool


class EvidenceSearch(BaseTool):
    def __init__(self, memory: BaseMemory | None = None):
        self._memory = memory

    @property
    def name(self) -> str:
        return "evidence_search"

    @property
    def description(self) -> str:
        return "Search for relevant evidence from the debate history and verified claims."

    def _parameters(self) -> dict:
        return {
            "type": "object",
            "properties": {
                "query": {
                    "type": "string",
                    "description": "Search query for evidence.",
                },
                "debate_id": {
                    "type": "string",
                    "description": "The debate ID to search within.",
                },
            },
            "required": ["query"],
        }

    async def run(self, **kwargs) -> dict:
        query = kwargs.get("query", "")
        debate_id = kwargs.get("debate_id")

        if not self._memory or not debate_id:
            return {"results": [], "note": "No memory backend available for evidence search."}

        shared = await self._memory.search_shared(debate_id, query, limit=5)
        results = [
            {"content": entry.content, "score": entry.score, "metadata": entry.metadata}
            for entry in shared
        ]
        return {"results": results, "count": len(results)}
