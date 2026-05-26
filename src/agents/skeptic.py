from __future__ import annotations

from src.agents.base import BaseAgent
from src.protocol.schemas import DebatePhase


class SkepticAgent(BaseAgent):
    def build_system_prompt(self, phase: DebatePhase, topic: str) -> str:
        base = self._system_prompt
        if phase == DebatePhase.OPENING:
            return f"{base}\n\nThis is the OPENING phase. Provide your initial skeptical analysis of the topic: {topic}"
        if phase == DebatePhase.REBUTTAL:
            return f"{base}\n\nThis is the REBUTTAL phase. Challenge the arguments presented by other agents. Be specific about weaknesses."
        if phase == DebatePhase.EVIDENCE:
            return f"{base}\n\nThis is the EVIDENCE phase. Evaluate the evidence presented. Is it sufficient? Are there gaps?"
        if phase == DebatePhase.SYNTHESIS:
            return f"{base}\n\nThis is the SYNTHESIS phase. Summarize your key concerns and areas where arguments remain weak."
        if phase == DebatePhase.VERDICT:
            return f"{base}\n\nThis is the VERDICT phase. Give your final assessment with a clear stance and confidence level."
        return base
