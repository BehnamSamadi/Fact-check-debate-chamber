from __future__ import annotations

import asyncio
import json
import logging
import uuid

from src.messaging.nats_client import NATSClient
from src.protocol.schemas import (
    ACPEnvelope,
    DebateContent,
    DebatePhase,
    DebateSession,
    MessageType,
    PHASE_ORDER,
    TaskState,
    make_envelope,
    nats_subject_agent,
    nats_subject_events,
    nats_subject_responses,
)

logger = logging.getLogger(__name__)


class DebateManager:
    def __init__(self, nats: NATSClient, agent_ids: list[str] | None = None):
        self._nats = nats
        self._sessions: dict[str, DebateSession] = {}
        self._event_queues: dict[str, list[asyncio.Queue]] = {}
        self._default_agents = agent_ids or ["skeptic", "researcher", "analyst"]
        self._pending_responses: dict[str, asyncio.Future[ACPEnvelope]] = {}
        self._response_collector_task: asyncio.Task | None = None
        self._message_log: list[dict] = []
        self._max_log = 500

    async def start_response_collector(self) -> None:
        await self._nats.subscribe("debate.*.responses", self._handle_agent_response)

    async def _handle_agent_response(self, envelope: ACPEnvelope) -> None:
        self._message_log.append({
            "timestamp": envelope.header.timestamp.isoformat(),
            "subject": "debate.*.responses",
            "direction": "in",
            "message_type": envelope.header.message_type.value,
            "sender": envelope.header.sender,
            "recipient": envelope.header.recipient,
            "task_id": envelope.header.task_id,
        })
        if len(self._message_log) > self._max_log:
            self._message_log = self._message_log[-self._max_log:]

        key = envelope.header.correlation_id
        future = self._pending_responses.get(key)
        if future and not future.done():
            future.set_result(envelope)
        else:
            debate_id = envelope.header.task_id
            phase = envelope.body.get("phase", "UNKNOWN")
            agent_id = envelope.header.sender
            self._store_response(debate_id, phase, envelope.body)
            await self._emit_event(debate_id, "agent_response", envelope.body)

    def _store_response(self, debate_id: str, phase: str, response: dict) -> None:
        session = self._sessions.get(debate_id)
        if session:
            if phase not in session.responses:
                session.responses[phase] = []
            session.responses[phase].append(response)

    async def create_debate(self, topic: str) -> str:
        debate_id = str(uuid.uuid4())[:8]
        session = DebateSession(
            debate_id=debate_id,
            topic=topic,
            agents=list(self._default_agents),
        )
        self._sessions[debate_id] = session
        self._event_queues[debate_id] = []
        logger.info("Created debate %s: %s", debate_id, topic)
        return debate_id

    async def run_debate(self, debate_id: str) -> None:
        session = self._sessions.get(debate_id)
        if not session:
            raise ValueError(f"Debate {debate_id} not found")

        session.state = TaskState.RUNNING
        await self._emit_event(debate_id, "debate_started", {"topic": session.topic, "debate_id": debate_id})

        for phase in PHASE_ORDER:
            session.phase = phase
            await self._emit_event(debate_id, "phase_started", {"phase": phase.value})

            try:
                await self._run_phase(session, phase)
            except Exception as e:
                logger.error("Phase %s failed for debate %s: %s", phase, debate_id, e)
                session.state = TaskState.FAILED
                await self._emit_event(debate_id, "debate_failed", {"error": str(e)})
                return

            await self._emit_event(debate_id, "phase_completed", {
                "phase": phase.value,
                "responses": session.responses.get(phase.value, []),
            })

        session.state = TaskState.COMPLETED
        await self._emit_event(debate_id, "debate_completed", {
            "debate_id": debate_id,
            "all_responses": {k: v for k, v in session.responses.items()},
        })

    async def _run_phase(self, session: DebateSession, phase: DebatePhase) -> None:
        tasks = []
        for agent_id in session.agents:
            content = DebateContent(
                topic=session.topic,
                phase=phase,
                round=session.current_round,
            )
            envelope = make_envelope(
                message_type=MessageType.TASK_CREATE,
                sender="orchestrator",
                recipient=agent_id,
                task_id=session.debate_id,
                body=content.model_dump(),
            )
            tasks.append(self._send_and_collect(session.debate_id, agent_id, envelope))

        responses = await asyncio.gather(*tasks, return_exceptions=True)
        for resp in responses:
            if isinstance(resp, Exception):
                logger.error("Agent response error: %s", resp)
            elif isinstance(resp, ACPEnvelope):
                self._store_response(session.debate_id, phase.value, resp.body)

        session.current_round += 1

    async def _send_and_collect(
        self, debate_id: str, agent_id: str, envelope: ACPEnvelope
    ) -> ACPEnvelope:
        correlation_id = envelope.header.correlation_id
        future: asyncio.Future[ACPEnvelope] = asyncio.get_event_loop().create_future()
        self._pending_responses[correlation_id] = future

        subject = nats_subject_agent(debate_id, agent_id)
        self._log_outgoing(subject, envelope)
        await self._nats.publish(subject, envelope)

        try:
            response = await asyncio.wait_for(future, timeout=120.0)
            return response
        except asyncio.TimeoutError:
            logger.error("Timeout waiting for %s in debate %s", agent_id, debate_id)
            raise
        finally:
            self._pending_responses.pop(correlation_id, None)

    async def _emit_event(self, debate_id: str, event_type: str, data: dict) -> None:
        event = make_envelope(
            message_type=MessageType.EVENT,
            sender="orchestrator",
            recipient="broadcast",
            task_id=debate_id,
            body={"event_type": event_type, **data},
        )
        subject = nats_subject_events(debate_id)
        self._log_outgoing(subject, event)
        await self._nats.publish(subject, event)

        for queue in self._event_queues.get(debate_id, []):
            await queue.put(event)

    def subscribe_events(self, debate_id: str) -> asyncio.Queue:
        queue: asyncio.Queue[ACPEnvelope] = asyncio.Queue()
        if debate_id not in self._event_queues:
            self._event_queues[debate_id] = []
        self._event_queues[debate_id].append(queue)
        return queue

    def unsubscribe_events(self, debate_id: str, queue: asyncio.Queue) -> None:
        queues = self._event_queues.get(debate_id, [])
        if queue in queues:
            queues.remove(queue)

    def get_session(self, debate_id: str) -> DebateSession | None:
        return self._sessions.get(debate_id)

    def _log_outgoing(self, subject: str, envelope: ACPEnvelope) -> None:
        self._message_log.append({
            "timestamp": envelope.header.timestamp.isoformat(),
            "subject": subject,
            "direction": "out",
            "message_type": envelope.header.message_type.value,
            "sender": envelope.header.sender,
            "recipient": envelope.header.recipient,
            "task_id": envelope.header.task_id,
        })
        if len(self._message_log) > self._max_log:
            self._message_log = self._message_log[-self._max_log:]

    def get_message_log(self, limit: int = 100) -> list[dict]:
        return self._message_log[-limit:]
