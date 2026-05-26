from __future__ import annotations

from src.agents.base import BaseAgent
from src.protocol.schemas import DebatePhase


class AnalystAgent(BaseAgent):
    def build_system_prompt(self, phase: DebatePhase, topic: str) -> str:
        base = self._system_prompt
        if phase == DebatePhase.OPENING:
            return f"{base}\n\nThis is the OPENING phase. Provide historical context and identify key patterns related to: {topic}"
        if phase == DebatePhase.REBUTTAL:
            return f"{base}\n\nThis is the REBUTTAL phase. Place other agents' arguments in broader context. What perspectives are missing?"
        if phase == DebatePhase.EVIDENCE:
            return f"{base}\n\nThis is the EVIDENCE phase. Contextualize the evidence presented. Identify patterns across arguments."
        if phase == DebatePhase.SYNTHESIS:
            return (
                f"{base}\n\nThis is the SYNTHESIS phase. Your primary role now. "
                "Synthesize all arguments into a coherent overview. Identify themes, "
                "areas of agreement, and irreconcilable differences."
            )
        if phase == DebatePhase.VERDICT:
            return (
                f"{base}\n\nThis is the VERDICT phase. Deliver the final synthesis. "
                "Provide a comprehensive verdict including consensus level, key claims, "
                "and remaining open questions."
            )
        return base
