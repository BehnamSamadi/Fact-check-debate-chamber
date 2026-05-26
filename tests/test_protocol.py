from __future__ import annotations

import json

from src.protocol.schemas import (
    ACPEnvelope,
    DebateContent,
    DebatePhase,
    MessageHeader,
    MessageType,
    PHASE_ORDER,
    TaskState,
    make_envelope,
)


def test_make_envelope():
    env = make_envelope(
        message_type=MessageType.TASK_CREATE,
        sender="orchestrator",
        recipient="skeptic",
        task_id="debate123",
        body={"topic": "test topic"},
    )
    assert env.header.message_type == MessageType.TASK_CREATE
    assert env.header.sender == "orchestrator"
    assert env.header.recipient == "skeptic"
    assert env.header.task_id == "debate123"
    assert env.body["topic"] == "test topic"


def test_envelope_serialization():
    env = make_envelope(
        message_type=MessageType.TASK_MESSAGE,
        sender="skeptic",
        recipient="orchestrator",
        task_id="debate123",
        body={"stance": "SKEPTICAL"},
        correlation_id="corr-1",
    )
    data = env.model_dump_json()
    parsed = ACPEnvelope.model_validate_json(data)
    assert parsed.header.correlation_id == "corr-1"
    assert parsed.body["stance"] == "SKEPTICAL"


def test_debate_content():
    content = DebateContent(
        topic="Test topic",
        phase=DebatePhase.OPENING,
        round=1,
        reasoning="Test reasoning",
        confidence=0.8,
    )
    data = content.model_dump()
    assert data["phase"] == "OPENING"
    assert data["round"] == 1
    restored = DebateContent.model_validate(data)
    assert restored.topic == content.topic


def test_phase_order():
    assert PHASE_ORDER == [
        DebatePhase.OPENING,
        DebatePhase.REBUTTAL,
        DebatePhase.EVIDENCE,
        DebatePhase.SYNTHESIS,
        DebatePhase.VERDICT,
    ]


def test_task_states():
    assert TaskState.CREATED.value == "CREATED"
    assert TaskState.RUNNING.value == "RUNNING"
    assert TaskState.COMPLETED.value == "COMPLETED"
    assert TaskState.FAILED.value == "FAILED"


def test_message_types():
    types = [t.value for t in MessageType]
    assert "TASK_CREATE" in types
    assert "TASK_MESSAGE" in types
    assert "TASK_COMPLETE" in types
    assert "TASK_ERROR" in types
    assert "EVENT" in types
