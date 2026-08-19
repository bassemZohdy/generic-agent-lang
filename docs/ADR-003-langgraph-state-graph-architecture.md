# ADR-003: LangGraph StateGraph Architecture

## Status
Accepted

## Context
Traditional agent frameworks rely on rigid class hierarchies that make cycles, interrupts, and multi-agent coordination difficult to observe and control. LangGraph provides first-class support for cyclic state graphs, fine-grained event streaming, and state checkpointing.

## Decision
1. Build all agent execution patterns as compiled `StateGraph` instances from `langgraph`.
2. Standardize on `AgentState` TypedDict with `add_messages` reducer and structured workflow fields (`context`, `intermediate_steps`, `plan`, `evaluation`, `approval_status`).
3. Leverage LangGraph Checkpointers (`MemorySaver`) for conversation persistence and human-in-the-loop governance.
4. Use `astream_events` (v2) for granular real-time event streaming over SSE and WebSockets.

## Consequences
- Highly modular, testable, and debuggable graph components.
- Native support for token streaming, tool execution tracing, and state inspection.
