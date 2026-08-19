"""Pipeline use case: sequential multi-step workflow execution."""

from typing import ClassVar, Dict

from ..graphs.sequential import SequentialStrategy
from .base import BaseUseCaseAgent


class PipelineUseCaseAgent(BaseUseCaseAgent):
    """Executes ordered multi-stage tasks in a sequential processing chain."""

    use_case = "pipeline"
    title = "Sequential Pipeline"
    when_to_use = "Multi-step workflows where output of step N feeds step N+1 (e.g. fetch -> analyze -> summarize)."
    aliases = ("sequential", "chain", "workflow")
    strategy = SequentialStrategy()
    defaults: ClassVar[Dict] = {
        "extra_config": {"steps": 3},
    }
