# Debate Chamber

Multi-agent LLM deliberation system for collaborative fact-checking and deliberation.

## Quick Start

```bash
# Start infrastructure
docker compose up nats qdrant

# In separate terminals:
python -m src.orchestrator.main
AGENT_CONFIG=config/agents/skeptic.yaml python -m src.agent_service
AGENT_CONFIG=config/agents/researcher.yaml python -m src.agent_service
AGENT_CONFIG=config/agents/analyst.yaml python -m src.agent_service
streamlit run ui/app.py
```

Or run everything with Docker:

```bash
docker compose up --build
```

## Architecture

- **Orchestrator** (FastAPI): Coordinates debate flow, routes messages, tracks state
- **Agent Services** (FastAPI): Each agent runs in its own service, processes ACP messages
- **NATS**: Async messaging between services
- **Qdrant**: Vector memory (shared debate history + private agent reasoning)
- **Streamlit**: Real-time debate UI

## Agents

| Agent | Role |
|-------|------|
| Skeptic | Challenges claims, identifies logical fallacies |
| Researcher | Validates evidence, checks facts |
| Analyst | Provides context, synthesizes arguments |
