"""Generic configuration-driven LangChain and LangGraph agent runtime."""

from .agent import (
    GenericAgentResponse,
    RuntimeEngine,
    build_root_agent,
    get_root_agent,
    inspect_runtime,
)
from .config.loader import resolve_agent_config
from .config.schema import AgentConfig
from .config.settings import Settings, settings
from .domain.state import AgentState

__version__ = "0.1.0"

__all__ = [
    "AgentConfig",
    "AgentState",
    "GenericAgentResponse",
    "RuntimeEngine",
    "Settings",
    "__version__",
    "build_root_agent",
    "get_root_agent",
    "inspect_runtime",
    "resolve_agent_config",
    "settings",
]
