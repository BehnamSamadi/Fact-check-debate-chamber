# Debate Chamber

Multi-agent LLM deliberation system for collaborative fact-checking and adversarial reasoning. Specialized agents independently analyze claims, challenge assumptions, validate evidence, and refine conclusions through structured debate cycles.

## Quick Start

### With Docker (recommended)

```bash
cp .env.example .env
# Add your API keys to .env

docker compose up --build
```

### Local Development

```bash
# Start infrastructure
docker compose up nats qdrant langfuse-db langfuse-redis langfuse-clickhouse langfuse-minio langfuse

# In separate terminals:
python -m src.orchestrator.main
AGENT_CONFIG=config/agents/skeptic.yaml python -m src.agent_service
AGENT_CONFIG=config/agents/researcher.yaml python -m src.agent_service
AGENT_CONFIG=config/agents/analyst.yaml python -m src.agent_service
streamlit run ui/app.py
```

## Services

| Service | Port | Description |
|---------|------|-------------|
| Orchestrator | 8000 | FastAPI control plane, debate coordination |
| Skeptic Agent | — | Challenges claims, detects fallacies |
| Researcher Agent | — | Validates evidence, fact-checks |
| Analyst Agent | — | Synthesizes arguments, delivers verdicts |
| Streamlit UI | 8501 | Debate launcher and response viewer |
| NATS Monitor | 9090 | Real-time NATS message traffic dashboard |
| Langfuse | 3000 | LLM tracing and observability |
| NATS | 4222 | Async messaging backbone |
| Qdrant | 6333 | Vector memory and semantic retrieval |

## Agents

| Agent | Role |
|-------|------|
| **Skeptic** | Challenges claims, identifies logical fallacies, questions assumptions |
| **Researcher** | Validates evidence, checks facts, assesses source credibility |
| **Analyst** | Provides historical context, identifies patterns, synthesizes arguments |

Each agent is defined by a YAML config in `config/agents/`. To use a different provider:

```yaml
# config/agents/skeptic.yaml
model: google/gemini-3.1-flash-lite
base_url: https://openrouter.ai/api/v1
api_key_env: OPENROUTER_API_KEY
```

## Configuration

Copy `.env.example` to `.env` and fill in:

```bash
# Required — at least one LLM provider
OPENAI_API_KEY=sk-...

# Optional — use OpenRouter or any OpenAI-compatible provider
# OPENROUTER_API_KEY=sk-or-...
# LLM_BASE_URL=https://openrouter.ai/api/v1

# Optional — Langfuse tracing
# LANGFUSE_PUBLIC_KEY=pk-lf-...
# LANGFUSE_SECRET_KEY=sk-lf-...
```

## Debate Phases

| Phase | Description |
|-------|-------------|
| **OPENING** | All agents give initial analysis |
| **REBUTTAL** | Agents challenge each other's claims |
| **EVIDENCE** | Agents present and validate evidence |
| **SYNTHESIS** | Analyst integrates all arguments |
| **VERDICT** | Final assessment with consensus level |

## Stack

FastAPI, Docker, ACP-inspired protocol, NATS, OpenAI SDK (pluggable), Qdrant, Langfuse, Streamlit
