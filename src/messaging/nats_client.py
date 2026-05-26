from __future__ import annotations

import json
import logging
from collections.abc import Awaitable, Callable

import nats
from nats.js import JetStreamContext

from src.protocol.schemas import ACPEnvelope

logger = logging.getLogger(__name__)


class NATSClient:
    def __init__(self, servers: list[str] | None = None):
        self._servers = servers or ["nats://localhost:4222"]
        self._nc: nats.NATS | None = None
        self._js: JetStreamContext | None = None

    async def connect(self) -> None:
        self._nc = await nats.connect(servers=self._servers)
        self._js = self._nc.jetstream()
        logger.info("Connected to NATS at %s", self._servers)

    async def close(self) -> None:
        if self._nc:
            await self._nc.close()
            self._nc = None
            self._js = None

    async def publish(self, subject: str, envelope: ACPEnvelope) -> None:
        if not self._nc:
            raise RuntimeError("NATS not connected")
        payload = envelope.model_dump_json().encode()
        await self._nc.publish(subject, payload)
        logger.debug("Published to %s: %s", subject, envelope.header.message_type)

    async def subscribe(
        self, subject: str, handler: Callable[[ACPEnvelope], Awaitable[None]], queue: str | None = None
    ) -> None:
        if not self._nc:
            raise RuntimeError("NATS not connected")

        async def _callback(msg: nats.aio.msg.Msg) -> None:
            data = json.loads(msg.data.decode())
            envelope = ACPEnvelope.model_validate(data)
            await handler(envelope)

        await self._nc.subscribe(subject, cb=_callback)
        logger.info("Subscribed to %s", subject)

    async def request(self, subject: str, envelope: ACPEnvelope, timeout: float = 120.0) -> ACPEnvelope:
        if not self._nc:
            raise RuntimeError("NATS not connected")
        payload = envelope.model_dump_json().encode()
        response = await self._nc.request(subject, payload, timeout=timeout)
        data = json.loads(response.data.decode())
        return ACPEnvelope.model_validate(data)
