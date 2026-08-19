"""Human-in-the-loop approval tool."""

from __future__ import annotations

import logging
from typing import Any, Dict

from langchain_core.tools import tool

logger = logging.getLogger(__name__)


@tool
def request_approval(action: str, details: str = "") -> str:
    """Request explicit human confirmation before executing an irreversible or state-changing action."""
    logger.info("request_approval called for action: %s", action)
    return (
        f"Approval requested for action: '{action}'. "
        "The operation is paused pending human confirmation."
    )
