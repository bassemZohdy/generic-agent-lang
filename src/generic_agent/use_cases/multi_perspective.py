"""Multi-perspective use case: concurrent analysis across multiple viewpoints."""

from typing import ClassVar, Dict

from ..graphs.parallel import ParallelStrategy
from .base import BaseUseCaseAgent


class MultiPerspectiveUseCaseAgent(BaseUseCaseAgent):
    """Gathers multiple perspectives concurrently and synthesizes a balanced overview."""

    use_case = "multi_perspective"
    title = "Multi-Perspective Analysis"
    when_to_use = "When complex issues benefit from parallel evaluation from several distinct viewpoints."
    aliases = ("parallel", "diverse_opinions", "panel")
    strategy = ParallelStrategy()
    defaults: ClassVar[Dict] = {
        "extra_config": {"workers": 3},
    }
