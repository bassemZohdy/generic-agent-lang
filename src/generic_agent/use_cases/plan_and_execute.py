"""Plan-and-execute use case: explicit planning followed by step execution."""

from typing import ClassVar, Dict

from ..graphs.planner_executor import PlannerExecutorStrategy
from .base import BaseUseCaseAgent


class PlanAndExecuteUseCaseAgent(BaseUseCaseAgent):
    """Decomposes a complex objective into an explicit multi-step plan before systematically executing."""

    use_case = "plan_and_execute"
    title = "Plan and Execute"
    when_to_use = "Complex goals requiring deliberate planning, phased execution, and verification."
    aliases = ("planner_executor", "plan_execute", "planner")
    strategy = PlannerExecutorStrategy()
