# ADR-002: Use-Case Taxonomy and Consolidation

## Status
Accepted

## Context
Users conceptualize agent tasks in terms of goals and workflows (e.g. "I want an assistant with tools", "I want an approval gate", "I need multi-specialist routing"), whereas graph engines operate in terms of nodes and edges.

## Decision
Consolidate 8 standardized public use-cases:
1. `assistant`: General-purpose direct conversational agent with ReAct tool execution.
2. `pipeline`: Ordered sequential multi-step processing chain.
3. `multi_perspective`: Concurrent fan-out workers aggregated into a balanced synthesis.
4. `refine_until_good`: Generate-evaluate-refine feedback loop with quality assessment.
5. `expert_dispatch`: Intent triage routing to domain specialists.
6. `team_coordinator`: Supervisor managing and delegating work across a team.
7. `plan_and_execute`: Explicit planning followed by step-by-step execution and verification.
8. `approval_gate`: Governed human-in-the-loop proposal, confirmation, and execution.

## Consequences
- Clean, intuitive API for operators and developers.
- Supports alias resolution for ergonomic CLI and configuration usage.
