"""Tool audit and mutation protection callbacks."""

from __future__ import annotations

import logging
from typing import Any, Callable, Dict, Optional

logger = logging.getLogger(__name__)

_MUTATING_TOOL_WORDS = frozenset(
    {
        "create",
        "delete",
        "execute",
        "patch",
        "post",
        "put",
        "remove",
        "run",
        "send",
        "update",
        "write",
    }
)


def tool_name(tool: Any) -> str:
    return str(getattr(tool, "name", getattr(tool, "__name__", type(tool).__name__)))


def is_mutating_tool(tool: Any) -> bool:
    name = tool_name(tool).lower().replace("-", "_")
    if name in {"request_approval", "inspect_runtime", "retrieve_knowledge", "web_search", "google_search"}:
        return False
    return any(word in name.split("_") for word in _MUTATING_TOOL_WORDS)


def protect_and_audit_tool(tool: Any, args: Dict[str, Any], context: Any = None) -> Optional[Dict[str, Any]]:
    """Audit tool call and reject mutating tools unless confirmed."""
    name = tool_name(tool)
    user_id = getattr(context, "user_id", "anonymous") if context else "anonymous"
    logger.info("tool invocation started sub=%s tool=%s", user_id, name)

    if not is_mutating_tool(tool):
        return None

    confirmation = getattr(context, "tool_confirmation", None) if context else None
    if confirmation is not None and getattr(confirmation, "confirmed", False):
        return None

    logger.warning("mutating tool invocation requires confirmation sub=%s tool=%s", user_id, name)
    return {"error": f"State-changing tool {name!r} requires explicit human approval before execution."}


def audit_tool_result(tool: Any, args: Dict[str, Any], result: Any, context: Any = None) -> None:
    """Record tool completion without leaking secrets or large payloads."""
    name = tool_name(tool)
    user_id = getattr(context, "user_id", "anonymous") if context else "anonymous"
    outcome = "ok" if not isinstance(result, dict) or "error" not in result else "error"
    logger.info("tool invocation completed sub=%s tool=%s outcome=%s", user_id, name, outcome)
