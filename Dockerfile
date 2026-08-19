# Multi-stage build for generic-agent-lang
FROM ghcr.io/astral-sh/uv:0.11.26 AS uv-bin

FROM python:3.12-slim-bookworm AS base

# Install uv binary from official image
COPY --from=uv-bin /uv /uvx /bin/

WORKDIR /app

ENV PYTHONUNBUFFERED=1 \
    UV_COMPILE_BYTECODE=1 \
    UV_LINK_MODE=copy \
    PORT=8002

# Install system dependencies
RUN apt-get update && apt-get install -y --no-install-recommends \
    curl \
    ca-certificates \
    && rm -rf /var/lib/apt/lists/*

# Copy pyproject.toml and sync dependencies first for caching
COPY pyproject.toml README.md /app/
RUN uv sync --frozen --no-install-project --all-extras || uv sync --no-install-project --all-extras

# Copy source code
COPY src/ /app/src/
COPY config/ /app/config/ 2>/dev/null || true
COPY skills/ /app/skills/ 2>/dev/null || true

# Install project package in editable/wheel mode
RUN uv sync --all-extras

# Non-root user for security
RUN groupadd -g 10001 agentgroup && \
    useradd -u 10001 -g agentgroup -s /bin/bash -m agentuser && \
    chown -R agentuser:agentgroup /app

USER agentuser

EXPOSE 8002 8003

CMD ["uv", "run", "uvicorn", "generic_agent.interfaces.rest:app", "--host", "0.0.0.0", "--port", "8002"]
