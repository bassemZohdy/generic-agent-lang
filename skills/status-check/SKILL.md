---
name: status-check
description: Inspect and verify node and service health metrics
version: 1.0.0
---

# Status Check Skill

## When to use
Use this skill whenever the user or another agent requests diagnostic, health, or latency status for deployed services.

## Instructions
1. Inspect available runtime metadata using `inspect_runtime`.
2. Query the service status endpoint.
3. Return a consolidated health summary with timestamp, status code, and latency metrics.

## Example
User: "Check node health"
Action: Query service health and output formatted status.
