from __future__ import annotations

import uuid
from datetime import datetime, timezone
from enum import Enum

from pydantic import BaseModel, Field


class MessageType(str, Enum):
    TASK_CREATE = "TASK_CREATE"
    TASK_MESSAGE = "TASK_MESSAGE"
    TASK_COMPLETE = "TASK_COMPLETE"
    TASK_ERROR = "TASK_ERROR"
    EVENT = "EVENT"


class TaskState(str, Enum):
    CREATED = "CREATED"
    RUNNING = "RUNNING"
    COMPLETED = "COMPLETED"
    FAILED = "FAILED"


class DebatePhase(str, Enum):
    OPENING = "OPENING"
    REBUTTAL = "REBUTTAL"
    EVIDENCE = "EVIDENCE"
    SYNTHESIS = "SYNTHESIS"
    VERDICT = "VERDICT"


PHASE_ORDER = list(DebatePhase)


class MessageHeader(BaseModel):
    message_id: str = Field(default_factory=lambda: str(uuid.uuid4()))
    message_type: MessageType
    sender: str
    recipient: str
    correlation_id: str
    task_id: str
    timestamp: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))
    metadata: dict = Field(default_factory=dict)


class ACPEnvelope(BaseModel):
    header: MessageHeader
    body: dict


class DebateContent(BaseModel):
    topic: str
    phase: DebatePhase
    round: int
    stance: str | None = None
    reasoning: str = ""
    confidence: float = 0.0
    evidence_refs: list[str] = Field(default_factory=list)
    target_agent: str | None = None
    challenges: list[str] = Field(default_factory=list)
    fallacies_detected: list[str] = Field(default_factory=list)
    verified_claims: list[str] = Field(default_factory=list)
    disputed_claims: list[str] = Field(default_factory=list)
    evidence_quality: str | None = None
    patterns_identified: list[str] = Field(default_factory=list)
    context_provided: list[str] = Field(default_factory=list)
    synthesis: str | None = None


class VerdictContent(BaseModel):
    summary: str
    consensus_level: float
    key_claims: list[str] = Field(default_factory=list)
    open_questions: list[str] = Field(default_factory=list)
    agent_verdicts: dict[str, dict] = Field(default_factory=dict)


class DebateSession(BaseModel):
    debate_id: str
    topic: str
    phase: DebatePhase = DebatePhase.OPENING
    current_round: int = 1
    state: TaskState = TaskState.CREATED
    agents: list[str] = Field(default_factory=list)
    responses: dict[str, list[dict]] = Field(default_factory=dict)


def make_envelope(
    message_type: MessageType,
    sender: str,
    recipient: str,
    task_id: str,
    body: dict,
    correlation_id: str | None = None,
    metadata: dict | None = None,
) -> ACPEnvelope:
    return ACPEnvelope(
        header=MessageHeader(
            message_type=message_type,
            sender=sender,
            recipient=recipient,
            correlation_id=correlation_id or str(uuid.uuid4()),
            task_id=task_id,
            metadata=metadata or {},
        ),
        body=body,
    )


def nats_subject_agent(debate_id: str, agent_id: str) -> str:
    return f"debate.{debate_id}.agent.{agent_id}"


def nats_subject_responses(debate_id: str) -> str:
    return f"debate.{debate_id}.responses"


def nats_subject_events(debate_id: str) -> str:
    return f"debate.{debate_id}.events"
