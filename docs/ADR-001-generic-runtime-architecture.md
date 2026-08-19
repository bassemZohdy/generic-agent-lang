# ADR-001: Generic Runtime Architecture

## Status
Accepted

## Context
Deploying AI agents across diverse use cases often leads to repetitive boilerplate, inconsistent configuration methods, and tightly-coupled agent code. We need a single, generic runtime that can adapt its execution pattern based entirely on externalized configuration (YAML and environment variables).

## Decision
1. Separate the public layer (`use_cases`) from the internal execution graph composition (`graphs`/`strategies`).
2. Use strict one-way dependencies: `use_cases` configure and invoke `graphs`, never the reverse.
3. Represent all agent states through typed, reducer-enabled structures compatible with LangGraph.
4. Expose the runtime across standard, enterprise-ready interfaces: REST API (with SSE streaming), WebSocket (bidirectional streaming), FastMCP server, and CLI.

## Consequences
- Single binary/container can be configured to run any supported agent pattern.
- New use cases can be added by declaring metadata and referencing a graph strategy.
