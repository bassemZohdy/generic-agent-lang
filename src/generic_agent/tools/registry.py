"""Tool construction registry and runtime inspector."""

from __future__ import annotations

import json
import logging
from typing import Any, Dict, List, Optional, Union

from langchain_core.tools import BaseTool, tool

from ..config.schema import AgentConfig
from ..config.settings import settings
from .approval import request_approval
from .knowledge import retrieve_knowledge
from .mcp_client import build_mcp_tools
from .openapi import build_openapi_tools
from .search import web_search
from .skills import load_skills_from_dir

logger = logging.getLogger(__name__)

_SILENT_TOOL_NAMES = {"code_execution", "structured_output"}


@tool
def inspect_runtime() -> str:
    """Inspect active agent configuration, model parameters, and enabled tools."""
    return json.dumps(
        {
            "agent": settings.app_name,
            "version": settings.app_version,
            "model": settings.model,
            "deployment": settings.deployment,
            "enabled_tools": list(settings.enabled_tools),
        }
    )


def build_tool(name: str, config: Optional[AgentConfig] = None) -> Union[BaseTool, List[BaseTool], None]:
    """Construct a tool or toolset by name.

    Args:
        name: Name of tool to build.
        config: Optional resolved AgentConfig.

    Returns:
        BaseTool, list of BaseTools, or None if unknown/silent.
    """
    if name in _SILENT_TOOL_NAMES:
        return None

    if name == "runtime":
        return inspect_runtime
    if name == "approval":
        return request_approval
    if name == "knowledge":
        return retrieve_knowledge
    if name == "search":
        return web_search

    if name == "mcp":
        mcp_cfg = config.tools.mcp if (config and config.tools) else None
        return build_mcp_tools(
            tools_filter=mcp_cfg.tools if mcp_cfg else None,
            prefix=mcp_cfg.prefix if mcp_cfg else settings.mcp_tool_prefix,
            server_path=mcp_cfg.server_path if mcp_cfg else None,
        )

    if name == "openapi":
        openapi_cfg = config.tools.openapi if (config and config.tools) else None
        return build_openapi_tools(
            url=openapi_cfg.url if (openapi_cfg and openapi_cfg.url) else settings.openapi_url,
            path=openapi_cfg.path if openapi_cfg else settings.openapi_path,
            title=openapi_cfg.title if openapi_cfg else settings.openapi_title,
            prefix=openapi_cfg.prefix if openapi_cfg else settings.openapi_tool_prefix,
        )

    if name == "skills":
        skills_cfg = config.tools.skills if (config and config.tools) else None
        s_dir = (skills_cfg.dir if skills_cfg else "") or settings.skills_dir
        s_prefix = (skills_cfg.prefix if skills_cfg else "") or settings.skills_tool_prefix
        if s_dir:
            return load_skills_from_dir(s_dir, prefix=s_prefix)
        return []

    return None
