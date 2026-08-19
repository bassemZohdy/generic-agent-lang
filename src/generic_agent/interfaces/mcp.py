"""Local MCP server exposing application status and tools."""

from __future__ import annotations

import json
from typing import Any

try:
    from mcp.server.mcpserver import MCPServer as FastMCP
except ImportError:
    try:
        from mcp.server.fastmcp import FastMCP
    except ImportError:
        FastMCP = None  # type: ignore

try:
    from ..config.settings import settings
except ImportError:
    from generic_agent.config import settings


def get_service_status() -> str:
    """Return the current status of the configured generic agent service."""
    return json.dumps(
        {
            "service": "generic-agent-lang",
            "framework": "langchain+langgraph",
            "environment": "local",
            "status": "healthy",
            "version": settings.app_version,
            "deployment": settings.deployment,
        }
    )


if FastMCP is not None:
    mcp = FastMCP("generic-agent-lang")
    mcp.tool()(get_service_status)
else:
    mcp = None


if __name__ == "__main__":
    if mcp is not None:
        mcp.run()
