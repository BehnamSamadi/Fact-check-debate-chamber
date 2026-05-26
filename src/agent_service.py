from __future__ import annotations

import logging
import os

import uvicorn
from fastapi import FastAPI

from src.factory.agent_factory import AgentFactory
from src.memory.qdrant_memory import QdrantMemory
from src.messaging.nats_client import NATSClient
from src.protocol.schemas import ACPEnvelope, MessageType, make_envelope, nats_subject_responses

logger = logging.getLogger(__name__)

app = FastAPI(title="Agent Service")

agent = None
nats_client: NATSClient | None = None


@app.on_event("startup")
async def startup() -> None:
    global agent, nats_client

    config_path = os.environ.get("AGENT_CONFIG")
    if not config_path:
        raise RuntimeError("AGENT_CONFIG environment variable not set")

    qdrant_url = os.getenv("QDRANT_URL", "http://localhost:6333")
    memory = QdrantMemory(url=qdrant_url)

    factory = AgentFactory(memory=memory)
    agent = factory.build(config_path)

    nats_client = NATSClient(servers=[os.getenv("NATS_URL", "nats://localhost:4222")])
    await nats_client.connect()

    subject = f"debate.*.agent.{agent.card.agent_id}"
    await nats_client.subscribe(subject, handle_message)
    logger.info("Agent %s started, listening on %s", agent.card.agent_id, subject)


async def handle_message(envelope: ACPEnvelope) -> None:
    if envelope.header.message_type != MessageType.TASK_CREATE:
        return

    debate_id = envelope.header.task_id
    response_subject = nats_subject_responses(debate_id)

    try:
        response = await agent.process_message(envelope)
        await nats_client.publish(response_subject, response)
        logger.info("Agent %s responded in debate %s", agent.card.agent_id, debate_id)
    except Exception as e:
        logger.error("Agent %s error: %s", agent.card.agent_id, e)
        error_response = make_envelope(
            message_type=MessageType.TASK_ERROR,
            sender=agent.card.agent_id,
            recipient="orchestrator",
            task_id=debate_id,
            body={"error": str(e)},
            correlation_id=envelope.header.correlation_id,
        )
        await nats_client.publish(response_subject, error_response)


@app.get("/")
async def health() -> dict:
    if agent:
        return {"status": "running", "agent": agent.card.model_dump()}
    return {"status": "starting"}


@app.on_event("shutdown")
async def shutdown() -> None:
    if nats_client:
        await nats_client.close()


def main() -> None:
    logging.basicConfig(level=logging.INFO)
    uvicorn.run(app, host="0.0.0.0", port=8000)


if __name__ == "__main__":
    main()
