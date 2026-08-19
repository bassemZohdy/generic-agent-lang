"""Refine-until-good use case: generate, evaluate, and optimize iteratively."""

from typing import ClassVar, Dict

from ..graphs.evaluator_optimizer import EvaluatorOptimizerStrategy
from .base import BaseUseCaseAgent


class RefineUntilGoodUseCaseAgent(BaseUseCaseAgent):
    """Iteratively drafts, assesses against quality criteria, and refines until acceptable."""

    use_case = "refine_until_good"
    title = "Iterative Refinement (Evaluator-Optimizer)"
    when_to_use = "High-stakes writing, code generation, or analysis requiring rigorous evaluation before final delivery."
    aliases = ("evaluator_optimizer", "refine", "optimizer", "self_critique")
    strategy = EvaluatorOptimizerStrategy()
    defaults: ClassVar[Dict] = {
        "max_iterations": 3,
    }
