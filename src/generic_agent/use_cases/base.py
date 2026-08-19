"""Base use-case agent facade owning a composed LangGraph state graph."""

from __future__ import annotations

import dataclasses
import logging
from typing import Any, Callable, ClassVar, Dict, Optional, Tuple

from langgraph.graph.state import CompiledStateGraph

from ..domain.context import RuntimeContext, StrategyContext
from ..graphs.base import BaseGraphStrategy

logger = logging.getLogger(__name__)

_DATACLASS_DEFAULTS: Dict[str, Any] = {
    "max_iterations": 3,
    "require_approval": False,
    "specialists": (),
}


class BaseUseCaseAgent:
    """Facade for a user-facing use case; owns a composed LangGraph graph.

    Subclasses declare metadata (use_case, title, when_to_use, aliases),
    specify a strategy, and can provide use-case-specific default parameters and lifecycle hooks.
    """

    use_case: str = ""
    title: str = ""
    when_to_use: str = ""
    defaults: ClassVar[dict] = {}
    aliases: Tuple[str, ...] = ()
    strategy: BaseGraphStrategy
    interfaces: Tuple[str, ...] = ("rest", "live", "mcp", "cli")

    def resolve_runtime(self, runtime: RuntimeContext) -> RuntimeContext:
        """Apply use case defaults onto a copy of runtime."""
        overrides: Dict[str, Any] = {}
        for key, default_val in self.defaults.items():
            current = getattr(runtime, key, None)
            if key == "roles":
                overrides[key] = {**default_val, **(current or {})}
            elif key in _DATACLASS_DEFAULTS:
                if current == _DATACLASS_DEFAULTS[key]:
                    overrides[key] = default_val
            elif key in ("model", "instruction", "tools"):
                if not current:
                    overrides[key] = default_val
            else:
                overrides[key] = default_val

        return dataclasses.replace(runtime, **overrides)

    def compose(self, runtime: RuntimeContext) -> CompiledStateGraph:
        """Build and compile the LangGraph state graph for this use case."""
        resolved = self.resolve_runtime(runtime)
        context = StrategyContext(
            strategy_type=self.strategy.agent_type,
            runtime=resolved,
            extra_config=dict(resolved.extra_config),
        )
        return self.strategy.build(context)

    def build(self, runtime: RuntimeContext) -> CompiledStateGraph:
        """Compile the graph and attach any lifecycle callbacks."""
        return self.compose(runtime)

    # Lifecycle hooks
    def before_run(self, state: Dict[str, Any]) -> None:
        """Hook called before graph execution begins."""

    def after_run(self, state: Dict[str, Any]) -> None:
        """Hook called after graph execution completes."""
