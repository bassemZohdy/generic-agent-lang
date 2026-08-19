"""Base strategy interface for LangGraph state graph composition."""

from __future__ import annotations

from abc import ABC, abstractmethod
from typing import Any, Callable, Dict, List, Optional

from langchain_core.language_models import BaseChatModel
from langchain_core.messages import AIMessage, BaseMessage, HumanMessage, SystemMessage
from langchain_core.tools import BaseTool
from langgraph.graph.state import CompiledStateGraph

from ..config.schema import RoleConfig
from ..domain.context import RuntimeContext, StrategyContext
from ..domain.state import AgentState


class BaseGraphStrategy(ABC):
    """Abstract base class for state graph strategies in generic-agent-lang."""

    @property
    @abstractmethod
    def agent_type(self) -> str:
        """Return the uppercase strategy identifier (e.g. 'DIRECT', 'SEQUENTIAL')."""

    @abstractmethod
    def build(self, context: StrategyContext) -> CompiledStateGraph:
        """Build and compile a LangGraph StateGraph from the provided runtime context."""

    def validate(self, context: StrategyContext) -> None:
        """Validate strategy-specific configuration requirements."""

    def positive_count(self, context: StrategyContext, key: str, default: int = 2) -> int:
        """Extract a positive integer option from context or extra_config."""
        val = (context.extra_config or {}).get(key, default)
        if isinstance(val, bool) or not isinstance(val, int) or val < 1:
            raise ValueError(f"{self.agent_type} option {key!r} must be an integer >= 1; got {val!r}")
        return val

    def require_min_iterations(self, context: StrategyContext, minimum: int = 1) -> None:
        """Validate that runtime.max_iterations meets the minimum requirement."""
        if context.runtime.max_iterations < minimum:
            raise ValueError(
                f"{self.agent_type} strategy requires max_iterations >= {minimum}; "
                f"got {context.runtime.max_iterations}"
            )

    def get_role_config(self, context: StrategyContext, role_name: str) -> RoleConfig:
        """Retrieve role overrides for a specific sub-agent or worker."""
        return context.runtime.roles.get(role_name, RoleConfig())

    def resolve_llm_for_role(
        self,
        context: StrategyContext,
        role_name: Optional[str] = None,
        bind_tools: bool = True,
    ) -> BaseChatModel:
        """Get model for a role with optional tool binding."""
        rt = context.runtime
        role = self.get_role_config(context, role_name) if role_name else RoleConfig()

        model = rt.model
        if role.model:
            from ..models.factory import resolve_model
            model = resolve_model(role.model)

        tools = rt.tools
        if role.tools is not None:
            from ..tools.registry import build_tool
            built_tools = []
            for t_name in role.tools:
                t = build_tool(t_name)
                if t:
                    if isinstance(t, list):
                        built_tools.extend(t)
                    else:
                        built_tools.append(t)
            tools = built_tools

        if bind_tools and tools and hasattr(model, "bind_tools"):
            return model.bind_tools(tools)
        return model

    def build_instruction(
        self,
        context: StrategyContext,
        role_name: Optional[str] = None,
        default: str = "",
    ) -> str:
        """Assemble full instruction prompt for a role."""
        rt = context.runtime
        role = self.get_role_config(context, role_name) if role_name else RoleConfig()
        instruction = role.instruction or default or rt.instruction
        return instruction
