# ADR-004: Pluggable Code Execution Sandbox

## Status
Accepted

## Context
Running model-generated code requires strict isolation to prevent host resource exhaustion, fork bombs, unauthorized network access, and data leaks.

## Decision
1. Implement a pluggable `BaseCodeExecutor` interface with a `resolve_code_executor()` probe chain.
2. Provide `HardenedContainerCodeExecutor` with strict security constraints:
   - Resource limits: `mem_limit='512m'`, `nano_cpus=1e9` (1 CPU), `pids_limit=128`.
   - Filesystem: `read_only=True` rootfs with isolated `/tmp` tmpfs.
   - Network: `network_disabled=True`.
   - Privileges: `cap_drop=['ALL']`, `no-new-privileges=True`.
   - Timeout: Wall-clock execution timeout with SIGKILL and container restart on hang.
3. `unsafe_local` executor is explicit-opt-in only with mandatory warning logs.

## Consequences
- Safe and isolated code execution across local and containerized deployments.
