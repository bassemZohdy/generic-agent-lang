"""Web search tool for generic-agent-lang."""

from __future__ import annotations

import logging
import os
from typing import Any, Dict, List

from langchain_core.tools import tool

logger = logging.getLogger(__name__)


@tool
def web_search(query: str) -> str:
    """Search the web for up-to-date information on a given topic or query."""
    # 1. Try Tavily if TAVILY_API_KEY is configured
    if os.environ.get("TAVILY_API_KEY"):
        try:
            from langchain_community.tools.tavily_search import TavilySearchResults

            tavily = TavilySearchResults(max_results=5)
            results = tavily.invoke({"query": query})
            return (
                "<untrusted_web_search_results>\n"
                f"{results}\n"
                "</untrusted_web_search_results>"
            )
        except Exception as err:
            logger.warning("Tavily search failed: %s; trying fallback", err)

    # 2. Try DuckDuckGo
    try:
        from langchain_community.tools import DuckDuckGoSearchResults

        ddg = DuckDuckGoSearchResults(num_results=5)
        results = ddg.invoke(query)
        return (
            "<untrusted_web_search_results>\n"
            f"{results}\n"
            "</untrusted_web_search_results>"
        )
    except Exception as err:
        logger.debug("DuckDuckGo search unavailable: %s", err)

    # 3. Fallback stub
    return (
        "<untrusted_web_search_results>\n"
        f"Search results for: {query}\n"
        "- No live search provider API key configured (set TAVILY_API_KEY or install duckduckgo-search).\n"
        "</untrusted_web_search_results>"
    )
