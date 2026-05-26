from __future__ import annotations

from pydantic import BaseModel, Field


class AgentCard(BaseModel):
    agent_id: str
    name: str
    description: str
    capabilities: list[str] = Field(default_factory=list)
    domains: list[str] = Field(default_factory=list)
    version: str = "0.1.0"
    metadata: dict = Field(default_factory=dict)
