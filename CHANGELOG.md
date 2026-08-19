# Changelog

All notable changes to `generic-agent-lang` will be documented in this file.

The format is based on [Keep a Changelog](https://keepachangelog.com/en/1.0.0/),
and this project adheres to [Semantic Versioning](https://semver.org/spec/v2.0.0.html).

## [0.1.0] - 2026-08-19

### Added
- **LangGraph StateGraph Core**: 8 state graph execution strategies (`DIRECT`, `SEQUENTIAL`, `PARALLEL`, `EVALUATOR_OPTIMIZER`, `ROUTER`, `SUPERVISOR`, `PLAN_EXECUTE`, `HUMAN_IN_LOOP`).
- **Use-Case Catalog**: 8 public use cases (`assistant`, `pipeline`, `multi_perspective`, `refine_until_good`, `expert_dispatch`, `team_coordinator`, `plan_and_execute`, `approval_gate`) with alias resolution.
- **Pydantic V2 Configuration**: Full validation, environment interpolation (`${VAR:default}`), and provenance tracking.
- **Multi-Model Provider Factory**: Support for OpenAI, Anthropic, Google Gemini, Ollama, Groq, Mistral, and DeepSeek.
- **Tool Ecosystem**: Knowledge retrieval with mtime caching, web search, human approval tool, MCP client, dynamic OpenAPI generator, SKILL.md folder scanner, and mutating tool audit callbacks.
- **Pluggable Code Execution Sandbox**: Hardened Docker container sandbox with CPU/memory/PIDs limits, readonly rootfs, tmpfs, and timeout recovery.
- **Enterprise Serving Interfaces**:
  - REST API with Server-Sent Events (SSE) token and node event streaming on port 8002.
  - WebSocket Live API with bidirectional streaming, message size constraints, and rate limiting on port 8003.
  - FastMCP stdio server.
  - Demo OpenAPI backend service on port 8001.
  - Rich CLI interface (`generic-agent run`, `generic-agent serve`, `generic-agent inspect`).
- **Security & Identity**: Keycloak/OIDC JWT validation, JWKS caching, role requirement enforcement, and FastAPI SubjectBindingMiddleware.
- **Observability**: OpenTelemetry tracing, span attributes, and LangSmith integration.
- **Docker Compose Stack**: Multi-profile orchestration with Keycloak, Traefik forward-auth, Observability, and Demo backend.
