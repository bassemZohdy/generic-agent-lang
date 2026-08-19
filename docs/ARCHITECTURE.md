# Architecture

This document describes the design and internal mechanisms of **`generic-agent-lang`** — module responsibilities, configuration pipeline, LangGraph state graph composition, code execution resolution, and security architecture.

## Overview

`generic-agent-lang` takes configuration (YAML files and environment variables) and turns it into a fully observable, type-safe, compiled **LangGraph state graph**. It is served behind multiple interfaces (REST with SSE streaming, WebSocket live streaming, FastMCP server, and CLI) with OIDC authentication and OpenTelemetry tracing.

```
 YAML / Env Vars
       │
       ▼
   use_cases (Public Catalog)
   • assistant, pipeline, multi_perspective, refine_until_good,
   • expert_dispatch, team_coordinator, plan_and_execute, approval_gate
       │
       ▼
   graphs / strategies (Internal Composition)
   • DirectStrategy (ReAct / Tool calling)
   • SequentialStrategy (Linear pipeline)
   • ParallelStrategy (Fan-out + Reducer)
   • EvaluatorOptimizerStrategy (Generate-Evaluate loop)
   • RouterStrategy (Specialist triage)
   • SupervisorStrategy (Team coordination)
   • PlannerExecutorStrategy (Plan then execute)
   • HumanInLoopStrategy (Approval gate & interrupt)
       │
       ▼
 Compiled LangGraph StateGraph (with MemorySaver checkpointer)
       │
       ▼
 Interfaces (FastAPI REST, WebSocket Live, FastMCP, CLI)
```

## Module Map (`src/generic_agent/`)

| Module / Package | Responsibility |
|---|---|
| `agent.py` | Top-level entrypoint. `RuntimeEngine` orchestrator, runtime context construction, graph compilation, `inspect_runtime()`. |
| `config/` | Pydantic V2 settings and configuration loader. `settings.py` (process snapshot), `schema.py` (validated schemas), `loader.py` (YAML + recursive `${ENV:default}` interpolation). |
| `domain/` | Framework-agnostic domain models. `state.py` (LangGraph `AgentState`), `schemas.py` (`GenericAgentResponse`), `context.py` (`RuntimeContext`). |
| `models/` | Multi-provider model factory (`resolve_model`) supporting OpenAI, Anthropic, Google Gemini, Ollama, Groq, Mistral, and DeepSeek. |
| `tools/` | Tool registry and builders: `knowledge.py` (cached retrieval), `search.py` (web search), `approval.py` (confirmation gate), `mcp_client.py`, `openapi.py`, `skills.py` (SKILL.md loader), and `audit.py` (security mutation guard). |
| `execution/` | Pluggable sandbox code execution (ADR-004). Docker container sandbox (`HardenedContainerCodeExecutor`) and `UnsafeLocalCodeExecutor`. |
| `graphs/` | LangGraph state graph strategies implementing `BaseGraphStrategy`. |
| `use_cases/` | Public use case catalog binding user metadata, defaults, aliases, and graph builders. |
| `auth/` | Keycloak/OIDC JWT validation, JWKS caching, role verification, forward-auth gateway (`gateway.py`), and FastAPI `SubjectBindingMiddleware`. |
| `interfaces/` | Interface adapters: REST API (`rest.py`), WebSocket live streaming (`live.py`), FastMCP server (`mcp.py`), OpenAPI service (`service.py`), and CLI (`cli.py`). |
| `telemetry/` | OpenTelemetry tracing (`tracing.py`) with span attribute instrumentation and LangSmith support. |
| `util.py` | Zero-dependency string helpers, environment variable interpolation, and production checks. |

## Use Cases vs. Strategies

| Use Case | Strategy | LangGraph Architecture |
|---|---|---|
| `assistant` | `DIRECT` | Single agent node with conditional tool-calling ReAct loop |
| `pipeline` | `SEQUENTIAL` | Multi-step linear graph (`step_0 -> step_1 -> step_2`) with accumulator state |
| `multi_perspective` | `PARALLEL` | Concurrent fan-out workers (`[w_0, w_1, w_2] -> aggregator`) |
| `refine_until_good` | `EVALUATOR_OPTIMIZER` | `generator -> evaluator -> [feedback loop / END]` |
| `expert_dispatch` | `ROUTER` | `router -> specialist_{name} -> END` |
| `team_coordinator` | `SUPERVISOR` | `supervisor -> worker_{i} -> supervisor -> END` |
| `plan_and_execute` | `PLAN_EXECUTE` | `planner -> executor -> replanner / summary -> END` |
| `approval_gate` | `HUMAN_IN_LOOP` | `proposer -> approval_gate (interrupt / check) -> completer` |

## Key Improvements over ADK Runtime

1. **State Graph Foundations (LangGraph)**:
   - Full control over state transitions, cyclic loops, and state schemas.
   - Built-in checkpointing (`MemorySaver`, SQLite, Postgres) enabling persistent multi-turn conversations and time-travel debugging.
2. **Unified Pydantic V2 Architecture**:
   - Consistent type validation, serialization, and OpenAPI schema generation across config, state, and outputs.
3. **Multi-Model Provider Flexibility**:
   - First-class support for OpenAI, Anthropic, Google, Ollama, Groq, Mistral, and custom OpenAI-compatible gateways.
4. **Fine-Grained Streaming**:
   - Server-Sent Events (SSE) and WebSocket streaming powered by LangGraph's `astream_events` (v2) emitting token-by-token deltas and tool events.
5. **Human-In-The-Loop Governance**:
   - Built-in approval gate, mutating tool protection, and interruptible state graphs.
