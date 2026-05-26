from __future__ import annotations

import os
import uuid

from langfuse import Langfuse

_client: Langfuse | None = None


def get_client() -> Langfuse | None:
    global _client
    if _client is None:
        pubkey = os.getenv("LANGFUSE_PUBLIC_KEY")
        secret = os.getenv("LANGFUSE_SECRET_KEY")
        if pubkey and secret:
            host = os.getenv("LANGFUSE_BASE_URL") or os.getenv("LANGFUSE_HOST", "https://cloud.langfuse.com")
            _client = Langfuse(
                public_key=pubkey,
                secret_key=secret,
                host=host,
            )
    return _client


def enabled() -> bool:
    return get_client() is not None


def _make_trace_id() -> str:
    return uuid.uuid4().hex


class TraceContext:
    def __init__(self, name: str, metadata: dict | None = None, trace_id: str | None = None):
        self._client = get_client()
        self._name = name
        self._metadata = metadata or {}
        self._trace_id = trace_id or _make_trace_id()
        self._root = None

    def __enter__(self):
        if self._client:
            self._root = self._client.start_observation(
                name=self._name,
                trace_context={"trace_id": self._trace_id},
                metadata=self._metadata,
            )
        return self

    def __exit__(self, *args):
        if self._root:
            self._root.end()
        if self._client:
            self._client.flush()

    @property
    def trace_id(self) -> str:
        return self._trace_id

    def generation(self, name: str, model: str, input_data, output_data=None, usage: dict | None = None, **kwargs):
        if not self._client:
            return None
        return self._client.start_observation(
            name=name,
            as_type="generation",
            model=model,
            input=input_data,
            output=output_data,
            usage_details=usage,
            trace_context={"trace_id": self._trace_id},
            **kwargs,
        )

    def event(self, name: str, **kwargs):
        if not self._client:
            return None
        return self._client.create_event(
            name=name,
            trace_context={"trace_id": self._trace_id},
            **kwargs,
        )
