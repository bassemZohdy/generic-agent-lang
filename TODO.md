# Project Roadmap & TODO

## LangGraph Core & Graphs
- [x] Direct ReAct tool-calling graph
- [x] Sequential pipeline graph
- [x] Parallel fan-out and aggregation graph
- [x] Evaluator-Optimizer feedback loop graph
- [x] Dynamic specialist router graph
- [x] Supervisor team coordination graph
- [x] Plan-and-execute graph
- [ ] Protected durable human approval gate (existing HUMAN_IN_LOOP prototype does not interrupt and must not authorize actions)
- [ ] PostgreSQL / Redis checkpointer support for horizontal scaling
- [ ] Time-travel graph state replay debugging UI

## Models & Connectors
- [x] Multi-provider factory (OpenAI, Anthropic, Google, Ollama, Groq, Mistral, DeepSeek)
- [x] Streaming token generation
- [ ] Local llama.cpp / vLLM native gRPC client integration

## Tooling & Capabilities
- [x] Knowledge retrieval with mtime file caching
- [x] Web search (Tavily, DuckDuckGo)
- [ ] Protected approval tool (existing request_approval returns text only)
- [x] FastMCP Model Context Protocol integration
- [x] Dynamic OpenAPI 3.0 toolset generator
- [x] SKILL.md folder scanner
- [x] Mutating tool security audit guards
- [ ] Vector database tool (ChromaDB / Qdrant)

## Serving & Security
- [x] FastAPI REST API with SSE event streaming
- [x] WebSocket live bidirectional streaming
- [x] Keycloak / OIDC JWT validation and forward-auth
- [x] Subject-bound session isolation
- [x] OpenTelemetry invocation spans & attributes
