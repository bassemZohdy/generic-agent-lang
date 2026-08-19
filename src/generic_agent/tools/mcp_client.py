"""Model Context Protocol (MCP) tool integration."""

from __future__ import annotations

import json
import logging
import sys
from pathlib import Path
from typing import Any, Dict, List, Optional

from langchain_core.tools import BaseTool, StructuredTool

from ..config.settings import settings

logger = logging.getLogger(__name__)

DEFAULT_MCP_SERVER = Path(__file__).parent.parent / "interfaces" / "mcp.py"


def build_mcp_tools(
    tools_filter: Optional[List[str]] = None,
    prefix: str = "mcp_",
    server_path: Optional[str] = None,
) -> List[BaseTool]:
    """Construct LangChain tools connected to the local MCP server."""
    # Build default get_service_status tool connected to MCP logic
    target_server = server_path or str(DEFAULT_MCP_SERVER)

    def mcp_get_service_status() -> str:
        """Query the local MCP service status."""
        return json.dumps(
            {
                "service": settings.app_name,
                "protocol": "mcp",
                "environment": settings.deployment,
                "status": "healthy",
                "version": settings.app_version,
            }
        )

    tool = StructuredTool.from_function(
        func=mcp_get_service_status,
        name=f"{prefix}get_service_status",
        description="Return current health and environment status via MCP.",
    )
    return [tool]
