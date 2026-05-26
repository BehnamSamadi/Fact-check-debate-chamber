from __future__ import annotations

from src.agents.base import BaseAgent
from src.protocol.schemas import DebatePhase


class ResearcherAgent(BaseAgent):
    def build_system_prompt(self, phase: DebatePhase, topic: str) -> str:
        base = self._system_prompt
        if phase == DebatePhase.OPENING:
            return f"{base}\n\nThis is the OPENING phase. Provide your initial fact-check and evidence assessment for: {topic}"
        if phase == DebatePhase.REBUTTAL:
            return f"{base}\n\nThis is the REBUTTAL phase. Verify or dispute the factual claims made by other agents."
        if phase == DebatePhase.EVIDENCE:
            return f"{base}\n\nThis is the EVIDENCE phase. Present and validate the strongest available evidence. Rate evidence quality."
        if phase == DebatePhase.SYNTHESIS:
            return f"{base}\n\nThis is the SYNTHESIS phase. Summarize which claims are verified, disputed, or unverified."
        if phase == DebatePhase.VERDICT:
            return f"{base}\n\nThis is the VERDICT phase. Give your final evidence-based assessment with verification status."
        return base
