"""Assistant use case: general-purpose conversational agent with tools."""

from ..graphs.direct import DirectStrategy
from .base import BaseUseCaseAgent


class AssistantUseCaseAgent(BaseUseCaseAgent):
    """Direct assistant handling single or multi-turn queries with optional tool use."""

    use_case = "assistant"
    title = "Helpful Assistant"
    when_to_use = "Direct Q&A, conversational assistance, and tool-augmented lookup tasks."
    aliases = ("direct", "chat", "default")
    strategy = DirectStrategy()
