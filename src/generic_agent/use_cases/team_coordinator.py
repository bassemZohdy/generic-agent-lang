"""Team coordinator use case: supervisor managing and delegating across worker sub-agents."""

from typing import ClassVar, Dict

from ..graphs.supervisor import SupervisorStrategy
from .base import BaseUseCaseAgent


class TeamCoordinatorUseCaseAgent(BaseUseCaseAgent):
    """Supervisor agent coordinating and delegating sub-tasks across a team of AI workers."""

    use_case = "team_coordinator"
    title = "Multi-Agent Team Coordinator"
    when_to_use = "Complex, multi-faceted projects requiring active management, sub-task division, and synthesis."
    aliases = ("supervisor", "team", "coordinator", "manager")
    strategy = SupervisorStrategy()
    defaults: ClassVar[Dict] = {
        "max_iterations": 4,
        "extra_config": {"workers": 3},
    }
