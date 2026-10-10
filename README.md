# Generic Agent Runtime (LangChain & LangGraph)

> **Approval limitation:** `approval_gate` / `HUMAN_IN_LOOP` does not pause
> for a human decision. Missing or unknown status can reach completion,
> and `request_approval` only returns text. Do not use it to authorize
> state changes. The migration guide requires a protected durable gate.

> **Consolidation preparation:** the target for portable workflow behavior is
> [Open Workflow Agent](https://github.com/bassemZohdy/open-workflow-agent).
> Read the [migration gates and pinned source manifest](docs/migration/README.md)
> before changing an installed client. This source is retained; no runtime
> migration, package rename, image promotion or archival is complete.

An early configuration-driven AI agent prototype built on **LangChain** and **LangGraph**. Choose your workflow behavior, configure it via environment variables or YAML, and run it with one Docker command or as a standalone Python service.

[![Tests](https://img.shields.io/badge/tests-57%20passing-brightgreen)](./tests/)
[![Coverage](https://img.shields.io/badge/coverage-85%25%2B-brightgreen)](./tests/)
[![Python](https://img.shields.io/badge/python-3.10%20%7C%203.11%20%7C%203.12%20%7C%203.13-blue)](https://www.python.org/)
[![LangChain](https://img.shields.io/badge/LangChain-0.3-blue)](https://python.langchain.com/)
[![LangGraph](https://img.shields.io/badge/LangGraph-0.2-orange)](https://langchain-ai.github.io/langgraph/)

---

## Highlights & Capabilities

- **State Graph Architecture**: Powered by LangGraph's compiled `StateGraph` and `MemorySaver` checkpointer for stateful and cyclic multi-agent graphs.
- **Config-Driven**: Configure everything via environment variables or YAML files with recursive `${ENV_VAR:default}` interpolation.
- **8 Built-In Use Cases**: Direct Assistant, Pipeline, Multi-Perspective, Refine-Until-Good, Expert Dispatch, Team Coordinator, Plan-and-Execute, and the unsafe approval prototype described above.
- **Multi-Model Provider Support**: First-class support for **OpenAI**, **Anthropic**, **Google Gemini**, **Ollama**, **Groq**, **Mistral AI**, **DeepSeek**, and self-hosted vLLM gateways.
- **Rich Tool Ecosystem**: Knowledge file retrieval with mtime caching, web search, an approval-request placeholder, Model Context Protocol (MCP), dynamic OpenAPI generator, and SKILL.md folder scanner.
- **Pluggable Code Execution Sandbox**: Isolated Docker container sandbox with CPU/Memory/PIDs limits, read-only rootfs, isolated tmpfs, and timeout recovery.
- **Multiple Serving Interfaces**:
  - **REST API** with Server-Sent Events (SSE) token and node streaming on port `8002`.
  - **WebSocket Live API** with bidirectional interactive streaming and rate limiting on port `8003`.
  - **FastMCP Server** exposing status and tools.
  - **CLI Interface** (`generic-agent run`, `generic-agent serve`, `generic-agent inspect`).
- **Enterprise Security**: Keycloak / OIDC JWT token validation, JWKS key caching, Forward-Auth gateway on port `8010`, and subject-bound session isolation.
- **Observability**: OpenTelemetry tracing spans and LangSmith telemetry hooks.

---

## Quick Start (30 Seconds)

```bash
# 1. Export your API key and model choice
export OPENAI_API_KEY=your-key-here
export AGENT_MODEL=openai/gpt-4o
export AUTH_DISABLED=true

# 2. Run the agent container
docker run -p 8002:8002 \
  -e OPENAI_API_KEY=$OPENAI_API_KEY \
  -e AGENT_MODEL=$AGENT_MODEL \
  -e AUTH_DISABLED=true \
  generic-agent-lang:latest

# 3. Open http://localhost:8002/docs to try the interactive REST API
```

---

## Choose What Your Agent Does

Set `AGENT_USE_CASE` (or configure `agent.use_case` in YAML):

| What you want | `AGENT_USE_CASE` | Underlying Graph Strategy | Example prompt |
|---|---|---|---|
| Answer questions & use tools | `assistant` | `DIRECT` (ReAct) | "What's our Q3 revenue?" |
| Run steps in order | `pipeline` | `SEQUENTIAL` | "Fetch data → analyze → summarize" |
| Multiple viewpoints | `multi_perspective` | `PARALLEL` | "Analyze this from tech, business & risk views" |
| Self-critique & refine | `refine_until_good` | `EVALUATOR_OPTIMIZER` | "Draft, critique, and improve this proposal" |
| Specialist routing | `expert_dispatch` | `ROUTER` | "Billing questions to billing, tech to tech" |
| Coordinate a team | `team_coordinator` | `SUPERVISOR` | "Coordinate research, coding, and review" |
| Plan then execute | `plan_and_execute` | `PLAN_EXECUTE` | "Break down goal into steps and execute" |
| Unsafe approval prototype | `approval_gate` | `HUMAN_IN_LOOP` | Do not use to authorize state changes |

```bash
# Example: Run a 3-stage pipeline
docker run -e AGENT_USE_CASE=pipeline \
  -e AGENT_MODEL=openai/gpt-4o \
  -e OPENAI_API_KEY=$OPENAI_API_KEY \
  -e AUTH_DISABLED=true \
  -p 8002:8002 generic-agent-lang:latest
```

---

## Supported AI Models

Prefix the model string with the provider name (`provider/model`):

| Provider | Model String Example | Required Environment Variable |
|---|---|---|
| **OpenAI** | `openai/gpt-4o` | `OPENAI_API_KEY` |
| **Anthropic** | `anthropic/claude-3-5-sonnet-latest` | `ANTHROPIC_API_KEY` |
| **Google** | `google/gemini-2.0-flash` | `GOOGLE_API_KEY` |
| **Groq** | `groq/llama-3.3-70b-versatile` | `GROQ_API_KEY` |
| **Mistral** | `mistral/mistral-large-latest` | `MISTRAL_API_KEY` |
| **DeepSeek** | `deepseek/deepseek-chat` | `DEEPSEEK_API_KEY` |
| **Ollama (Local)** | `ollama/llama3` | `OLLAMA_API_BASE=http://host.docker.internal:11434` |

---

## Tool Capabilities

Enable tools via `AGENT_TOOLS` (default: `knowledge,search,mcp,openapi,approval,runtime,structured_output`):

- `knowledge` — Cached document search (`AGENT_KNOWLEDGE_FILE`, JSON or text)
- `search` — Web search via Tavily or DuckDuckGo (`TAVILY_API_KEY`)
- `code_execution` — Secure Docker sandbox execution (`AGENT_CODE_EXECUTION_STRATEGY=docker_container`)
- `approval` — Request text only; no protected pause or human authorization is implemented
- `skills` — Load `SKILL.md` capability folders (`AGENT_SKILLS_DIR=./skills`)
- `mcp` — Model Context Protocol tool connector
- `openapi` — Dynamic OpenAPI 3.0 toolset generator (`AGENT_OPENAPI_URL`)
- `runtime` — Inspect agent metadata and configuration
- `structured_output` — Enforce Pydantic `GenericAgentResponse` schema

---

## Configure with YAML

For complex setups, create an `agent.yaml`:

```yaml
agent:
  use_case: expert_dispatch
  name: "support-dispatcher"
  description: "Customer support specialist router"

model:
  provider: openai
  name: gpt-4o

roles:
  billing:
    instruction: "You handle billing, invoicing, and subscription inquiries."
    tools: [knowledge]
  technical:
    instruction: "You handle API errors, server crashes, and code debugging."
    tools: [search, runtime]

tools:
  enabled: [knowledge, search, runtime]
```

Run with:
```bash
docker run -v ./agent.yaml:/app/config/agent.yaml \
  -e OPENAI_API_KEY=$OPENAI_API_KEY \
  -e AUTH_DISABLED=true \
  -p 8002:8002 generic-agent-lang:latest
```

---

## Full Docker Compose Stack

Run the full stack with Keycloak authentication, Forward-Auth gateway, and demo services:

```bash
# 1. Copy environment template
cp .env.example .env

# 2. Start full stack
docker compose up --build -d

# 3. Start with Live WebSocket support
docker compose --profile live up --build -d

# 4. Start with demo OpenAPI service
docker compose --profile demo up --build -d
```

---

## Developer Guide & Testing

```bash
# 1. Clone repository
git clone https://github.com/bassemZohdy/generic-agent-lang.git
cd generic-agent-lang

# 2. Install dependencies with uv
uv sync --all-extras

# 3. Run test suite with coverage
uv run pytest --cov=generic_agent --cov-report=term-missing

# 4. Run CLI commands
uv run generic-agent inspect
uv run generic-agent run "What is the status of the runtime?"
uv run generic-agent serve --port 8002
```

---

## Documentation & Architecture

- [Architecture Overview](./docs/ARCHITECTURE.md)
- [ADR-001: Generic Runtime Architecture](./docs/ADR-001-generic-runtime-architecture.md)
- [ADR-002: Use-Case Taxonomy](./docs/ADR-002-use-case-taxonomy.md)
- [ADR-003: LangGraph StateGraph Architecture](./docs/ADR-003-langgraph-state-graph-architecture.md)
- [ADR-004: Pluggable Code Execution Sandbox](./docs/ADR-004-pluggable-code-execution.md)
- [Examples](./examples/)
- [Changelog](./CHANGELOG.md)
