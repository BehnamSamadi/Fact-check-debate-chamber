from __future__ import annotations

import json
import logging
from abc import ABC, abstractmethod

from src.memory.base import BaseMemory
from src.protocol.agent_card import AgentCard
from src.protocol.schemas import (
    ACPEnvelope,
    DebateContent,
    DebatePhase,
    MessageType,
    make_envelope,
)
from src.runtime.base import BaseRuntime
from src.tools.base import BaseTool
from src.tracing.tracer import TraceContext

logger = logging.getLogger(__name__)


class BaseAgent(ABC):
    def __init__(
        self,
        card: AgentCard,
        runtime: BaseRuntime,
        memory: BaseMemory | None = None,
        tools: list[BaseTool] | None = None,
        system_prompt: str = "",
    ):
        self.card = card
        self.runtime = runtime
        self.memory = memory
        self.tools = tools or []
        self._system_prompt = system_prompt

    async def process_message(self, envelope: ACPEnvelope) -> ACPEnvelope:
        content = DebateContent.model_validate(envelope.body)
        debate_id = envelope.header.task_id

        trace = TraceContext(
            name=f"{self.card.agent_id}_{content.phase.value}",
            metadata={
                "debate_id": debate_id,
                "agent_id": self.card.agent_id,
                "phase": content.phase.value,
                "round": content.round,
            },
        )

        with trace:
            shared_history = await self._retrieve_shared(debate_id, content.topic)
            private_history = await self._retrieve_private(content.topic)

            messages = self._build_messages(content, shared_history, private_history)
            system_prompt = self.build_system_prompt(content.phase, content.topic)

            openai_tools = [t.to_openai_tool() for t in self.tools] if self.tools else None

            response = await self.runtime.generate(system_prompt, messages, openai_tools, trace=trace)

            try:
                agent_response = json.loads(response.content)
            except json.JSONDecodeError:
                agent_response = self._extract_json_fallback(response.content)

            agent_response["agent_id"] = self.card.agent_id
            agent_response["phase"] = content.phase.value
            agent_response["round"] = content.round

            if self.memory:
                await self.memory.store_shared(
                    debate_id,
                    json.dumps(agent_response),
                    {"agent_id": self.card.agent_id, "phase": content.phase.value, "round": content.round},
                )
                await self.memory.store_private(
                    self.card.agent_id,
                    json.dumps({"input_topic": content.topic, "reasoning": agent_response.get("reasoning", ""), "phase": content.phase.value}),
                    {"round": content.round},
                )

            trace.event("response_stored", output={"stance": agent_response.get("stance"), "confidence": agent_response.get("confidence")})

            return make_envelope(
                message_type=MessageType.TASK_MESSAGE,
                sender=self.card.agent_id,
                recipient="orchestrator",
                task_id=debate_id,
                body=agent_response,
                correlation_id=envelope.header.correlation_id,
            )

    @abstractmethod
    def build_system_prompt(self, phase: DebatePhase, topic: str) -> str:
        pass

    def _extract_json_fallback(self, text: str) -> dict:
        for start_char, end_char in [("{", "}"), ("[", "]")]:
            start = text.find(start_char)
            if start == -1:
                continue
            depth = 0
            for i in range(start, len(text)):
                if text[i] == start_char:
                    depth += 1
                elif text[i] == end_char:
                    depth -= 1
                    if depth == 0:
                        try:
                            parsed = json.loads(text[start : i + 1])
                            if isinstance(parsed, dict):
                                return parsed
                        except json.JSONDecodeError:
                            break
        logger.info(f"Couldn't parse the json {text}")
        return {"stance": "ERROR", "reasoning": text[:2000], "confidence": 0.0}

    async def _retrieve_shared(self, debate_id: str, topic: str) -> list[dict]:
        if not self.memory:
            return []
        entries = await self.memory.search_shared(debate_id, topic, limit=10)
        return [{"content": e.content, **e.metadata} for e in entries]

    async def _retrieve_private(self, topic: str) -> list[dict]:
        if not self.memory:
            return []
        entries = await self.memory.search_private(self.card.agent_id, topic, limit=5)
        return [{"content": e.content, **e.metadata} for e in entries]

    def _build_messages(
        self,
        content: DebateContent,
        shared_history: list[dict],
        private_history: list[dict],
    ) -> list[dict]:
        messages: list[dict] = []

        if shared_history:
            history_text = "\n\n".join(
                f"[{h.get('agent_id', 'unknown')} ({h.get('phase', '?')}): {h.get('content', '')}]"
                for h in shared_history[-6:]
            )
            messages.append({"role": "assistant", "content": f"Previous debate history:\n{history_text}"})

        task_description = f"Debate topic: {content.topic}\nPhase: {content.phase.value}\nRound: {content.round}"
        if content.reasoning:
            task_description += f"\n\nCurrent argument to address:\n{content.reasoning}"
        if content.target_agent and content.target_agent != self.card.agent_id:
            task_description += f"\n\nThis is directed at you from {content.target_agent}."

        messages.append({"role": "user", "content": task_description})
        return messages
