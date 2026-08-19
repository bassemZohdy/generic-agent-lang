"""Approval gate use case: human-in-the-loop confirmation before action execution."""

from typing import ClassVar, Dict

from ..graphs.human_in_loop import HumanInLoopStrategy
from .base import BaseUseCaseAgent


class ApprovalGateUseCaseAgent(BaseUseCaseAgent):
    """Proposes an action and halts for explicit human approval before completing execution."""

    use_case = "approval_gate"
    title = "Human Approval Gate"
    when_to_use = "High-impact actions (sending emails, modifying databases, making purchases, altering production systems)."
    aliases = ("human_in_loop", "human_in_the_loop", "approval", "gate")
    strategy = HumanInLoopStrategy()
    defaults: ClassVar[Dict] = {
        "require_approval": True,
    }
