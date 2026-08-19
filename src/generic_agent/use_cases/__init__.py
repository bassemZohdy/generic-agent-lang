"""Use-cases package for generic-agent-lang."""

from .approval_gate import ApprovalGateUseCaseAgent
from .assistant import AssistantUseCaseAgent
from .base import BaseUseCaseAgent
from .expert_dispatch import ExpertDispatchUseCaseAgent
from .multi_perspective import MultiPerspectiveUseCaseAgent
from .pipeline import PipelineUseCaseAgent
from .plan_and_execute import PlanAndExecuteUseCaseAgent
from .refine_until_good import RefineUntilGoodUseCaseAgent
from .registry import UseCaseRegistry, get_default_registry
from .team_coordinator import TeamCoordinatorUseCaseAgent

__all__ = [
    "ApprovalGateUseCaseAgent",
    "AssistantUseCaseAgent",
    "BaseUseCaseAgent",
    "ExpertDispatchUseCaseAgent",
    "MultiPerspectiveUseCaseAgent",
    "PipelineUseCaseAgent",
    "PlanAndExecuteUseCaseAgent",
    "RefineUntilGoodUseCaseAgent",
    "TeamCoordinatorUseCaseAgent",
    "UseCaseRegistry",
    "get_default_registry",
]
