"""Runtime execution context containing resolved components for graph composition."""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any, Callable, Dict, List, Optional, Tuple, Type

from langchain_core.language_models import BaseChatModel
from langchain_core.tools import BaseTool
from langgraph.checkpoint.base import BaseCheckpointSaver

from ..config.schema import RoleConfig


@dataclass
class RuntimeContext:
    """Shared runtime resources and configuration for LangGraph strategy execution."""

    model: BaseChatModel
    instruction: str
    tools: List[BaseTool]
    description: str
    code_executor: Any = None
    code_execution_strategy: Optional[str] = None
    code_execution_detail: str = ""
    state_schema: Type = Any
    output_schema: Optional[Type] = None
    output_key: Optional[str] = "last_response"
    checkpointer: Optional[BaseCheckpointSaver] = None
    before_agent_callback: Optional[Callable] = None
    after_agent_callback: Optional[Callable] = None
    max_iterations: int = 3
    require_approval: bool = False
    specialists: Tuple[str, ...] = ()
    roles: Dict[str, RoleConfig] = field(default_factory=dict)
    before_tool_callback: Optional[Callable] = None
    after_tool_callback: Optional[Callable] = None
    extra_config: Dict[str, Any] = field(default_factory=dict)


@dataclass
class StrategyContext:
    """Strategy-specific context passed to graph builders."""

    strategy_type: str
    runtime: RuntimeContext
    extra_config: Dict[str, Any] = field(default_factory=dict)
