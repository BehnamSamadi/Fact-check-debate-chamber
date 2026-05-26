from __future__ import annotations

from src.protocol.agent_card import AgentCard

DEFAULT_AGENT_CARDS = {
    "skeptic": AgentCard(
        agent_id="skeptic",
        name="Skeptic Agent",
        description="Challenges claims, identifies logical fallacies, and questions assumptions",
        capabilities=["challenge_claims", "detect_fallacies", "assess_evidence_quality", "identify_biases"],
        domains=["general", "science", "politics", "technology"],
    ),
    "researcher": AgentCard(
        agent_id="researcher",
        name="Researcher Agent",
        description="Validates evidence, checks facts, and assesses source credibility",
        capabilities=["validate_evidence", "fact_check", "assess_source_credibility", "cross_reference"],
        domains=["general", "science", "politics", "technology"],
    ),
    "analyst": AgentCard(
        agent_id="analyst",
        name="Analyst Agent",
        description="Provides historical context, identifies patterns, and synthesizes arguments",
        capabilities=["provide_context", "identify_patterns", "synthesize_arguments", "historical_analysis"],
        domains=["general", "science", "politics", "technology"],
    ),
}


class AgentRegistry:
    def __init__(self, cards: dict[str, AgentCard] | None = None):
        self._cards = cards or DEFAULT_AGENT_CARDS

    def get_card(self, agent_id: str) -> AgentCard | None:
        return self._cards.get(agent_id)

    def list_cards(self) -> list[AgentCard]:
        return list(self._cards.values())

    def get_agent_ids(self) -> list[str]:
        return list(self._cards.keys())
