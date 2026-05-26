from __future__ import annotations

import asyncio
import json
import logging
import os

import uvicorn
from fastapi import FastAPI, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import HTMLResponse
from pydantic import BaseModel
from sse_starlette.sse import EventSourceResponse

from src.messaging.nats_client import NATSClient
from src.orchestrator.agent_registry import AgentRegistry
from src.orchestrator.debate_manager import DebateManager

logger = logging.getLogger(__name__)

app = FastAPI(title="Debate Chamber Orchestrator")
app.add_middleware(CORSMiddleware, allow_origins=["*"], allow_methods=["*"], allow_headers=["*"])

nats_client = NATSClient(servers=[os.getenv("NATS_URL", "nats://localhost:4222")])
registry = AgentRegistry()
debate_manager: DebateManager | None = None


class StartDebateRequest(BaseModel):
    topic: str


@app.on_event("startup")
async def startup() -> None:
    global debate_manager
    await nats_client.connect()
    debate_manager = DebateManager(nats_client, registry.get_agent_ids())
    await debate_manager.start_response_collector()
    logger.info("Orchestrator started")


@app.on_event("shutdown")
async def shutdown() -> None:
    await nats_client.close()


@app.get("/")
async def health() -> dict:
    return {"status": "running", "service": "orchestrator"}


@app.get("/agents")
async def list_agents() -> list[dict]:
    return [card.model_dump() for card in registry.list_cards()]


@app.post("/debate/start")
async def start_debate(request: StartDebateRequest) -> dict:
    debate_id = await debate_manager.create_debate(request.topic)
    asyncio.create_task(debate_manager.run_debate(debate_id))
    return {"debate_id": debate_id, "topic": request.topic, "stream_url": f"/debate/{debate_id}/stream"}


@app.get("/debate/{debate_id}/status")
async def debate_status(debate_id: str) -> dict:
    session = debate_manager.get_session(debate_id)
    if not session:
        return {"error": "Debate not found"}
    return session.model_dump()


@app.get("/debate/{debate_id}/responses")
async def debate_responses(debate_id: str) -> dict:
    session = debate_manager.get_session(debate_id)
    if not session:
        return {"error": "Debate not found"}
    return {"debate_id": debate_id, "state": session.state.value, "phase": session.phase.value, "responses": session.responses}


@app.get("/monitor/messages")
async def monitor_messages(limit: int = 100) -> list[dict]:
    return debate_manager.get_message_log(limit)


@app.get("/monitor", response_class=HTMLResponse)
async def monitor_page() -> str:
    return """<!DOCTYPE html>
<html>
<head>
<title>Debate Chamber - NATS Monitor</title>
<style>
body { font-family: monospace; background: #1a1a2e; color: #e0e0e0; margin: 0; padding: 20px; }
h1 { color: #00d4ff; }
#controls { margin-bottom: 15px; }
#controls input, #controls button { padding: 6px 12px; font-size: 14px; }
table { width: 100%; border-collapse: collapse; }
th { text-align: left; color: #00d4ff; border-bottom: 1px solid #333; padding: 8px; }
td { border-bottom: 1px solid #222; padding: 6px 8px; font-size: 13px; }
tr:hover { background: #16213e; }
.dir-in { color: #4ecdc4; }
.dir-out { color: #ff6b6b; }
.auto-refresh { color: #888; font-size: 12px; }
</style>
</head>
<body>
<h1>NATS Message Monitor</h1>
<div id="controls">
  <label class="auto-refresh">Auto-refresh:
    <input type="checkbox" id="autoRefresh" checked onchange="toggleRefresh()">
  </label>
  <span id="count" class="auto-refresh"></span>
</div>
<table>
<thead><tr><th>Time</th><th>Dir</th><th>Type</th><th>Subject</th><th>From</th><th>To</th><th>Debate</th></tr></thead>
<tbody id="messages"></tbody>
</table>
<script>
let interval = null;
function fetchMessages() {
  fetch('/monitor/messages?limit=100')
    .then(r => r.json())
    .then(data => {
      document.getElementById('count').textContent = data.length + ' messages';
      const tbody = document.getElementById('messages');
      tbody.innerHTML = data.reverse().map(m =>
        '<tr><td>' + m.timestamp.slice(11,19) + '</td>' +
        '<td class="dir-' + m.direction + '">' + m.direction.toUpperCase() + '</td>' +
        '<td>' + m.message_type + '</td>' +
        '<td>' + m.subject + '</td>' +
        '<td>' + m.sender + '</td>' +
        '<td>' + m.recipient + '</td>' +
        '<td>' + m.task_id + '</td></tr>'
      ).join('');
    });
}
function toggleRefresh() {
  if (document.getElementById('autoRefresh').checked) {
    interval = setInterval(fetchMessages, 2000);
  } else {
    clearInterval(interval);
  }
}
fetchMessages();
toggleRefresh();
</script>
</body>
</html>"""


@app.get("/debate/{debate_id}/stream")
async def debate_stream(debate_id: str, request: Request) -> EventSourceResponse:
    queue = debate_manager.subscribe_events(debate_id)

    async def event_generator():
        try:
            while True:
                if await request.is_disconnected():
                    break
                try:
                    event = await asyncio.wait_for(queue.get(), timeout=30.0)
                    yield {"data": event.model_dump_json()}
                except asyncio.TimeoutError:
                    yield {"event": "ping", "data": ""}
        finally:
            debate_manager.unsubscribe_events(debate_id, queue)

    return EventSourceResponse(event_generator())


def main() -> None:
    logging.basicConfig(level=logging.INFO)
    uvicorn.run(app, host="0.0.0.0", port=8000)


if __name__ == "__main__":
    main()
