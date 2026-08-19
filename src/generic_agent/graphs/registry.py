"""Registry for LangGraph agent strategy graph builders."""

from __future__ import annotations

import logging
from typing import Dict, List, Optional

from .base import BaseGraphStrategy
from .direct import DirectStrategy
from .evaluator_optimizer import EvaluatorOptimizerStrategy
from .human_in_loop import HumanInLoopStrategy
from .parallel import ParallelStrategy
from .planner_executor import PlannerExecutorStrategy
from .router import RouterStrategy
from .sequential import SequentialStrategy
from .supervisor import SupervisorStrategy

logger = logging.getLogger(__name__)


class GraphStrategyRegistry:
    """Registry managing available LangGraph building strategies."""

    def __init__(self) -> None:
        self._strategies: Dict[str, BaseGraphStrategy] = {}

    def register(self, strategy: BaseGraphStrategy) -> None:
        key = strategy.agent_type.upper()
        if key in self._strategies:
            raise ValueError(f"Strategy for agent type {key!r} is already registered")
        self._strategies[key] = strategy
        logger.debug("Registered strategy for agent type %r", key)

    def get(self, agent_type: str) -> Optional[BaseGraphStrategy]:
        return self._strategies.get(agent_type.upper())

    def has(self, agent_type: str) -> bool:
        return agent_type.upper() in self._strategies

    def list_types(self) -> List[str]:
        return sorted(self._strategies.keys())


_default_registry: Optional[GraphStrategyRegistry] = None


def get_default_strategy_registry() -> GraphStrategyRegistry:
    """Retrieve or initialize the default strategy registry."""
    global _default_registry
    if _default_registry is None:
        _default_registry = GraphStrategyRegistry()
        for strategy in [
            DirectStrategy(),
            SequentialStrategy(),
            ParallelStrategy(),
            EvaluatorOptimizerStrategy(),
            RouterStrategy(),
            SupervisorStrategy(),
            PlannerExecutorStrategy(),
            HumanInLoopStrategy(),
        ]:
            _default_registry.register(strategy)
    return _default_registry
