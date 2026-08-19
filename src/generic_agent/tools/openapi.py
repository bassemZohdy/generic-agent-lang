"""OpenAPI toolset builder generating LangChain tools from OpenAPI specifications."""

from __future__ import annotations

import logging
from typing import Any, Callable, Dict, List, Optional

import httpx
from langchain_core.tools import BaseTool, StructuredTool

from ..config.settings import settings

logger = logging.getLogger(__name__)


def build_openapi_tools(
    *,
    url: str,
    path: str = "/status",
    title: str = "Service API",
    prefix: str = "api_",
    api_key: Optional[str] = None,
) -> List[BaseTool]:
    """Construct LangChain tools pointing to the configured OpenAPI endpoint."""
    headers = {"x-api-key": api_key or settings.service_api_key} if (api_key or settings.service_api_key) else {}

    def get_service_status() -> str:
        """Call the service endpoint and return status information."""
        target_url = f"{url.rstrip('/')}{path}"
        try:
            with httpx.Client(timeout=5.0) as client:
                response = client.get(target_url, headers=headers)
                if response.status_code == 200:
                    return f"Service Status: {response.text}"
                return f"Service responded with status {response.status_code}: {response.text}"
        except Exception as err:
            return f"Failed to reach service at {target_url}: {err}"

    tool = StructuredTool.from_function(
        func=get_service_status,
        name=f"{prefix}get_status",
        description=f"Check the status and health of the {title} service.",
    )
    return [tool]
