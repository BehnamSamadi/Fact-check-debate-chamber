# Debate Chamber

Distributed multi-agent deliberation platform designed around isolated autonomous reasoning systems collaborating through structured communication protocols rather than tightly coupled framework logic. The system focuses on collaborative fact-checking and adversarial reasoning by orchestrating multiple specialized LLM agents that independently analyze claims, challenge assumptions, validate evidence, and iteratively refine conclusions through structured debate cycles.

## Architecture

The architecture is intentionally built as **infrastructure-first rather than framework-first**. Instead of centering the system around a single orchestration framework such as LangChain or CrewAI, the platform treats agents as independent protocol-compliant services. Each agent runs inside its own isolated Docker container with its own runtime environment, dependencies, reasoning strategy, memory scope, and execution lifecycle. This isolation guarantees loose coupling between agents and allows heterogeneous implementations across different providers and frameworks without affecting the rest of the system.

For example:

- One agent may use the OpenAI SDK directly
- Another may use LangChain chains
- Another may use CrewAI workflows
- Another may use a local Ollama model

All agents participate uniformly because communication is standardized at the protocol layer rather than the framework layer.

## Communication

### ACP-Inspired Protocol

The communication architecture is based on an **ACP-inspired message protocol** that defines how agents exchange reasoning artifacts and debate state. Instead of direct Python calls or shared framework state, agents communicate exclusively through structured serialized messages over asynchronous transport channels. Messages contain metadata such as:

- Debate identifiers
- Sender and recipient information
- Round state
- Message type
- Confidence scores
- Evidence references
- Reasoning payloads

This creates a fully decoupled communication model where agents are implementation-independent and runtime-agnostic. The orchestrator only understands protocol contracts and does not require knowledge of how individual agents internally generate reasoning.

### NATS Messaging

The communication layer is event-driven and built on top of **NATS**. NATS acts as the distributed messaging backbone responsible for:

- Asynchronous pub/sub communication
- Event streaming
- Message routing
- Distributed coordination
- Scalable inter-service messaging

The ACP-inspired protocol defines message semantics, while NATS provides transport and delivery guarantees. This separation allows communication infrastructure and agent cognition to evolve independently.

## Orchestrator

A central orchestration service implemented with **FastAPI** acts as the deterministic control plane of the system. The orchestrator is responsible for:

- Initializing debate sessions
- Managing deliberation rounds
- Maintaining state transitions
- Coordinating message flow
- Enforcing protocol contracts
- Aggregating responses
- Tracking confidence evolution

Importantly, **the orchestrator does not perform reasoning itself**. It remains deterministic infrastructure while all probabilistic reasoning is delegated to the isolated agents. This separation between orchestration and cognition is a core architectural principle of the system.

## Memory

The platform uses a layered memory architecture designed to preserve both collaborative context and independent agent reasoning. The memory model consists of three primary scopes:

### Shared Deliberation Memory

A globally accessible memory space containing:

- Debate transcripts
- Verified evidence
- Shared conclusions
- Consensus state
- Public reasoning artifacts

This acts as the official debate context visible to all agents.

### Private Agent Memory

Each agent maintains isolated private memory accessible only within its own container and runtime. This memory stores:

- Intermediate reasoning
- Internal observations
- Temporary hypotheses
- Confidence evolution
- Strategic analysis

Private memory prevents premature convergence between agents and preserves cognitive diversity during deliberation.

### Semantic Vector Memory

**Qdrant** is used as the semantic retrieval layer for:

- Embedding storage
- Contextual retrieval
- Prior debate recall
- Evidence similarity search
- Long-term contextual grounding

The memory layer is abstracted behind interfaces so agents are not tightly coupled to the persistence implementation.

## Agent Factory

The system includes an **Agent Factory** layer responsible for dynamically provisioning agents from declarative configurations rather than hardcoded orchestration logic. The factory automatically injects:

- Runtime adapters
- Protocol interfaces
- Memory access layers
- Tool registries
- Tracing middleware
- Communication handlers

This enables agents to be treated as composable infrastructure units that can be dynamically introduced or replaced without changes to orchestration logic.

## Runtime

The runtime architecture is fully vendor-agnostic. A runtime abstraction layer standardizes interaction with different providers and frameworks through unified interfaces. Internally, each runtime may use:

- OpenAI SDK
- LangChain
- CrewAI
- Anthropic APIs
- Local inference servers
- Custom reasoning pipelines

But externally every agent exposes the same protocol-compliant communication interface. This allows heterogeneous reasoning systems to coexist inside the same deliberation workflow.

## Observability

**Langfuse** is integrated across all services to monitor:

- Prompts and completions
- Token usage
- Latency
- Reasoning chains
- Inter-agent interactions
- Debate timelines

## Frontend

**Streamlit** serves as a lightweight operational interface for launching debates and visualizing agent interactions, reasoning outputs, confidence scores, and deliberation progress in real time.

## Design Foundations

The overall architecture combines principles from:

- Distributed systems
- Protocol-oriented architecture
- Event-driven microservices
- Multi-agent coordination systems
- Retrieval-augmented reasoning
- Autonomous deliberation infrastructure

## Stack

| Component | Technology |
|-----------|-----------|
| Orchestration | FastAPI |
| Isolation | Docker |
| Protocol | ACP-inspired structured messages |
| Messaging | NATS |
| Cognition | OpenAI SDK / LangChain / CrewAI / local runtimes |
| Memory | Qdrant |
| Observability | Langfuse |
| Frontend | Streamlit |
