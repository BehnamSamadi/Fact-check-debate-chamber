from __future__ import annotations

import json

from src.protocol.schemas import (
    DebateContent,
    DebatePhase,
    DebateSession,
    MessageType,
    TaskState,
    make_envelope,
)


def test_session_creation():
    session = DebateSession(
        debate_id="test123",
        topic="Is AI beneficial?",
        agents=["skeptic", "researcher", "analyst"],
    )
    assert session.debate_id == "test123"
    assert session.phase == DebatePhase.OPENING
    assert session.state == TaskState.CREATED
    assert session.current_round == 1
    assert len(session.agents) == 3


def test_session_serialization():
    session = DebateSession(
        debate_id="test123",
        topic="Test topic",
        agents=["skeptic"],
    )
    data = session.model_dump()
    restored = DebateSession.model_validate(data)
    assert restored.debate_id == session.debate_id
    assert restored.topic == session.topic


def test_debate_content_phases():
    for phase in DebatePhase:
        content = DebateContent(topic="test", phase=phase, round=1)
        assert content.phase == phase
