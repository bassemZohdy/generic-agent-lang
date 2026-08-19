"""Registry and alias catalog for user-facing use cases."""

from __future__ import annotations

import logging
from typing import Dict, List, Optional, Tuple

from .approval_gate import ApprovalGateUseCaseAgent
from .assistant import AssistantUseCaseAgent
from .base import BaseUseCaseAgent
from .expert_dispatch import ExpertDispatchUseCaseAgent
from .multi_perspective import MultiPerspectiveUseCaseAgent
from .pipeline import PipelineUseCaseAgent
from .plan_and_execute import PlanAndExecuteUseCaseAgent
from .refine_until_good import RefineUntilGoodUseCaseAgent
from .team_coordinator import TeamCoordinatorUseCaseAgent

logger = logging.getLogger(__name__)


class UseCaseRegistry:
    """Registry mapping use-case identifiers and aliases to BaseUseCaseAgent instances."""

    def __init__(self) -> None:
        self._use_cases: Dict[str, BaseUseCaseAgent] = {}
        self._aliases: Dict[str, str] = {}

    def register(self, agent: BaseUseCaseAgent) -> None:
        canonical = agent.use_case.lower()
        if canonical in self._use_cases:
            raise ValueError(f"Use case {canonical!r} is already registered")
        self._use_cases[canonical] = agent
        self._aliases[canonical] = canonical
        for alias in agent.aliases:
            self._aliases[alias.lower()] = canonical
        logger.debug("Registered use case %r with aliases %s", canonical, agent.aliases)

    def resolve(self, raw_key: str) -> Tuple[str, BaseUseCaseAgent]:
        """Resolve a raw key (or alias) to its canonical key and instance.

        Raises:
            ValueError: If key is unknown.
        """
        cleaned = raw_key.strip().lower()
        canonical = self._aliases.get(cleaned)
        if not canonical or canonical not in self._use_cases:
            known = ", ".join(sorted(self._use_cases.keys()))
            raise ValueError(f"Unknown use case {raw_key!r}; available: {known}")
        return canonical, self._use_cases[canonical]

    def has(self, raw_key: str) -> bool:
        cleaned = raw_key.strip().lower()
        return cleaned in self._aliases

    def list_use_cases(self) -> List[str]:
        return sorted(self._use_cases.keys())

    def get_catalog(self) -> List[Dict[str, str]]:
        return [
            {
                "use_case": agent.use_case,
                "title": agent.title,
                "when_to_use": agent.when_to_use,
                "strategy": agent.strategy.agent_type,
            }
            for _, agent in sorted(self._use_cases.items())
        ]


_default_registry: Optional[UseCaseRegistry] = None


def get_default_registry() -> UseCaseRegistry:
    """Get or initialize default use-case registry."""
    global _default_registry
    if _default_registry is None:
        _default_registry = UseCaseRegistry()
        for agent in [
            AssistantUseCaseAgent(),
            PipelineUseCaseAgent(),
            MultiPerspectiveUseCaseAgent(),
            RefineUntilGoodUseCaseAgent(),
            ExpertDispatchUseCaseAgent(),
            TeamCoordinatorUseCaseAgent(),
            PlanAndExecuteUseCaseAgent(),
            ApprovalGateUseCaseAgent(),
        ]:
            _default_registry.register(agent)
    return _default_registry
