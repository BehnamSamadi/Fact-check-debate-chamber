from __future__ import annotations

import logging
import os

import yaml

from src.agents.analyst import AnalystAgent
from src.agents.base import BaseAgent
from src.agents.researcher import ResearcherAgent
from src.agents.skeptic import SkepticAgent
from src.memory.base import BaseMemory
from src.protocol.agent_card import AgentCard
from src.runtime.base import BaseRuntime
from src.runtime.openai_runtime import OpenAIRuntime
from src.tools.base import BaseTool
from src.tools.contradiction import ContradictionChecker
from src.tools.evidence_search import EvidenceSearch

logger = logging.getLogger(__name__)

AGENT_CLASSES = {
    "skeptic": SkepticAgent,
    "researcher": ResearcherAgent,
    "analyst": AnalystAgent,
}

TOOL_CLASSES: dict[str, type[BaseTool]] = {
    "contradiction_checker": ContradictionChecker,
    "evidence_search": EvidenceSearch,
}

RUNTIME_BUILDERS: dict[str, type[BaseRuntime]] = {
    "openai": OpenAIRuntime,
}


def _resolve_provider_config(config: dict) -> dict:
    base_url = config.get("base_url")
    api_key_env = config.get("api_key_env")
    api_key = os.getenv(api_key_env) if api_key_env else None
    return {"base_url": base_url, "api_key": api_key}


class AgentFactory:
    def __init__(self, memory: BaseMemory | None = None):
        self._memory = memory

    def build(self, config_path: str) -> BaseAgent:
        with open(config_path) as f:
            config = yaml.safe_load(f)

        agent_id = config["agent_id"]
        agent_cls = AGENT_CLASSES.get(agent_id)
        if not agent_cls:
            raise ValueError(f"Unknown agent type: {agent_id}")

        card = AgentCard(
            agent_id=agent_id,
            name=config["name"],
            description=config["description"],
            capabilities=config.get("capabilities", []),
            domains=config.get("domains", []),
            version="0.1.0",
        )

        provider = _resolve_provider_config(config)
        runtime_cls = RUNTIME_BUILDERS.get(config.get("framework", "openai"))
        if not runtime_cls:
            raise ValueError(f"Unknown runtime: {config.get('framework')}")
        runtime = runtime_cls(model=config.get("model"), **provider)

        tools: list[BaseTool] = []
        for tool_name in config.get("tools", []):
            tool_cls = TOOL_CLASSES.get(tool_name)
            if tool_cls:
                if tool_name == "evidence_search" and self._memory:
                    tools.append(EvidenceSearch(memory=self._memory))
                else:
                    tools.append(tool_cls())
            else:
                logger.warning("Unknown tool: %s", tool_name)

        return agent_cls(
            card=card,
            runtime=runtime,
            memory=self._memory if config.get("memory_enabled", True) else None,
            tools=tools,
            system_prompt=config.get("system_prompt", ""),
        )
