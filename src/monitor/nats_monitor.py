from __future__ import annotations

import asyncio
import json
import logging
import os
import uuid
from collections import deque
from datetime import datetime, timezone

import nats
import uvicorn
from fastapi import FastAPI, Request, WebSocket, WebSocketDisconnect
from fastapi.responses import HTMLResponse
from fastapi.middleware.cors import CORSMiddleware

logger = logging.getLogger(__name__)

app = FastAPI(title="NATS Monitor")
app.add_middleware(CORSMiddleware, allow_origins=["*"], allow_methods=["*"], allow_headers=["*"])

NATS_URL = os.getenv("NATS_URL", "nats://localhost:4222")
MAX_MESSAGES = 1000

# Shared state
_messages: deque[dict] = deque(maxlen=MAX_MESSAGES)
_websockets: list[WebSocket] = []
_nc = None


async def _nats_listener():
    global _nc
    try:
        _nc = await nats.connect(servers=[NATS_URL])
        logger.info("Connected to NATS at %s", NATS_URL)

        async def handler(msg):
            try:
                data = json.loads(msg.data.decode())
                entry = {
                    "id": str(uuid.uuid4())[:8],
                    "timestamp": datetime.now(timezone.utc).isoformat(),
                    "subject": msg.subject,
                    "data": data,
                }
                _messages.append(entry)
                dead = []
                for ws in _websockets:
                    try:
                        await ws.send_json(entry)
                    except Exception:
                        dead.append(ws)
                for ws in dead:
                    _websockets.remove(ws)
            except Exception as e:
                logger.error("Error processing message: %s", e)

        await _nc.subscribe(">", cb=handler)
        logger.info("NATS monitor subscribed to all subjects")
    except Exception as e:
        logger.error("NATS listener failed: %s", e)


@app.on_event("startup")
async def startup():
    asyncio.create_task(_nats_listener())
    logger.info("NATS Monitor started")


@app.on_event("shutdown")
async def shutdown():
    if _nc:
        await _nc.close()


@app.get("/api/messages")
async def get_messages(limit: int = 100):
    msgs = list(_messages)
    return list(reversed(msgs[-limit:]))


@app.get("/api/stats")
async def get_stats():
    return {
        "total_messages": len(_messages),
        "connected_clients": len(_websockets),
    }


@app.websocket("/ws")
async def websocket_endpoint(ws: WebSocket):
    await ws.accept()
    _websockets.append(ws)
    try:
        while True:
            await ws.receive_text()
    except WebSocketDisconnect:
        pass
    finally:
        if ws in _websockets:
            _websockets.remove(ws)


@app.get("/", response_class=HTMLResponse)
async def index():
    return """<!DOCTYPE html>
<html lang="en">
<head>
<meta charset="UTF-8">
<meta name="viewport" content="width=device-width, initial-scale=1.0">
<title>Debate Chamber - NATS Monitor</title>
<style>
* { box-sizing: border-box; margin: 0; padding: 0; }
body { font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, monospace; background: #0d1117; color: #c9d1d9; }
.header { background: #161b22; border-bottom: 1px solid #30363d; padding: 12px 20px; display: flex; justify-content: space-between; align-items: center; position: sticky; top: 0; z-index: 10; }
.header h1 { font-size: 16px; color: #58a6ff; }
.header .stats { display: flex; gap: 16px; font-size: 13px; color: #8b949e; }
.header .stats .val { color: #58a6ff; font-weight: bold; }
.toolbar { background: #161b22; border-bottom: 1px solid #30363d; padding: 8px 20px; display: flex; gap: 12px; align-items: center; }
.toolbar input { background: #0d1117; border: 1px solid #30363d; color: #c9d1d9; padding: 6px 10px; border-radius: 4px; font-size: 13px; width: 300px; }
.toolbar input:focus { outline: none; border-color: #58a6ff; }
.toolbar button { background: #21262d; border: 1px solid #30363d; color: #c9d1d9; padding: 6px 12px; border-radius: 4px; cursor: pointer; font-size: 13px; }
.toolbar button:hover { background: #30363d; }
.toolbar button.active { background: #238636; border-color: #238636; color: #fff; }
.toolbar .count { color: #8b949e; font-size: 13px; margin-left: auto; }
.messages { padding: 0; overflow-y: auto; height: calc(100vh - 90px); }
.msg { border-bottom: 1px solid #21262d; padding: 10px 20px; font-size: 13px; transition: background 0.2s; }
.msg:hover { background: #161b22; }
.msg-header { display: flex; gap: 12px; align-items: center; margin-bottom: 6px; }
.msg-time { color: #8b949e; font-size: 11px; min-width: 70px; }
.msg-subject { color: #58a6ff; font-weight: 500; }
.msg-type { padding: 2px 6px; border-radius: 3px; font-size: 11px; font-weight: 500; }
.msg-type.TASK_CREATE { background: #1f6feb33; color: #58a6ff; }
.msg-type.TASK_MESSAGE { background: #23863633; color: #3fb950; }
.msg-type.TASK_COMPLETE { background: #8957e533; color: #a371f7; }
.msg-type.TASK_ERROR { background: #da363333; color: #f85149; }
.msg-type.EVENT { background: #9e6a0333; color: #d29922; }
.msg-sender { color: #f0883e; font-size: 12px; }
.msg-arrow { color: #484f58; }
.msg-recipient { color: #3fb950; font-size: 12px; }
.msg-debate { color: #8b949e; font-size: 11px; margin-left: auto; }
.msg-body { background: #161b22; border-radius: 4px; padding: 8px 10px; font-size: 12px; color: #8b949e; max-height: 120px; overflow-y: auto; white-space: pre-wrap; word-break: break-all; cursor: pointer; }
.msg-body.expanded { max-height: none; }
.empty { text-align: center; padding: 60px; color: #484f58; }
.empty h2 { margin-bottom: 8px; color: #30363d; }
.new-msg { animation: flash 1s ease-out; }
@keyframes flash { 0% { background: #1f6feb22; } 100% { background: transparent; } }
</style>
</head>
<body>

<div class="header">
  <h1>NATS Message Monitor</h1>
  <div class="stats">
    Messages: <span class="val" id="msgCount">0</span>
    &nbsp;|&nbsp; Connected: <span class="val" id="wsStatus">connecting...</span>
  </div>
</div>

<div class="toolbar">
  <input type="text" id="filter" placeholder="Filter by subject, agent, or message type...">
  <button id="btnPause" onclick="togglePause()">Pause</button>
  <button id="btnClear" onclick="clearMessages()">Clear</button>
  <button id="btnExpand" onclick="toggleExpand()">Expand All</button>
  <span class="count" id="filterCount"></span>
</div>

<div class="messages" id="messages">
  <div class="empty"><h2>Waiting for messages...</h2><p>Start a debate to see NATS traffic here</p></div>
</div>

<script>
let allMsgs = [];
let paused = false;
let expandAll = false;
let ws;
let reconnectDelay = 1000;

function connect() {
  const proto = location.protocol === 'https:' ? 'wss:' : 'ws:';
  ws = new WebSocket(proto + '//' + location.host + '/ws');
  ws.onopen = () => {
    document.getElementById('wsStatus').textContent = 'live';
    document.getElementById('wsStatus').style.color = '#3fb950';
    reconnectDelay = 1000;
  };
  ws.onmessage = (e) => {
    if (paused) return;
    const msg = JSON.parse(e.data);
    allMsgs.unshift(msg);
    if (allMsgs.length > 500) allMsgs.length = 500;
    document.getElementById('msgCount').textContent = allMsgs.length;
    renderMsg(msg, true);
    removeEmpty();
  };
  ws.onclose = () => {
    document.getElementById('wsStatus').textContent = 'reconnecting...';
    document.getElementById('wsStatus').style.color = '#d29922';
    setTimeout(connect, reconnectDelay);
    reconnectDelay = Math.min(reconnectDelay * 2, 10000);
  };
  ws.onerror = () => ws.close();
}

function removeEmpty() {
  const el = document.querySelector('.empty');
  if (el) el.remove();
}

function renderMsg(msg, isNew) {
  const container = document.getElementById('messages');
  const filter = document.getElementById('filter').value.toLowerCase();
  const header = msg.data?.header || {};
  const body = msg.data?.body || {};
  const msgType = header.message_type || '';
  const sender = header.sender || '';
  const recipient = header.recipient || '';
  const debateId = header.task_id || '';
  const eventType = body.event_type || '';

  const searchText = (msg.subject + ' ' + msgType + ' ' + sender + ' ' + recipient + ' ' + debateId + ' ' + eventType).toLowerCase();
  if (filter && !searchText.includes(filter)) return;

  const div = document.createElement('div');
  div.className = 'msg' + (isNew ? ' new-msg' : '');
  const bodyStr = JSON.stringify(msg.data?.body || {}, null, 2);
  const shortBody = bodyStr.length > 300 ? bodyStr.substring(0, 300) + '...' : bodyStr;

  div.innerHTML = `
    <div class="msg-header">
      <span class="msg-time">${msg.timestamp?.slice(11,19) || ''}</span>
      <span class="msg-subject">${msg.subject}</span>
      ${msgType ? '<span class="msg-type ' + msgType + '">' + msgType + '</span>' : ''}
      <span class="msg-sender">${sender}</span>
      <span class="msg-arrow">→</span>
      <span class="msg-recipient">${recipient}</span>
      ${debateId ? '<span class="msg-debate">debate: ' + debateId + '</span>' : ''}
    </div>
    <div class="msg-body" onclick="this.classList.toggle('expanded')" class="${expandAll ? 'expanded' : ''}">${escapeHtml(expandAll ? bodyStr : shortBody)}</div>
  `;
  container.insertBefore(div, container.firstChild);

  // Limit DOM nodes
  while (container.children.length > 200) {
    container.removeChild(container.lastChild);
  }
}

function escapeHtml(text) {
  const d = document.createElement('div');
  d.textContent = text;
  return d.innerHTML;
}

function togglePause() {
  paused = !paused;
  const btn = document.getElementById('btnPause');
  btn.textContent = paused ? 'Resume' : 'Pause';
  btn.classList.toggle('active', paused);
}

function clearMessages() {
  allMsgs = [];
  document.getElementById('messages').innerHTML = '<div class="empty"><h2>Messages cleared</h2><p>Waiting for new messages...</p></div>';
  document.getElementById('msgCount').textContent = '0';
}

function toggleExpand() {
  expandAll = !expandAll;
  const btn = document.getElementById('btnExpand');
  btn.classList.toggle('active', expandAll);
}

// Filter
document.getElementById('filter').addEventListener('input', function() {
  const container = document.getElementById('messages');
  container.innerHTML = '';
  const filter = this.value.toLowerCase();
  let count = 0;
  for (const msg of allMsgs) {
    renderMsg(msg, false);
    count++;
  }
  document.getElementById('filterCount').textContent = filter ? count + ' shown' : '';
});

// Load history on startup
fetch('/api/messages?limit=50').then(r => r.json()).then(msgs => {
  msgs.reverse().forEach(m => { allMsgs.push(m); renderMsg(m, false); });
  document.getElementById('msgCount').textContent = allMsgs.length;
  removeEmpty();
});

connect();
</script>
</body>
</html>"""


def main():
    logging.basicConfig(level=logging.INFO)
    uvicorn.run(app, host="0.0.0.0", port=8080)


if __name__ == "__main__":
    main()
